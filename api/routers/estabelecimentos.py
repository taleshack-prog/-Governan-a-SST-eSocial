# api/routers/estabelecimentos.py — SST ESOCIAL GOV
# Adendo 04: o estabelecimento guarda identificacao/natureza/datas; o enquadramento (grau/RAT)
# e DERIVADO da atividade preponderante (RN-20) — não é campo escolhido. A entrada do motor é a
# lista de atividades com quantitativo por periodo (RF-0.173).
import re
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel

from api.database import get_db
from api.models.estabelecimento import Estabelecimento
from api.models.estabelecimento_fap import EstabelecimentoFAP
from api.models.estabelecimento_atividade import EstabelecimentoAtividade
from api.models.estabelecimento_enquadramento import EstabelecimentoEnquadramento
from api.models.estabelecimento_rat_aplicado import EstabelecimentoRatAplicado
from api.models.estabelecimento_fpas_periodo import EstabelecimentoFpasPeriodo
from api.models.cnae_enquadramento import CnaeEnquadramento
from api.models.tabela_fpas import TabelaFPAS
from api.models.usuario import Usuario
from api.auth import get_current_user, require_perfil, require_papel
from api.services.enquadramento_situacao import (
    situacao_de, divergencia_de, origem_divergencia, divergencia_amparada, ROTULO_ORIGEM,
)
from api.services.fundamentacao import citacoes_do_periodo
from api.models.enquadramento_evento import EnquadramentoEvento, ROTULO_EVENTO
from api.services.enquadramento_eventos import registrar_ato_humano, retrato

router = APIRouter()

TIPOS_ESTABELECIMENTO = ("CNPJ", "CNO", "CAEPF")   # RF-0.171
POSICOES = ("matriz", "filial", "obra")
STATUS_VALIDOS = ("ativa", "paralisada", "encerrada")
GRAU_LABEL = {1: "leve", 2: "médio", 3: "grave"}


def _autor(u: Usuario) -> str:
    """Quem assina. Nunca "sistema": o estado conferido registra pessoa."""
    return getattr(u, "email", None) or getattr(u, "nome", None) or str(getattr(u, "id", "?"))


def _sem_sobreposicao(periodos: list, rotulo: str) -> None:
    """Periodos de um mesmo estabelecimento nao podem se sobrepor.

    O motor pega o PRIMEIRO periodo vigente na competencia: com sobreposicao o resultado
    dependeria da ordem das linhas no banco. Em documento com peso juridico isso e inaceitavel —
    melhor recusar a gravacao e dizer onde esta o conflito.
    """
    ordenados = sorted(periodos, key=lambda p: p.inicio)
    for ant, prox in zip(ordenados, ordenados[1:]):
        if ant.fim is None or ant.fim >= prox.inicio:
            fim_txt = "em aberto" if ant.fim is None else ant.fim.strftime("%m/%Y")
            raise HTTPException(
                status_code=422,
                detail=(f"Períodos de {rotulo} sobrepostos: o que começa em "
                        f"{ant.inicio.strftime('%m/%Y')} ({fim_txt}) invade o que começa em "
                        f"{prox.inicio.strftime('%m/%Y')}. Feche o anterior antes de abrir o próximo."),
            )


def _cnpj_valido(v: str | None) -> bool:
    c = re.sub(r"\D", "", v or "")
    if len(c) != 14 or len(set(c)) == 1:
        return False
    def dv(base: str) -> int:
        pesos = [5,4,3,2,9,8,7,6,5,4,3,2] if len(base) == 12 else [6,5,4,3,2,9,8,7,6,5,4,3,2]
        s = sum(int(d) * p for d, p in zip(base, pesos))
        r = s % 11
        return 0 if r < 2 else 11 - r
    return dv(c[:12]) == int(c[12]) and dv(c[:13]) == int(c[13])


def _validar(data) -> None:
    if data.tipo_estabelecimento not in TIPOS_ESTABELECIMENTO:
        raise HTTPException(status_code=422, detail="Natureza deve ser CNPJ, CNO ou CAEPF.")
    if data.posicao not in POSICOES:
        raise HTTPException(status_code=422, detail="Posição deve ser matriz, filial ou obra.")
    if data.status not in STATUS_VALIDOS:
        raise HTTPException(status_code=422, detail="Status inválido.")
    if data.tipo_estabelecimento == "CNPJ" and not _cnpj_valido(data.cnpj):
        raise HTTPException(status_code=422, detail="CNPJ obrigatório e válido (dígito verificador) para natureza CNPJ.")
    if data.tipo_estabelecimento == "CNO" and not (data.identificador and data.identificador.strip()):
        raise HTTPException(status_code=422, detail="Matrícula CNO obrigatória para natureza CNO.")
    if not data.data_abertura:
        raise HTTPException(status_code=422, detail="Data de abertura é obrigatória.")


def _to_dict(e: Estabelecimento) -> dict:
    return {
        "id": str(e.id), "codigo": e.codigo, "nome": e.nome,
        "tipo_estabelecimento": e.tipo_estabelecimento, "posicao": e.posicao,
        "cnpj": e.cnpj, "identificador": e.identificador,
        "status": e.status, "cidade": e.cidade, "uf": e.uf, "endereco": e.endereco,
        # Endereço estruturado (item 5), mesma forma da tela da empresa — entra na memória
        "cep": e.cep, "numero": e.numero, "complemento": e.complemento, "bairro": e.bairro,
        "data_abertura": e.data_abertura.isoformat() if e.data_abertura else None,
        "data_encerramento": e.data_encerramento.isoformat() if e.data_encerramento else None,
    }


