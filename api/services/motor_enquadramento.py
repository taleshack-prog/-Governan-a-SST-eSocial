# api/services/motor_enquadramento.py — SST ESOCIAL GOV
# Motor de apuracao do enquadramento (Adendo 04, Fase 3 / RF-0.175-182).
# Para cada competencia do periodo de apuracao: escolhe a atividade de MAIOR quantitativo
# (empate -> maior grau), le o grau na tabela do Anexo I (cnae_enquadramento), converte em
# aliquota (1/2/3 %), multiplica pelo FAP do ano e grava a serie (1 linha por competencia).
# Vao a FILA DE CONFERENCIA (nunca valor presumido): obra CNO (B.5), CNAE fora do Anexo I
# (RF-0.182), FAP do ano nao informado (RF-0.177), e competencia sem quantitativo declarado.
from datetime import date, datetime

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.estabelecimento import Estabelecimento
from api.models.empresa import Empresa
from api.models.estabelecimento_atividade import EstabelecimentoAtividade
from api.models.estabelecimento_fap import EstabelecimentoFAP
from api.models.estabelecimento_rat_aplicado import EstabelecimentoRatAplicado
from api.models.estabelecimento_enquadramento import EstabelecimentoEnquadramento
from api.models.cnae_enquadramento import CnaeEnquadramento

FUND = {
    "dispositivo": "Lei 8.212/91, art. 22, II; Decreto 3.048/99, art. 202, §§ 3º e 4º",
    "ato": "IN RFB 2.110/2022, art. 43",
    "anexo": "Anexo I (grau por subclasse CNAE)",
}


def _meses(inicio: date, fim: date):
    y, m = inicio.year, inicio.month
    while (y, m) <= (fim.year, fim.month):
        yield date(y, m, 1)
        m += 1
        if m > 12:
            m, y = 1, y + 1


def _vigente(comp: date, ini: date, fim) -> bool:
    return ini <= comp and (fim is None or fim >= comp)


async def apurar_estabelecimento(estab_id, db: AsyncSession) -> dict:
    estab = (await db.execute(select(Estabelecimento).where(Estabelecimento.id == estab_id))).scalar_one_or_none()
    if estab is None:
        return {"ok": False, "erro": "estabelecimento inexistente"}
    empresa = (await db.execute(select(Empresa).where(Empresa.id == estab.empresa_id))).scalar_one_or_none()

    # janela = periodo de apuracao da empresa, recortado pela vida do estabelecimento (RF-0.172)
    p_ini = (empresa.periodo_apuracao_inicio if empresa else None) or estab.data_abertura or date(date.today().year - 4, 1, 1)
    p_fim = (empresa.periodo_apuracao_fim if empresa else None) or date.today()
    ini = max(p_ini, estab.data_abertura or p_ini)
    fim = min(p_fim, estab.data_encerramento or p_fim)

    atividades = (await db.execute(
        select(EstabelecimentoAtividade).where(EstabelecimentoAtividade.estabelecimento_id == estab_id)
    )).scalars().all()
    faps = {r.ano_vigencia: float(r.valor_fap) for r in (await db.execute(
        select(EstabelecimentoFAP).where(EstabelecimentoFAP.estabelecimento_id == estab_id)
    )).scalars().all()}
    rats = (await db.execute(
        select(EstabelecimentoRatAplicado).where(EstabelecimentoRatAplicado.estabelecimento_id == estab_id)
    )).scalars().all()

    # grau por CNAE (cache) a partir do Anexo I
    graus: dict[str, int | None] = {}
    async def grau_de(cnae: str):
        if cnae not in graus:
            ce = (await db.execute(select(CnaeEnquadramento).where(CnaeEnquadramento.cnae == cnae))).scalar_one_or_none()
            graus[cnae] = ce.grau_risco if ce else None
        return graus[cnae]

    is_cno = estab.tipo_estabelecimento == "CNO"
    versao = "Anexo I: Decreto 3.048/99 (red. 10.410/2020), CNAE 2.3; IN RFB 2.110/2022"

    # recalcula: apaga a serie anterior e regrava
    await db.execute(delete(EstabelecimentoEnquadramento).where(EstabelecimentoEnquadramento.estabelecimento_id == estab_id))

    total = em_fila = 0
    if fim < ini:
        await db.commit()
        return {"ok": True, "competencias": 0, "em_fila": 0, "aviso": "janela vazia (datas)"}

    for comp in _meses(ini, fim):
        total += 1
        em_fila_flag = False
        motivo = None
        cnae_prep = criterio = None
        grau = aliq_dev = aliq_ef = None

        # RAT aplicado vigente na competencia
        aliq_apl = None
        for r in rats:
            if _vigente(comp, r.inicio, r.fim):
                aliq_apl = float(r.aliquota)
                break

        # atividades vigentes com quantitativo declarado
        vigentes = [a for a in atividades if _vigente(comp, a.vigencia_inicio, a.vigencia_fim) and a.quantitativo is not None]

        if is_cno:
            em_fila_flag, motivo = True, "Obra (CNO): apuração vai à conferência (Anexo VI pendente)."
        elif not vigentes:
            em_fila_flag, motivo = True, "Sem quantitativo declarado nesta competência."
        else:
            # preponderante = maior quantitativo; empate -> maior grau
            qmax = max(a.quantitativo for a in vigentes)
            candidatos = [a for a in vigentes if a.quantitativo == qmax]
            if len(candidatos) == 1:
                escolhida, criterio = candidatos[0], "maior_quantitativo"
            else:
                melhor, melhor_grau = None, -1
                for a in candidatos:
                    g = (await grau_de(a.cnae)) or 0
                    if g > melhor_grau:
                        melhor, melhor_grau = a, g
                escolhida, criterio = melhor, "desempate_grau"
            cnae_prep = escolhida.cnae
            grau = await grau_de(cnae_prep)
            if grau is None:
                em_fila_flag, motivo = True, f"CNAE {cnae_prep} sem linha no Anexo I."
            else:
                aliq_dev = float(grau)  # 1/2/3 %
                fap = faps.get(comp.year)
                if fap is None:
                    em_fila_flag, motivo = True, f"FAP de {comp.year} não informado."
                else:
                    aliq_ef = round(aliq_dev * fap, 4)

        if em_fila_flag:
            em_fila += 1

        db.add(EstabelecimentoEnquadramento(
            estabelecimento_id=estab_id, competencia=comp,
            cnae_preponderante=cnae_prep, criterio=(criterio or ("fila_conferencia" if em_fila_flag else None)),
            grau_risco=grau, aliquota_devida=aliq_dev,
            fap=faps.get(comp.year), aliquota_efetiva=aliq_ef, aliquota_aplicada=aliq_apl,
            em_fila=em_fila_flag, motivo_fila=motivo,
            fund_dispositivo=FUND["dispositivo"], fund_ato_normativo=FUND["ato"],
            fund_anexo=FUND["anexo"], fund_vigencia=versao,
            data_apuracao=datetime.utcnow(), versao_tabelas=versao,
        ))

    await db.commit()
    return {"ok": True, "competencias": total, "em_fila": em_fila}
