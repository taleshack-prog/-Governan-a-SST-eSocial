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
from api.services.regime_competencia import regime_da_competencia, rat_se_aplica, CERTO
from api.services.enquadramento_eventos import registrar_apuracao, retrato

# A CITACAO NAO MORA MAIS AQUI (decisao da Carolina, 21/10). Havia uma constante FUND neste
# arquivo com o dispositivo escrito a mao, e o motor a copiava em cada linha apurada. Eram duas
# fontes divergindo com o tempo: a tabela versionada (fundamentacao_campo, campo 'rat_devido') e
# este literal em Python. Quem lesse a competencia veria o literal; quem clicasse no § na tela
# veria a tabela. O literal nao tinha data: uma serie de 2021 saia citando a redacao de hoje.
#
# A regra: a tabela versionada e a unica fonte do sistema, consultada SEMPRE pela data da
# competencia (api/services/fundamentacao.citacao_de). A citacao congelada deixa de ser campo da
# competencia e passa a ser parte do documento EMITIDO — a peca leva dentro dela a copia do que
# citou, com a data em que resolveu.
#
# As colunas fund_dispositivo / fund_ato_normativo / fund_anexo / fund_vigencia continuam na
# tabela, ja sem ninguem escrevendo nem lendo. Sao removidas na limpeza de colunas aposentadas,
# DEPOIS que este codigo estiver em producao — derrubar coluna que o codigo antigo ainda le
# quebraria a API no intervalo entre a migration e o deploy.


def _meses(inicio: date, fim: date):
    y, m = inicio.year, inicio.month
    while (y, m) <= (fim.year, fim.month):
        yield date(y, m, 1)
        m += 1
        if m > 12:
            m, y = 1, y + 1


def _vigente(comp: date, ini: date, fim) -> bool:
    return ini <= comp and (fim is None or fim >= comp)