class EstabelecimentoIn(BaseModel):
    codigo: str
    nome: str
    tipo_estabelecimento: str = "CNPJ"
    posicao: str = "filial"
    cnpj: str | None = None
    identificador: str | None = None
    status: str = "ativa"
    endereco: str | None = None          # logradouro
    cep: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    uf: str | None = None
    data_abertura: date | None = None
    data_encerramento: date | None = None


async def _enquadramento_corrente(estab_ids: list, db: AsyncSession) -> dict:
    """Enquadramento APURADO da competencia corrente, por estabelecimento (item 2 da revisao).

    'Corrente' = a competencia mais recente ja decorrida. Se a serie inteira ainda esta no futuro
    (janela de apuracao que comeca adiante), devolve a primeira — nunca nada, e sempre dizendo A
    QUAL competencia o numero se refere, porque grau e RAT mudam mes a mes.

    Le a SERIE APURADA, nao as colunas estaticas estabelecimentos.grau_risco/aliquota_rat: aquelas
    sao resquicio de quando o enquadramento era campo escolhido, nunca foram preenchidas pelo
    motor, e mostra-las seria exibir um valor que ninguem calculou.
    """
    if not estab_ids:
        return {}
    E = EstabelecimentoEnquadramento
    hoje = date.today().replace(day=1)

    # 1) ultima competencia ja decorrida (o caso normal)
    decorridas = (await db.execute(
        select(E).where(E.estabelecimento_id.in_(estab_ids), E.competencia <= hoje)
        .order_by(E.estabelecimento_id, E.competencia.desc())
        .distinct(E.estabelecimento_id)
    )).scalars().all()
    por_estab = {str(r.estabelecimento_id): r for r in decorridas}

    # 2) quem nao tem competencia decorrida: primeira da serie
    faltantes = [i for i in estab_ids if str(i) not in por_estab]
    if faltantes:
        futuras = (await db.execute(
            select(E).where(E.estabelecimento_id.in_(faltantes))
            .order_by(E.estabelecimento_id, E.competencia.asc())
            .distinct(E.estabelecimento_id)
        )).scalars().all()
        for r in futuras:
            por_estab[str(r.estabelecimento_id)] = r

    out = {}
    for k, r in por_estab.items():
        devida = float(r.aliquota_devida) if r.aliquota_devida is not None else None
        efetiva = float(r.aliquota_efetiva) if r.aliquota_efetiva is not None else None
        aplicada = float(r.aliquota_aplicada) if r.aliquota_aplicada is not None else None
        fap_dev = float(r.fap) if r.fap is not None else None
        rat_apl = float(r.rat_aplicado) if r.rat_aplicado is not None else None
        fap_apl = float(r.fap_aplicado) if r.fap_aplicado is not None else None
        orig = origem_divergencia(devida, fap_dev, rat_apl, fap_apl)
        out[k] = {
            "competencia": r.competencia.isoformat(),
            "grau_risco": r.grau_risco,
            "grau_label": GRAU_LABEL.get(r.grau_risco or 0, ""),
            "aliquota_devida": devida,
            "fap": fap_dev,
            "aliquota_efetiva": efetiva,
            "aliquota_aplicada": aplicada,
            "rat_aplicado": rat_apl,
            "fap_aplicado": fap_apl,
            "divergencia_pp": divergencia_de(efetiva, aplicada),
            "origem_divergencia": orig,
            "amparada": divergencia_amparada(orig, r.processo_rat, r.processo_fap),
            "situacao": situacao_de(rat_aplicavel=r.rat_aplicavel, em_fila=r.em_fila,
                                    aliquota_devida=devida, conferido_por=r.conferido_por),
            "rat_aplicavel": bool(r.rat_aplicavel),
            "motivo_inaplicavel": r.motivo_inaplicavel,
            "conferido_por": r.conferido_por,
            "conferido_em": r.conferido_em.isoformat() if r.conferido_em else None,
            "motivo_fila": r.motivo_fila,
        }
    return out


async def _completude(estab_ids: list, db: AsyncSession) -> dict:
    """Quais insumos cada estabelecimento já tem (item 10 da revisão).

    Com uma construtora de quarenta obras, descobrir o que falta abrindo um por um é inviável.
    Três marcas: atividade cadastrada, FAP informado e RAT aplicado declarado.
    """
    if not estab_ids:
        return {}
    async def ids_com(modelo):
        rows = (await db.execute(
            select(modelo.estabelecimento_id).where(modelo.estabelecimento_id.in_(estab_ids)).distinct()
        )).scalars().all()
        return {str(i) for i in rows}
    com_ativ = await ids_com(EstabelecimentoAtividade)
    com_fap = await ids_com(EstabelecimentoFAP)
    com_rat = await ids_com(EstabelecimentoRatAplicado)
    com_fpas = await ids_com(EstabelecimentoFpasPeriodo)
    return {str(i): {
        "atividade": str(i) in com_ativ,
        "fap": str(i) in com_fap,
        "rat_aplicado": str(i) in com_rat,
        "fpas": str(i) in com_fpas,
    } for i in estab_ids}


@router.get("/")
async def listar_estabelecimentos(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(Estabelecimento).where(Estabelecimento.empresa_id == current_user.empresa_id)
        .order_by(Estabelecimento.codigo)
    )
    estabs = list(result.scalars())
    ids = [e.id for e in estabs]
    corrente = await _enquadramento_corrente(ids, db)
    completo = await _completude(ids, db)
    saida = []
    for e in estabs:
        d = _to_dict(e)
        d["enquadramento_atual"] = corrente.get(str(e.id))   # None = serie ainda nao apurada
        d["completude"] = completo.get(str(e.id))
        saida.append(d)
    return saida


@router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_estabelecimento(
    data: EstabelecimentoIn,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    _validar(data)
    existente = (await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.empresa_id == current_user.empresa_id,
            Estabelecimento.codigo == data.codigo,
        )
    )).scalar_one_or_none()
    if existente:
        raise HTTPException(status_code=409, detail="Já existe um estabelecimento com este código.")
    e = Estabelecimento(empresa_id=current_user.empresa_id, **data.model_dump())
    db.add(e)
    await db.commit()
    await db.refresh(e)
    return _to_dict(e)


@router.put("/{estab_id}")
async def atualizar_estabelecimento(
    estab_id: UUID,
    data: EstabelecimentoIn,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    _validar(data)
    e = (await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.id == estab_id, Estabelecimento.empresa_id == current_user.empresa_id
        )
    )).scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail="Estabelecimento não encontrado.")
    for k, v in data.model_dump().items():
        setattr(e, k, v)
    await db.commit()
    await db.refresh(e)
    return _to_dict(e)


# ---- Lista de atividades com quantitativo por período (RF-0.173) ----
class AtividadeIn(BaseModel):
    cnae: str
    descricao: str | None = None
    quantitativo: int | None = None
    inicio: date
    fim: date | None = None


async def _tenant_estab(estab_id: UUID, current_user: Usuario, db: AsyncSession) -> Estabelecimento:
    e = (await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.id == estab_id, Estabelecimento.empresa_id == current_user.empresa_id
        )
    )).scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail="Estabelecimento não encontrado.")
    return e