async def apurar_estabelecimento(estab_id, db: AsyncSession, autor: str | None = None) -> dict:
    estab = (await db.execute(select(Estabelecimento).where(Estabelecimento.id == estab_id))).scalar_one_or_none()
    if estab is None:
        return {"ok": False, "erro": "estabelecimento inexistente"}
    empresa = (await db.execute(select(Empresa).where(Empresa.id == estab.empresa_id))).scalar_one_or_none()

    # janela = periodo de apuracao da empresa, recortado pela vida do estabelecimento (RF-0.172)
    p_ini = (empresa.periodo_apuracao_inicio if empresa else None) or estab.data_abertura or date(date.today().year - 4, 1, 1)
    p_fim = (empresa.periodo_apuracao_fim if empresa else None) or date.today()
    ini = max(p_ini, estab.data_abertura or p_ini)
    fim = min(p_fim, estab.data_encerramento or p_fim)

    # ITEM 8 DA REVISAO DE 19/10 — a SITUACAO CADASTRAL delimita a janela.
    # Empresa baixada, suspensa ou inapta tem a janela limitada do mesmo modo que a encerrada:
    # nao faz sentido apurar competencia posterior ao fim da atividade. A situacao e dado de
    # calculo, nao recado de tela.
    situacao = (getattr(empresa, "situacao_cadastral", None) or "").strip().upper() if empresa else ""
    sit_data = getattr(empresa, "situacao_cadastral_data", None) if empresa else None
    situacao_sem_data = False
    if situacao and situacao != "ATIVA":
        if sit_data:
            fim = min(fim, sit_data)
        else:
            # Sabemos que a empresa NAO esta ativa e nao sabemos desde quando. Recortar numa data
            # inventada omitiria competencias devidas; nao recortar afirmaria atividade que pode
            # nao existir. Entao nada e presumido: as competencias vao a conferencia.
            situacao_sem_data = True

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

    # ITEM 2 DA REVISAO DE 19/10 — REVOGACAO DA CONFERENCIA.
    # Conferir e assinar sobre um numero determinado. Se o dado de calculo mudou, o numero muda e
    # a assinatura nao corresponde mais a nada: manter o estado anterior seria carregar o aval de
    # uma pessoa sobre um valor que ja nao existe. Antes de reescrever a serie, guardamos QUEM
    # havia conferido cada competencia, para que a nova linha nasca NAO conferida mas com o
    # rastro de que houve um aval e de que ele foi revogado — quando e por quem.
    # A SERIE ANTERIOR INTEIRA, e nao so as conferidas (migration 047). Duas razoes: o diff da
    # trilha precisa do valor de antes para dizer "de quanto para quanto", e so da para saber se
    # algo mudou comparando com o que havia. Como a serie e APAGADA logo abaixo, este e o unico
    # instante em que o estado anterior existe.
    linhas_antes = (await db.execute(
        select(EstabelecimentoEnquadramento).where(
            EstabelecimentoEnquadramento.estabelecimento_id == estab_id
        )
    )).scalars().all()
    antes_por_comp = {r.competencia: retrato(r) for r in linhas_antes}
    conferidas_antes = {
        r.competencia: (r.conferido_por, r.conferido_em)
        for r in linhas_antes if r.conferido_por
    }
    agora = datetime.utcnow()
    eventos_gravados = 0

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
        rat_aplicavel = True
        motivo_inaplicavel = None
        reg = {"certeza": CERTO, "regime": None, "anexo": None, "motivo": None}

        # RAT aplicado vigente na competencia. Desdobrado em GRAU e FATOR (migration 036): a
        # efetiva aplicada e o produto dos dois, como o eSocial valida no S-1005. Quando a linha
        # e antiga e guarda so a efetiva, usa-a e deixa as origens NULL — o sistema registra que
        # divergiu sem afirmar de onde, em vez de presumir rat=3 / fap=1,0.
        aliq_apl = rat_apl = fap_apl = None
        proc_rat = proc_fap = None
        for r in rats:
            if _vigente(comp, r.inicio, r.fim):
                proc_rat, proc_fap = r.processo_rat, r.processo_fap
                if r.aliquota_rat is not None and r.fap_aplicado is not None:
                    rat_apl, fap_apl = float(r.aliquota_rat), float(r.fap_aplicado)
                    aliq_apl = round(rat_apl * fap_apl, 4)
                else:
                    aliq_apl = float(r.aliquota)
                break

        # atividades vigentes com quantitativo declarado
        vigentes = [a for a in atividades if _vigente(comp, a.vigencia_inicio, a.vigencia_fim) and a.quantitativo is not None]

        # O REGIME VEM ANTES DE TUDO (22/10). Se o regime afasta a apuracao, nao importa se a
        # obra e CNO, se ha quantitativo declarado ou se o FAP do ano foi informado: nao ha RAT
        # a apurar, e perguntar o resto seria apurar o que nao existe. Era a ausencia deste
        # bloco que fazia o sistema afirmar credito em 58 competencias de uma empresa do
        # Simples, Anexo III.
        if empresa is not None:
            reg = await regime_da_competencia(empresa.id, comp, db)
            if reg["certeza"] != CERTO:
                # Incerteza vai para conferencia, NUNCA para premissa — regra da Carolina.
                # Sem saber o regime nao da para dizer nem que ha RAT, nem que nao ha.
                em_fila_flag, motivo = True, reg["motivo"]
            else:
                aplica, porque = rat_se_aplica(reg["regime"], reg["anexo"])
                if not aplica:
                    rat_aplicavel, motivo_inaplicavel = False, porque

        if not rat_aplicavel:
            # Nada a calcular: devida, efetiva e grau ficam nulos, e por consequencia a
            # divergencia tambem — nao ha o que comparar com o aplicado. O APLICADO continua
            # gravado de proposito: empresa do Anexo III que declarou RAT no S-1005 e achado
            # por si so, porque pode estar recolhendo o que nao deve.
            pass
        elif em_fila_flag:
            # Regime incerto, ja resolvido acima com o seu proprio motivo. Vem antes dos demais
            # ramos para que nenhum deles sobrescreva a explicacao — sem saber o regime, dizer
            # "sem quantitativo declarado" seria apontar a pendencia errada.
            pass
        elif situacao_sem_data:
            em_fila_flag, motivo = True, (
                f"Empresa com situação cadastral '{situacao}' e sem data da situação: não é "
                f"possível delimitar a janela. Informe a data para apurar.")
        elif is_cno:
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
            rat_aplicado=rat_apl, fap_aplicado=fap_apl,
            processo_rat=proc_rat, processo_fap=proc_fap,
            # Nasce NAO conferida, sempre: o motor nao assina. Se havia aval sobre esta
            # competencia, o rastro da revogacao fica registrado.
            conferido_por=None, conferido_em=None,
            revogado_em=agora if comp in conferidas_antes else None,
            revogado_por=autor if comp in conferidas_antes else None,
            revogado_de=conferidas_antes[comp][0] if comp in conferidas_antes else None,
            em_fila=em_fila_flag, motivo_fila=motivo,
            # Aplicabilidade e o regime que a decidiu, congelados na linha (migration 046): a
            # peca precisa dizer o fato E a fonte. 'regime_origem' fica nulo ate a rodada da
            # procedencia; hoje toda declaracao de regime e do contribuinte.
            rat_aplicavel=rat_aplicavel, motivo_inaplicavel=motivo_inaplicavel,
            regime_competencia=reg.get("regime"), anexo_competencia=reg.get("anexo"),
            # fund_* NAO sao mais preenchidas: a citacao vem da tabela versionada, pela data da
            # competencia. 'versao_tabelas' permanece — e outra coisa: a versao das tabelas de
            # CALCULO usadas na apuracao, nao a vigencia da norma. Vinham impressas no mesmo
            # rodape, uma rotulada como se fosse a outra.
            data_apuracao=datetime.utcnow(), versao_tabelas=versao,
        ))

        # TRILHA (migration 047). Registra o que esta competencia passou a valer e, quando havia
        # conferencia sobre um numero diferente, tambem o que deixou de valer e de quem era a
        # assinatura. Nao grava nada quando o numero nao mudou — ver registrar_apuracao.
        eventos_gravados += await registrar_apuracao(
            db,
            estabelecimento_id=estab_id,
            competencia=comp,
            antes=antes_por_comp.get(comp),
            depois={
                "grau_risco": grau, "aliquota_devida": aliq_dev, "fap": faps.get(comp.year),
                "aliquota_efetiva": aliq_ef, "aliquota_aplicada": aliq_apl,
                "rat_aplicavel": rat_aplicavel,
            },
            autor=autor,
            conferido_por=conferidas_antes.get(comp, (None, None))[0],
        )

    await db.commit()
    revogadas = sum(1 for c in conferidas_antes if ini <= c <= fim)
    return {"ok": True, "competencias": total, "em_fila": em_fila,
            "eventos_registrados": eventos_gravados,
            "conferencias_revogadas": revogadas,
            "aviso": (f"{revogadas} competência(s) tinham sido conferidas e voltaram a apurado: "
                      f"o dado de cálculo mudou, então a validação anterior não vale mais.")
                     if revogadas else None}