@router.get("/{estab_id}/atividades")
async def listar_atividades(
    estab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _tenant_estab(estab_id, current_user, db)
    rows = (await db.execute(
        select(EstabelecimentoAtividade).where(EstabelecimentoAtividade.estabelecimento_id == estab_id)
        .order_by(EstabelecimentoAtividade.vigencia_inicio)
    )).scalars().all()
    return [{"cnae": r.cnae, "descricao": r.descricao, "quantitativo": r.quantitativo,
             "inicio": r.vigencia_inicio.isoformat(), "fim": r.vigencia_fim.isoformat() if r.vigencia_fim else None,
             "declarado_por": r.declarado_por} for r in rows]


@router.put("/{estab_id}/atividades")
async def salvar_atividades(
    estab_id: UUID,
    data: list[AtividadeIn],
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """Substitui a lista de atividades. Rejeita CNAE inexistente no Anexo I (RF-0.173).
    Grava autoria (RN-23)."""
    await _tenant_estab(estab_id, current_user, db)
    for it in data:
        cnae = re.sub(r"\D", "", it.cnae or "")
        if len(cnae) != 7:
            raise HTTPException(status_code=422, detail=f"CNAE '{it.cnae}' deve ter 7 dígitos.")
        existe = (await db.execute(
            select(CnaeEnquadramento.cnae).where(CnaeEnquadramento.cnae == cnae)
        )).scalar_one_or_none()
        if not existe:
            raise HTTPException(status_code=422, detail=f"CNAE {cnae} não existe no Anexo I. Confira a subclasse.")
        if it.fim and it.fim < it.inicio:
            raise HTTPException(status_code=422, detail="Atividade com fim anterior ao início.")
    declarante = getattr(current_user, "email", None) or getattr(current_user, "nome", None)
    antigas = (await db.execute(
        select(EstabelecimentoAtividade).where(EstabelecimentoAtividade.estabelecimento_id == estab_id)
    )).scalars().all()
    for a in antigas:
        await db.delete(a)
    for it in data:
        db.add(EstabelecimentoAtividade(
            estabelecimento_id=estab_id, cnae=re.sub(r"\D", "", it.cnae), descricao=it.descricao,
            quantitativo=it.quantitativo, vigencia_inicio=it.inicio, vigencia_fim=it.fim,
            declarado_por=declarante, declarado_em=datetime.utcnow(),
        ))
    await db.commit()
    from api.services.motor_enquadramento import apurar_estabelecimento
    await apurar_estabelecimento(estab_id, db, autor=_autor(current_user))   # reapura a série ao mudar as atividades
    return {"ok": True, "total": len(data)}


# ---- FAP por ano (RF-0.177) ----
class FapAnoIn(BaseModel):
    ano: int
    fap: float


@router.get("/{estab_id}/fap")
async def listar_fap(
    estab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _tenant_estab(estab_id, current_user, db)
    rows = (await db.execute(
        select(EstabelecimentoFAP).where(EstabelecimentoFAP.estabelecimento_id == estab_id)
        .order_by(EstabelecimentoFAP.ano_vigencia)
    )).scalars().all()
    return [{"ano": r.ano_vigencia, "fap": float(r.valor_fap)} for r in rows]


@router.put("/{estab_id}/fap")
async def salvar_fap(
    estab_id: UUID,
    faps: list[FapAnoIn],
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """FAP por ano (0,5 a 2,0). Campo vazio não é 1,0 — simplesmente não é enviado."""
    await _tenant_estab(estab_id, current_user, db)
    for item in faps:
        if not (0.5 <= item.fap <= 2.0):
            raise HTTPException(status_code=422, detail=f"FAP {item.fap} fora da faixa 0,5–2,0 (ano {item.ano}).")
        existe = (await db.execute(
            select(EstabelecimentoFAP).where(
                EstabelecimentoFAP.estabelecimento_id == estab_id,
                EstabelecimentoFAP.ano_vigencia == item.ano,
            )
        )).scalar_one_or_none()
        if existe:
            existe.valor_fap = item.fap
            existe.origem = "declarado"
            existe.declarado_em = datetime.utcnow()
        else:
            db.add(EstabelecimentoFAP(estabelecimento_id=estab_id, ano_vigencia=item.ano, valor_fap=item.fap,
                                      origem="declarado", declarado_em=datetime.utcnow()))
    await db.commit()
    from api.services.motor_enquadramento import apurar_estabelecimento
    await apurar_estabelecimento(estab_id, db, autor=_autor(current_user))   # reapura a série ao mudar o FAP
    return {"ok": True, "salvos": len(faps)}


# ---- RAT aplicado pela empresa, por período (RF-0.179 / item 1 da revisão) ----
# Este é o único número do enquadramento que o sistema NÃO calcula: é o que a empresa de fato
# usou na folha dela. Preenchê-lo automaticamente destruiria o produto — a diferença entre ele e
# a alíquota efetiva é o achado. Por isso: sem valor padrão, sem sugestão, sem herdar do devido.
# Desdobrado em GRAU e FATOR (item 1 da revisão): o eSocial valida no S-1005 que aliqRatAjust é
# o produto de aliqRat por fap, então o erro nunca está no ajustado — está numa das duas origens,
# e a resposta decide a defesa.
class RatAplicadoIn(BaseModel):
    aliquota_rat: float | None = None       # 1 | 2 | 3
    fap_aplicado: float | None = None       # 0,5000 a 2,0000
    aliquota: float | None = None           # efetiva; só para linha antiga, sem desdobramento
    processo_rat: str | None = None
    processo_fap: str | None = None
    inicio: date
    fim: date | None = None


@router.get("/{estab_id}/rat-aplicado")
async def listar_rat_aplicado(
    estab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _tenant_estab(estab_id, current_user, db)
    rows = (await db.execute(
        select(EstabelecimentoRatAplicado)
        .where(EstabelecimentoRatAplicado.estabelecimento_id == estab_id)
        .order_by(EstabelecimentoRatAplicado.inicio)
    )).scalars().all()
    return [{
        "aliquota": float(r.aliquota),
        "aliquota_rat": float(r.aliquota_rat) if r.aliquota_rat is not None else None,
        "fap_aplicado": float(r.fap_aplicado) if r.fap_aplicado is not None else None,
        "processo_rat": r.processo_rat, "processo_fap": r.processo_fap,
        # true = linha antiga, que guarda só a efetiva. A tela pede o desdobramento; o sistema
        # NÃO infere o par, porque rat=3/fap=1,0 seria valor presumido.
        "sem_desdobramento": r.aliquota_rat is None,
        "inicio": r.inicio.isoformat(), "fim": r.fim.isoformat() if r.fim else None,
    } for r in rows]


@router.put("/{estab_id}/rat-aplicado")
async def salvar_rat_aplicado(
    estab_id: UUID,
    data: list[RatAplicadoIn],
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """Substitui a lista de períodos do RAT aplicado. Reapura a série ao final.

    Aceita o período desdobrado (RAT + FAP, o normal) ou, só para compatibilidade com o que já
    estava gravado, a efetiva isolada. O par é tudo-ou-nada: meio desdobramento não diz qual
    origem errou, que é justamente o que o campo existe para responder.
    """
    await _tenant_estab(estab_id, current_user, db)
    resolvidos = []
    for it in data:
        if it.fim and it.fim < it.inicio:
            raise HTTPException(status_code=422, detail="Período com fim anterior ao início.")
        tem_rat, tem_fap = it.aliquota_rat is not None, it.fap_aplicado is not None
        if tem_rat != tem_fap:
            raise HTTPException(
                status_code=422,
                detail=("Informe a alíquota RAT e o FAP aplicados juntos. Só um dos dois não "
                        "permite dizer qual origem causou a divergência — que é o motivo de o "
                        "campo ser desdobrado."),
            )
        if tem_rat:
            if float(it.aliquota_rat) not in (1.0, 2.0, 3.0):
                raise HTTPException(
                    status_code=422,
                    detail=(f"Alíquota RAT aplicada deve ser 1, 2 ou 3 (grau leve, médio ou "
                            f"grave). Recebido: {it.aliquota_rat}."),
                )
            if not (0.5 <= float(it.fap_aplicado) <= 2.0):
                raise HTTPException(
                    status_code=422,
                    detail=f"FAP aplicado {it.fap_aplicado} fora da faixa 0,5000–2,0000.",
                )
            efetiva = round(float(it.aliquota_rat) * float(it.fap_aplicado), 4)
        else:
            if it.aliquota is None:
                raise HTTPException(
                    status_code=422,
                    detail="Informe a alíquota RAT e o FAP aplicados no período.",
                )
            # Faixa possível da efetiva: 1×0,5 = 0,5% até 3×2,0 = 6,0%. Fora disso não é um RAT,
            # é erro de digitação — e um erro aqui vira achado fantasma de milhões.
            if not (0.5 <= float(it.aliquota) <= 6.0):
                raise HTTPException(
                    status_code=422,
                    detail=(f"Alíquota efetiva {it.aliquota}% fora da faixa possível "
                            f"(0,50% a 6,00% = RAT × FAP)."),
                )
            efetiva = round(float(it.aliquota), 4)
        resolvidos.append((it, efetiva))
    _sem_sobreposicao([it for it, _ in resolvidos], "RAT aplicado")

    antigos = (await db.execute(
        select(EstabelecimentoRatAplicado)
        .where(EstabelecimentoRatAplicado.estabelecimento_id == estab_id)
    )).scalars().all()
    for a in antigos:
        await db.delete(a)
    for it, efetiva in resolvidos:
        db.add(EstabelecimentoRatAplicado(
            estabelecimento_id=estab_id, aliquota=efetiva,
            aliquota_rat=it.aliquota_rat, fap_aplicado=it.fap_aplicado,
            processo_rat=(it.processo_rat or None), processo_fap=(it.processo_fap or None),
            inicio=it.inicio, fim=it.fim,
        ))
    await db.commit()
    from api.services.motor_enquadramento import apurar_estabelecimento
    await apurar_estabelecimento(estab_id, db, autor=_autor(current_user))
    return {"ok": True, "periodos": len(data)}


# ---- FPAS por período (item 4 da revisão) ----
# O FPAS determina a composição de Terceiros, e essa composição muda dentro da janela — daí o
# período. As opções vêm do Anexo III (tabela de referência, global); a escolha é declarada.
class FpasPeriodoIn(BaseModel):
    codigo_fpas: str
    inicio: date
    fim: date | None = None


@router.get("/{estab_id}/fpas")
async def listar_fpas_estab(
    estab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    estab = await _tenant_estab(estab_id, current_user, db)
    rows = (await db.execute(
        select(EstabelecimentoFpasPeriodo)
        .where(EstabelecimentoFpasPeriodo.estabelecimento_id == estab_id)
        .order_by(EstabelecimentoFpasPeriodo.inicio)
    )).scalars().all()
    # A alíquota de cada período é lida NA VIGÊNCIA DAQUELE PERÍODO, não "a atual" — a tabela
    # tem três vigências dentro da janela, e aplicar a de hoje ao passado erra sem emitir erro.
    from api.services.terceiros import aliquota_em
    por_periodo = {}
    for r in rows:
        por_periodo[r.id] = await aliquota_em(r.codigo_fpas, r.inicio, db)
    # Janela sugerida para um período NOVO (item 3): o padrão é a apuração inteira, recortada
    # pela vida do estabelecimento. Nascendo com um mês só, 59 das 60 competências ficariam sem
    # FPAS informado — e o usuário não tem como adivinhar que precisa esticar o período.
    from api.models.empresa import Empresa
    empresa = (await db.execute(select(Empresa).where(Empresa.id == estab.empresa_id))).scalar_one_or_none()
    p_ini = (empresa.periodo_apuracao_inicio if empresa else None) or estab.data_abertura
    p_fim = (empresa.periodo_apuracao_fim if empresa else None)
    if p_ini and estab.data_abertura:
        p_ini = max(p_ini, estab.data_abertura)
    if p_fim and estab.data_encerramento:
        p_fim = min(p_fim, estab.data_encerramento)
    return {
        "janela_sugerida": {
            "inicio": p_ini.isoformat() if p_ini else None,
            "fim": p_fim.isoformat() if p_fim else None,
        },
        "periodos": [{
            "codigo_fpas": r.codigo_fpas,
            "descricao": por_periodo[r.id]["descricao"],
            "aliquota_terceiros": por_periodo[r.id]["aliquota_terceiros"],
            # A fonte viaja junto: o laudo cita o fundamento, e o fundamento muda.
            "fonte": por_periodo[r.id]["fonte"],
            "vigencia_aplicada": por_periodo[r.id]["vigencia_inicio"],
            "em_conferencia": por_periodo[r.id]["em_conferencia"],
            "motivo": por_periodo[r.id]["motivo"],
            "inicio": r.inicio.isoformat(), "fim": r.fim.isoformat() if r.fim else None,
            "declarado_por": r.declarado_por,
        } for r in rows],
    }


@router.put("/{estab_id}/fpas")
async def salvar_fpas_estab(
    estab_id: UUID,
    data: list[FpasPeriodoIn],
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """Substitui a lista de períodos de FPAS. Recusa código fora do Anexo III (RF-0.182)."""
    await _tenant_estab(estab_id, current_user, db)
    for it in data:
        # Existência do CÓDIGO, em qualquer vigência — não da alíquota de uma competência.
        # Desde a migration 038 a chave é (codigo_fpas, vigencia_inicio), então scalar_one_or_none()
        # levantaria MultipleResultsFound (500) no código que tivesse mais de uma vigência, que é
        # o caso assim que a carga da IN RFB 2.321/2026 entrar. first() é o que esta checagem
        # sempre quis dizer.
        existe = (await db.execute(
            select(TabelaFPAS.codigo_fpas).where(TabelaFPAS.codigo_fpas == it.codigo_fpas).limit(1)
        )).scalars().first()
        if not existe:
            raise HTTPException(
                status_code=422,
                detail=f"FPAS {it.codigo_fpas} não existe no Anexo III da IN RFB 2.110/2022.",
            )
        if it.fim and it.fim < it.inicio:
            raise HTTPException(status_code=422, detail="Período com fim anterior ao início.")
    _sem_sobreposicao(data, "FPAS")

    declarante = getattr(current_user, "email", None) or getattr(current_user, "nome", None)
    antigos = (await db.execute(
        select(EstabelecimentoFpasPeriodo)
        .where(EstabelecimentoFpasPeriodo.estabelecimento_id == estab_id)
    )).scalars().all()
    for a in antigos:
        await db.delete(a)
    for it in data:
        db.add(EstabelecimentoFpasPeriodo(
            estabelecimento_id=estab_id, codigo_fpas=it.codigo_fpas,
            inicio=it.inicio, fim=it.fim,
            declarado_por=declarante, declarado_em=datetime.utcnow(),
        ))
    await db.commit()
    return {"ok": True, "periodos": len(data)}


# ---- Motor de apuração do enquadramento (RF-0.175-182) ----
@router.post("/{estab_id}/apurar")
async def apurar(
    estab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """Recalcula a série mensal de enquadramento (preponderância → grau → RAT × FAP)."""
    await _tenant_estab(estab_id, current_user, db)
    from api.services.motor_enquadramento import apurar_estabelecimento
    return await apurar_estabelecimento(estab_id, db, autor=_autor(current_user))


@router.get("/{estab_id}/enquadramento")
async def serie_enquadramento(
    estab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Série apurada por competência (somente leitura).

    Divergência = aplicado − alíquota EFETIVA (RAT × FAP), que é o que a folha recolhe.
    Situação em três estados (conferência / apurado / conferido): ver enquadramento_situacao.py.
    """
    await _tenant_estab(estab_id, current_user, db)
    rows = (await db.execute(
        select(EstabelecimentoEnquadramento).where(EstabelecimentoEnquadramento.estabelecimento_id == estab_id)
        .order_by(EstabelecimentoEnquadramento.competencia)
    )).scalars().all()
    out = []
    for r in rows:
        devida = float(r.aliquota_devida) if r.aliquota_devida is not None else None
        apl = float(r.aliquota_aplicada) if r.aliquota_aplicada is not None else None
        efet = float(r.aliquota_efetiva) if r.aliquota_efetiva is not None else None
        fap_dev = float(r.fap) if r.fap is not None else None
        rat_apl = float(r.rat_aplicado) if r.rat_aplicado is not None else None
        fap_apl = float(r.fap_aplicado) if r.fap_aplicado is not None else None
        orig = origem_divergencia(devida, fap_dev, rat_apl, fap_apl)
        out.append({
            "competencia": r.competencia.isoformat(),
            "cnae_preponderante": r.cnae_preponderante,
            "criterio": r.criterio,
            "grau_risco": r.grau_risco,
            "grau_label": GRAU_LABEL.get(r.grau_risco or 0, ""),
            "aliquota_devida": devida,
            "fap": fap_dev,
            "aliquota_efetiva": efet,
            "aliquota_aplicada": apl,
            # As duas origens aplicadas + de qual veio a divergência (item 1 da revisão)
            "rat_aplicado": rat_apl,
            "fap_aplicado": fap_apl,
            "origem_divergencia": orig,
            "origem_label": ROTULO_ORIGEM.get(orig) if orig else None,
            "amparada": divergencia_amparada(orig, r.processo_rat, r.processo_fap),
            "processo_rat": r.processo_rat,
            "processo_fap": r.processo_fap,
            "divergencia_pp": divergencia_de(efet, apl),
            "situacao": situacao_de(rat_aplicavel=r.rat_aplicavel, em_fila=r.em_fila,
                                    aliquota_devida=devida, conferido_por=r.conferido_por),
            "rat_aplicavel": bool(r.rat_aplicavel),
            "motivo_inaplicavel": r.motivo_inaplicavel,
            "conferido_por": r.conferido_por,
            "conferido_em": r.conferido_em.isoformat() if r.conferido_em else None,
            "revogado_em": r.revogado_em.isoformat() if r.revogado_em else None,
            "revogado_de": r.revogado_de,
            "em_fila": r.em_fila,
            "motivo_fila": r.motivo_fila,
            # SEM 'fundamentacao' na linha. A citacao nao e dado da competencia: a tela pergunta
            # a /fundamentacao/{campo}?em=<competencia>, que le a tabela versionada na data certa.
            # Enquanto vinha daqui, o rodape da tela mostrava o texto congelado na primeira linha
            # da serie — sem data — como se valesse para todos os anos exibidos.
        })
    return out


# ---- Conferência: o ato humano (itens 1 e 2 da revisão de 19/10) ----
# Este é o único lugar do sistema que grava "conferido". O motor não assina: conferir é ato
# profissional, e é precisamente onde o cliente paga para alguém assinar embaixo. A competência
# com pendência não pode ser conferida — não há o que validar.
class ConferenciaIn(BaseModel):
    competencias: list[date] | None = None   # None = todas as apuradas da janela
    observacao: str | None = None


@router.post("/{estab_id}/conferir")
async def conferir_competencias(
    estab_id: UUID,
    data: ConferenciaIn,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_papel("operador")),
):
    """Registra que uma PESSOA examinou e validou as competências, com autor e data.

    Recusa competência em conferência: validar o que o motor não conseguiu apurar seria assinar
    sobre um número que não existe.
    """
    await _tenant_estab(estab_id, current_user, db)
    E = EstabelecimentoEnquadramento
    q = select(E).where(E.estabelecimento_id == estab_id)
    if data.competencias:
        q = q.where(E.competencia.in_(data.competencias))
    rows = (await db.execute(q)).scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="Nenhuma competência encontrada para conferir.")

    pendentes = [r for r in rows if r.em_fila or r.aliquota_devida is None]
    if pendentes and data.competencias:
        comps = ", ".join(r.competencia.strftime("%m/%Y") for r in pendentes[:5])
        raise HTTPException(
            status_code=422,
            detail=(f"Não é possível conferir competência em conferência: {comps}"
                    f"{'…' if len(pendentes) > 5 else ''}. "
                    f"Resolva a pendência (FAP, atividade, CNAE) antes de validar."),
        )

    autor = _autor(current_user)
    agora = datetime.now(timezone.utc)
    conferidas = 0
    for r in rows:
        if r.em_fila or r.aliquota_devida is None:
            continue                       # pendente: fica de fora, sem erro, numa conferência em lote
        r.conferido_por = autor
        r.conferido_em = agora
        r.revogado_em = r.revogado_por = r.revogado_de = None
        conferidas += 1
        # TRILHA (047): o valor vai JUNTO do ato. Era o nucleo do pedido — o sistema sabia que
        # alguem havia conferido e nao sabia dizer sobre qual numero.
        await registrar_ato_humano(
            db, estabelecimento_id=estab_id, competencia=r.competencia, conferindo=True,
            valores=retrato(r), autor=autor, observacao=data.observacao,
        )
    await db.commit()
    return {"ok": True, "conferidas": conferidas,
            "ignoradas_por_pendencia": len(rows) - conferidas,
            "conferido_por": autor, "conferido_em": agora.isoformat()}


@router.post("/{estab_id}/desconferir")
async def desconferir_competencias(
    estab_id: UUID,
    data: ConferenciaIn,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_papel("operador")),
):
    """Retira a validação humana, devolvendo as competências a apurado."""
    await _tenant_estab(estab_id, current_user, db)
    E = EstabelecimentoEnquadramento
    q = select(E).where(E.estabelecimento_id == estab_id, E.conferido_por.isnot(None))
    if data.competencias:
        q = q.where(E.competencia.in_(data.competencias))
    rows = (await db.execute(q)).scalars().all()
    autor = _autor(current_user)
    agora = datetime.now(timezone.utc)
    for r in rows:
        r.revogado_de = r.conferido_por
        r.revogado_em = agora
        r.revogado_por = autor
        # O retrato guarda o numero que estava validado ate este instante. Ele NAO inclui os
        # campos de conferencia, entao gravar antes ou depois de limpa-los da no mesmo — fica
        # antes por clareza de leitura, nao por necessidade.
        await registrar_ato_humano(
            db, estabelecimento_id=estab_id, competencia=r.competencia, conferindo=False,
            valores=retrato(r), autor=autor, observacao=data.observacao,
        )
        r.conferido_por = None
        r.conferido_em = None
    await db.commit()
    return {"ok": True, "desconferidas": len(rows)}


# ---- Trilha de eventos do enquadramento (migration 047) ----
@router.get("/{estab_id}/eventos")
async def eventos_enquadramento(
    estab_id: UUID,
    competencia: date | None = Query(
        None, description="Filtra uma competência. Omitido, traz a trilha do estabelecimento."),
    limite: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """O que aconteceu com uma competência, do mais recente para o mais antigo.

    Cada linha traz o VALOR DAQUELE INSTANTE, não o valor de hoje: é o que permite ler uma
    conferência antiga e saber sobre o que ela foi dada, mesmo depois de a competência ter sido
    recalculada várias vezes.
    """
    await _tenant_estab(estab_id, current_user, db)
    q = select(EnquadramentoEvento).where(EnquadramentoEvento.estabelecimento_id == estab_id)
    if competencia:
        q = q.where(EnquadramentoEvento.competencia == competencia)
    linhas = (await db.execute(
        q.order_by(EnquadramentoEvento.ocorrido_em.desc()).limit(limite)
    )).scalars().all()

    def _n(v):
        return float(v) if v is not None else None

    return [{
        "id": str(e.id),
        "competencia": e.competencia.isoformat(),
        "evento": e.evento,
        "evento_label": ROTULO_EVENTO.get(e.evento, e.evento),
        "autor": e.autor,
        "ocorrido_em": e.ocorrido_em.isoformat() if e.ocorrido_em else None,
        # O retrato do cálculo naquele instante — é o que torna a conferência uma assinatura
        # sobre um número determinado, e não só uma marca de que alguém olhou.
        "grau_risco": e.grau_risco,
        "aliquota_devida": _n(e.aliquota_devida),
        "fap": _n(e.fap),
        "aliquota_efetiva": _n(e.aliquota_efetiva),
        "aliquota_aplicada": _n(e.aliquota_aplicada),
        "rat_aplicavel": e.rat_aplicavel,
        "alteracoes": e.alteracoes,
        "motivo": e.motivo,
    } for e in linhas]


# ---- Memória de enquadramento em PDF (RF-0.183) ----
@router.get("/{estab_id}/memoria")
async def memoria_enquadramento(
    estab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from datetime import datetime
    from api.models.empresa import Empresa
    from api.models.empresa_cprb import EmpresaCprb
    from api.services.memoria_enquadramento import gerar_memoria_pdf
    estab = await _tenant_estab(estab_id, current_user, db)
    empresa = (await db.execute(select(Empresa).where(Empresa.id == estab.empresa_id))).scalar_one_or_none()
    cprb_rows = (await db.execute(
        select(EmpresaCprb).where(EmpresaCprb.empresa_id == estab.empresa_id).order_by(EmpresaCprb.inicio)
    )).scalars().all() if empresa else []
    ativ = (await db.execute(
        select(EstabelecimentoAtividade).where(EstabelecimentoAtividade.estabelecimento_id == estab_id)
        .order_by(EstabelecimentoAtividade.vigencia_inicio)
    )).scalars().all()
    serie_rows = (await db.execute(
        select(EstabelecimentoEnquadramento).where(EstabelecimentoEnquadramento.estabelecimento_id == estab_id)
        .order_by(EstabelecimentoEnquadramento.competencia)
    )).scalars().all()

    serie = []
    for r in serie_rows:
        devida = float(r.aliquota_devida) if r.aliquota_devida is not None else None
        apl = float(r.aliquota_aplicada) if r.aliquota_aplicada is not None else None
        efet = float(r.aliquota_efetiva) if r.aliquota_efetiva is not None else None
        fap_dev = float(r.fap) if r.fap is not None else None
        rat_apl = float(r.rat_aplicado) if r.rat_aplicado is not None else None
        fap_apl = float(r.fap_aplicado) if r.fap_aplicado is not None else None
        orig = origem_divergencia(devida, fap_dev, rat_apl, fap_apl)
        serie.append({
            "competencia": r.competencia.isoformat(), "cnae_preponderante": r.cnae_preponderante,
            "criterio": r.criterio, "grau_risco": r.grau_risco, "aliquota_devida": devida,
            "fap": fap_dev,
            "aliquota_efetiva": efet,
            "aliquota_aplicada": apl,
            "rat_aplicado": rat_apl, "fap_aplicado": fap_apl,
            "origem_divergencia": orig,
            "amparada": divergencia_amparada(orig, r.processo_rat, r.processo_fap),
            "processo_rat": r.processo_rat, "processo_fap": r.processo_fap,
            "divergencia_pp": divergencia_de(efet, apl),
            "situacao": situacao_de(rat_aplicavel=r.rat_aplicavel, em_fila=r.em_fila,
                                    aliquota_devida=devida, conferido_por=r.conferido_por),
            "rat_aplicavel": bool(r.rat_aplicavel),
            "motivo_inaplicavel": r.motivo_inaplicavel,
            "conferido_por": r.conferido_por,
            "conferido_em": r.conferido_em.strftime("%d/%m/%Y") if r.conferido_em else None,
            "em_fila": r.em_fila, "motivo_fila": r.motivo_fila,
        })
    autoria = sorted({f"{a.declarado_por or 'n/d'} em {a.declarado_em.date().isoformat()}"
                      for a in ativ if a.declarado_em})
    # PORTA DE EMISSAO. A fundamentacao vem da tabela versionada, resolvida competencia por
    # competencia (nao mais congelada na linha apurada, nem escrita a mao no gerador). Sem serie
    # apurada nao ha periodo a fundamentar; com qualquer mes sem citacao cadastrada, ha mes que o
    # documento nao sabe fundamentar — e documento sem fundamento nao se completa com texto de
    # reserva, se recusa. Os meses da lacuna vao nomeados na resposta: a recusa tem que dizer o
    # que fazer para deixar de acontecer.
    if not serie_rows:
        raise HTTPException(
            status_code=409,
            detail=("A memória não pode ser emitida: não há série de enquadramento apurada para "
                    "este estabelecimento. Apure a série antes de gerar o documento."),
        )
    fund_blocos = await citacoes_do_periodo(
        "rat_devido", [r.competencia for r in serie_rows], db
    )
    lacunas = [b for b in fund_blocos if b["citacao"] is None]
    if lacunas:
        faixas = "; ".join(
            b["de"].strftime("%m/%Y") + (f" a {b['ate'].strftime('%m/%Y')}" if b["ate"] != b["de"] else "")
            for b in lacunas
        )
        raise HTTPException(
            status_code=409,
            detail=("A memória não pode ser emitida: não há fundamentação cadastrada para o campo "
                    f"'rat_devido' nestas competências: {faixas}. Cadastre a vigência "
                    "correspondente na tabela de fundamentação antes de gerar o documento."),
        )
    dados = {
        "empresa": {"razao_social": empresa.razao_social if empresa else None, "cnpj": (empresa.cnpj[:8] if empresa and empresa.cnpj else None)},
        "estab": {"codigo": estab.codigo, "nome": estab.nome, "tipo": estab.tipo_estabelecimento,
                  "identificador": estab.identificador, "cnpj": estab.cnpj, "posicao": estab.posicao,
                  "abertura": estab.data_abertura.isoformat() if estab.data_abertura else None,
                  "encerramento": estab.data_encerramento.isoformat() if estab.data_encerramento else None,
                  # Endereço estruturado (item 5) — compõe a identificação na memória
                  "endereco": ", ".join(p for p in [
                      estab.endereco, estab.numero, estab.complemento, estab.bairro,
                      f"{estab.cidade}/{estab.uf}" if (estab.cidade and estab.uf) else (estab.cidade or estab.uf),
                      estab.cep,
                  ] if p)},
        "periodo": {"inicio": empresa.periodo_apuracao_inicio.isoformat() if empresa and empresa.periodo_apuracao_inicio else None,
                    "fim": empresa.periodo_apuracao_fim.isoformat() if empresa and empresa.periodo_apuracao_fim else None},
        "atividades": [{"cnae": a.cnae, "descricao": a.descricao, "quantitativo": a.quantitativo,
                        "inicio": a.vigencia_inicio.isoformat(), "fim": a.vigencia_fim.isoformat() if a.vigencia_fim else None} for a in ativ],
        "serie": serie,
        # SEM CITACAO, NAO EMITE — a recusa esta na checagem acima deste dicionario. Aqui havia
        # texto de reserva: nao encontrando a fundamentacao na linha apurada, o gerador escrevia
        # uma citacao fixa e seguia. Isso e um gerador de afirmacao falsa dentro de peca assinada
        # por advogado. Agora o documento leva a COPIA do que a tabela versionada respondeu, por
        # bloco de vigencia, com o intervalo de competencias que cada redacao governa e a data em
        # que foi resolvida: e isso que torna a citacao conferivel depois de emitida.
        "fundamentacao_blocos": [
            {"de": b["de"].isoformat(), "ate": b["ate"].isoformat(),
             "dispositivo": b["citacao"]["dispositivo"],
             "ato": b["citacao"]["ato_normativo"],
             "anexo": b["citacao"]["anexo"],
             "observacao": b["citacao"]["observacao"],
             "estruturado": b["citacao"]["estruturado"],
             "vigencia_inicio": b["citacao"]["vigencia_inicio"],
             "vigencia_fim": b["citacao"]["vigencia_fim"]}
            for b in fund_blocos
        ],
        "autoria": autoria,
        "cprb": {
            "status": (empresa.cprb_status if empresa else None) or "nao_informado",
            "verificado_por": empresa.cprb_verificado_por if empresa else None,
            "verificado_em": empresa.cprb_verificado_em.strftime("%d/%m/%Y") if (empresa and empresa.cprb_verificado_em) else None,
            "periodos": [{"inicio": c.inicio.isoformat(), "fim": c.fim.isoformat() if c.fim else None} for c in cprb_rows],
        },
        "gerado_em": datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"),
    }
    pdf = gerar_memoria_pdf(dados)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename=memoria_enquadramento_{estab.codigo}.pdf"})
