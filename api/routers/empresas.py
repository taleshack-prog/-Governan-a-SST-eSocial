# api/routers/empresas.py — SST ESOCIAL GOV
# Adendo 03: o enquadramento e do ESTABELECIMENTO (matriz), nao da empresa (RN-17).
# A empresa guarda identificacao, periodo de apuracao, regime/CPRB por periodo e contato.
import re
from uuid import UUID
from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel

from api.database import get_db
from api.models.empresa import Empresa
from api.models.estabelecimento import Estabelecimento
from api.models.estabelecimento_atividade import EstabelecimentoAtividade
from api.models.estabelecimento_enquadramento import EstabelecimentoEnquadramento
from api.models.empresa_regime import EmpresaRegime
from api.models.empresa_cprb import EmpresaCprb
from api.models.empresa_cnae_secundario import EmpresaCnaeSecundario
from api.models.cnae_enquadramento import CnaeEnquadramento
from api.models.cnae_fpas_sugestao import CnaeFpasSugestao
from api.models.usuario import Usuario
from api.auth import get_current_user, require_perfil
from api.services.enquadramento_situacao import situacao_de, divergencia_de

router = APIRouter()

GRAU_LABEL = {1: "leve", 2: "médio", 3: "grave"}


# ---------------- helpers ----------------
def _cnpj_dv(base: str) -> int:
    pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] if len(base) == 12 else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s = sum(int(d) * p for d, p in zip(base, pesos))
    r = s % 11
    return 0 if r < 2 else 11 - r


def _cnpj_matriz(cnpj_informado: Optional[str]) -> Optional[str]:
    """Matriz = raiz (8 dígitos) + ordem 0001 + dígitos verificadores (RF-0.152)."""
    d = re.sub(r"\D", "", cnpj_informado or "")
    if len(d) < 8:
        return None
    base = d[:8] + "0001"
    dv1 = _cnpj_dv(base)
    dv2 = _cnpj_dv(base + str(dv1))
    return base + str(dv1) + str(dv2)


def _sem_sobreposicao(periodos: list[tuple[date, Optional[date]]]) -> bool:
    """True se os períodos [inicio, fim] (fim None = aberto) não se sobrepõem."""
    ordenados = sorted(periodos, key=lambda p: p[0])
    for i in range(1, len(ordenados)):
        fim_ant = ordenados[i - 1][1] or date.max
        if ordenados[i][0] <= fim_ant:
            return False
    return True


async def _garantir_matriz(empresa: Empresa, db: AsyncSession, declarante: str | None = None) -> None:
    """RF-0.152: ao salvar a empresa, garante o estabelecimento matriz e registra a atividade
    declarada da matriz (input do motor do Adendo 04). O enquadramento apurado (grau/RAT) é
    resultado do motor, não é gravado aqui."""
    matriz = (await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.empresa_id == empresa.id, Estabelecimento.posicao == "matriz"
        )
    )).scalars().first()
    # abertura da matriz = abertura REAL da empresa (consulta), não o período de apuração (RF-0.152)
    abertura = empresa.data_abertura or empresa.periodo_apuracao_inicio
    if matriz is None:
        matriz = Estabelecimento(
            empresa_id=empresa.id, codigo="MATRIZ", nome=empresa.razao_social or "Matriz",
            cnpj=_cnpj_matriz(empresa.cnpj), cnae=empresa.cnae_principal,
            posicao="matriz", status="ativa", tipo_estabelecimento="CNPJ",
            endereco=empresa.endereco, cidade=empresa.cidade, uf=empresa.uf,
            data_abertura=abertura, data_encerramento=empresa.data_encerramento,
        )
        db.add(matriz)
        await db.flush()
    else:
        if empresa.cnae_principal:
            matriz.cnae = empresa.cnae_principal
        if abertura:
            matriz.data_abertura = abertura
        matriz.data_encerramento = empresa.data_encerramento

    # registra a atividade declarada da matriz (uma linha) — INPUT do motor (RF-0.173)
    if empresa.cnae_principal:
        inicio = abertura or getattr(matriz, "data_abertura", None) or date.today()
        ativ = (await db.execute(
            select(EstabelecimentoAtividade).where(
                EstabelecimentoAtividade.estabelecimento_id == matriz.id,
                EstabelecimentoAtividade.vigencia_fim.is_(None),
            ).order_by(EstabelecimentoAtividade.vigencia_inicio.desc())
        )).scalars().first()
        if ativ is None:
            db.add(EstabelecimentoAtividade(
                estabelecimento_id=matriz.id, cnae=empresa.cnae_principal,
                vigencia_inicio=inicio, declarado_por=declarante,
            ))
        else:
            ativ.cnae = empresa.cnae_principal


# ---------------- schemas ----------------
class EmpresaCreate(BaseModel):
    razao_social: str
    cnpj: str
    cnae_principal: str | None = None
    regime_tributario: str | None = None


class EmpresaUpdate(BaseModel):
    razao_social: str | None = None
    nome_fantasia: str | None = None
    cnpj: str | None = None
    cnae_principal: str | None = None            # usado p/ semear o enquadramento da matriz
    periodo_apuracao_inicio: date | None = None
    periodo_apuracao_fim: date | None = None
    data_abertura: date | None = None
    data_encerramento: date | None = None
    origem_cadastro: str | None = None
    consultado_em: datetime | None = None             # data/hora da consulta (RF-0.150)
    cnaes_secundarios: List[str] | None = None         # lista de códigos, gravada à parte
    endereco: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    uf: str | None = None
    cep: str | None = None
    contato_nome: str | None = None
    contato_email: str | None = None
    contato_telefone: str | None = None


class RegimeItem(BaseModel):
    regime: str
    anexo_simples: str | None = None
    inicio: date
    fim: date | None = None


class CprbItem(BaseModel):
    inicio: date
    fim: date | None = None
    # RF-0.166: fim em branco = "vigente ate hoje". Afirmacao forte -> exige confirmacao
    # explicita; sem ela, o sistema fecha no fim do ano-calendario do inicio.
    fim_confirmado: bool = False


class CprbPayload(BaseModel):
    """RF-0.163: estado explicito da CPRB. Periodos so valem quando status == 'optante'."""
    status: str = "nao_informado"            # nao_informado | nao_optante | optante
    periodos: List[CprbItem] = []


_CPRB_STATUS = {"nao_informado", "nao_optante", "optante"}
_CPRB_LIMITE_FIM = date(2027, 12, 31)        # RF-0.165: extingue em 2028 (Lei 14.973/2024)


def _mesma_competencia(a: Optional[date], b: Optional[date]) -> bool:
    return bool(a and b and a.year == b.year and a.month == b.month)


def _resolver_e_validar_cprb(itens: List[CprbItem], empresa: Empresa) -> list[tuple[date, Optional[date]]]:
    """Aplica RF-0.164/0.165/0.166 a cada periodo e devolve os pares (inicio, fim) resolvidos.
    Lanca HTTP 422 na primeira violacao, com mensagem acionavel."""
    abertura, encerramento = empresa.data_abertura, empresa.data_encerramento
    resolvidos: list[tuple[date, Optional[date]]] = []
    for it in itens:
        ini = it.inicio
        # RF-0.166: fim em branco
        fim = it.fim
        if fim is None and not it.fim_confirmado:
            fim = date(ini.year, 12, 31)     # fecha no fim do ano-calendario do inicio
        if fim is not None and fim < ini:
            raise HTTPException(status_code=422, detail="Período de CPRB com fim anterior ao início.")

        # RF-0.164: ano-calendario — inicio em janeiro, salvo se coincidir com a abertura
        if ini.month != 1 and not _mesma_competencia(ini, abertura):
            raise HTTPException(status_code=422, detail=(
                f"Período de CPRB deve iniciar em janeiro (opção anual e irretratável, "
                f"Lei 12.546/2011, art. 9º, §13). Início {ini.strftime('%m/%Y')} só é aceito se "
                f"coincidir com a abertura da empresa."))
        # fim em dezembro, salvo se coincidir com o encerramento
        if fim is not None and fim.month != 12 and not _mesma_competencia(fim, encerramento):
            raise HTTPException(status_code=422, detail=(
                f"Período de CPRB deve terminar em dezembro. Fim {fim.strftime('%m/%Y')} só é "
                f"aceito se coincidir com o encerramento da empresa."))

        # RF-0.165: teto em 12/2027
        if ini > _CPRB_LIMITE_FIM:
            raise HTTPException(status_code=422, detail="CPRB extinta a partir de 2028 (Lei 14.973/2024): início não pode ultrapassar 12/2027.")
        if fim is not None and fim > _CPRB_LIMITE_FIM:
            raise HTTPException(status_code=422, detail="CPRB extinta a partir de 2028 (Lei 14.973/2024): nenhum período pode ultrapassar 12/2027.")
        # periodo em aberto (fim confirmado) tambem nao vale alem de 2027 no calculo — a tabela
        # de transicao ja trava isso; aqui mantemos o None (vigente) so se o inicio for valido.
        resolvidos.append((ini, fim))
    return resolvidos


# ---------------- CRUD empresa ----------------
@router.get("/")
async def listar_empresas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    result = await db.execute(select(Empresa).where(Empresa.ativo == True))
    return [{"id": str(e.id), "razao_social": e.razao_social, "cnpj": e.cnpj} for e in result.scalars()]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_empresa(
    data: EmpresaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    empresa = Empresa(**data.model_dump())
    db.add(empresa)
    await db.commit()
    await db.refresh(empresa)
    return {"id": str(empresa.id), "razao_social": empresa.razao_social}


# ---- Consulta pública de CNPJ (RF-0.150), via backend + adapter ----
@router.get("/consulta-cnpj/{cnpj}")
async def consulta_cnpj(
    cnpj: str,
    current_user: Usuario = Depends(get_current_user),
):
    """Consulta os dados públicos cadastrais pelo CNPJ raiz. A chamada sai do backend.
    Retorno marcado como 'consultado, não confirmado' — o usuário confirma antes de valer."""
    from api.services.cnpj_lookup import consultar_cnpj, CnpjConsultaError
    try:
        return await consultar_cnpj(cnpj)
    except CnpjConsultaError as e:
        # 422: sem bloquear o fluxo — o front abre manual e marca "declarado"
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/opcoes/fpas")
async def listar_fpas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from api.models.tabela_fpas import TabelaFPAS
    rows = (await db.execute(
        select(TabelaFPAS).where(TabelaFPAS.ativo == True).order_by(TabelaFPAS.codigo_fpas)
    )).scalars().all()
    return [{"codigo": r.codigo_fpas, "descricao": r.descricao, "aliquota_terceiros": float(r.aliquota_terceiros)} for r in rows]


@router.get("/{empresa_id}")
async def obter_empresa(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    empresa = (await db.execute(select(Empresa).where(Empresa.id == empresa_id))).scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    # RF-0.159: número de estabelecimentos é contagem derivada (ativos), não campo digitado
    num_estab = (await db.execute(
        select(func.count()).select_from(Estabelecimento).where(
            Estabelecimento.empresa_id == empresa_id, Estabelecimento.status == "ativa"
        )
    )).scalar_one()
    secundarios = (await db.execute(
        select(EmpresaCnaeSecundario.cnae).where(EmpresaCnaeSecundario.empresa_id == empresa_id)
    )).scalars().all()
    return {
        "id": str(empresa.id),
        "razao_social": empresa.razao_social,
        "nome_fantasia": empresa.nome_fantasia,
        "cnpj": empresa.cnpj,
        "cnae_principal": empresa.cnae_principal,   # semente do enquadramento da matriz
        "cnaes_secundarios": [{"codigo": c} for c in secundarios],
        "periodo_apuracao_inicio": empresa.periodo_apuracao_inicio.isoformat() if empresa.periodo_apuracao_inicio else None,
        "periodo_apuracao_fim": empresa.periodo_apuracao_fim.isoformat() if empresa.periodo_apuracao_fim else None,
        "data_abertura": empresa.data_abertura.isoformat() if empresa.data_abertura else None,
        "data_encerramento": empresa.data_encerramento.isoformat() if empresa.data_encerramento else None,
        "origem_cadastro": empresa.origem_cadastro,
        "consultado_em": empresa.consultado_em.isoformat() if empresa.consultado_em else None,
        "endereco": empresa.endereco,
        "numero": empresa.numero,
        "complemento": empresa.complemento,
        "bairro": empresa.bairro,
        "cidade": empresa.cidade,
        "uf": empresa.uf,
        "cep": empresa.cep,
        "num_estabelecimentos": int(num_estab),
        "contato_nome": empresa.contato_nome,
        "contato_email": empresa.contato_email,
        "contato_telefone": empresa.contato_telefone,
    }


@router.get("/{empresa_id}/cadastro-status")
async def cadastro_status(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.empresa_id != empresa_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado a empresa de outro tenant")
    from api.services.cadastro_completo import verificar_cadastro
    return await verificar_cadastro(empresa_id, db)


@router.put("/{empresa_id}")
async def atualizar_empresa(
    empresa_id: UUID,
    data: EmpresaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    empresa = (await db.execute(select(Empresa).where(Empresa.id == empresa_id))).scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    payload = data.model_dump(exclude_unset=True)
    # CNAEs secundários são relação 1:N — tratados à parte (RF-0.150: gravar todo o retorno da consulta)
    secundarios = payload.pop("cnaes_secundarios", None)
    for k, v in payload.items():
        setattr(empresa, k, v)
    if secundarios is not None:
        await db.execute(delete(EmpresaCnaeSecundario).where(EmpresaCnaeSecundario.empresa_id == empresa_id))
        vistos = set()
        for cod in secundarios:
            c = re.sub(r"\D", "", cod or "")[:7]
            if c and c not in vistos:
                vistos.add(c)
                db.add(EmpresaCnaeSecundario(empresa_id=empresa_id, cnae=c))
    declarante = getattr(current_user, "email", None) or getattr(current_user, "nome", None)
    await _garantir_matriz(empresa, db, declarante)   # RF-0.152
    await db.commit()
    return {"id": str(empresa.id), "ok": True}


@router.post("/{empresa_id}/reset")
async def zerar_empresa(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """Zera o cadastro do tenant (uso em testes): apaga estabelecimentos (e, por cascata no banco,
    atividades/enquadramento/FAP/RAT/custeio/rubrica/achado), regime, CPRB e CNAEs secundários, e
    limpa os campos de cadastro da empresa. NÃO apaga a linha da empresa (mantém o login) nem mexe
    em razão social/CNPJ (reaproveitados ou sobrescritos na tela). Bloqueia se houver dados
    vinculados que impeçam (trabalhador/documento/vínculo apontando para o estabelecimento)."""
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    empresa = (await db.execute(select(Empresa).where(Empresa.id == empresa_id))).scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    try:
        # estabelecimentos primeiro (cascata no banco cuida dos filhos do estabelecimento)
        await db.execute(delete(Estabelecimento).where(Estabelecimento.empresa_id == empresa_id))
        await db.execute(delete(EmpresaRegime).where(EmpresaRegime.empresa_id == empresa_id))
        await db.execute(delete(EmpresaCprb).where(EmpresaCprb.empresa_id == empresa_id))
        await db.execute(delete(EmpresaCnaeSecundario).where(EmpresaCnaeSecundario.empresa_id == empresa_id))
        # limpa os campos de cadastro (mantém razao_social/cnpj — NOT NULL/UNIQUE, sobrescritos na tela)
        empresa.cnae_principal = None
        empresa.periodo_apuracao_inicio = None
        empresa.periodo_apuracao_fim = None
        empresa.data_abertura = None
        empresa.data_encerramento = None
        empresa.origem_cadastro = None
        empresa.consultado_em = None
        empresa.endereco = empresa.numero = empresa.complemento = None
        empresa.bairro = empresa.cidade = empresa.uf = empresa.cep = None
        empresa.cprb_status = "nao_informado"
        empresa.cprb_verificado_por = None
        empresa.cprb_verificado_em = None
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=(
            "Não foi possível zerar: há dados vinculados a um estabelecimento "
            "(trabalhador, documento ou vínculo). Remova-os antes de zerar a empresa."))
    return {"id": str(empresa.id), "ok": True, "zerado": True}


# ---- Espelho do enquadramento da matriz (RF-0.155) ----
@router.get("/{empresa_id}/matriz-enquadramento")
async def matriz_enquadramento(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    matriz = (await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.empresa_id == empresa_id, Estabelecimento.posicao == "matriz"
        )
    )).scalars().first()
    if matriz is None:
        return {"existe": False}
    empresa_cnae_principal = (await db.execute(
        select(Empresa.cnae_principal).where(Empresa.id == empresa_id)
    )).scalar_one_or_none()
    # PRIMEIRA FONTE: a série APURADA da matriz (motor do Adendo 04, Fase 3). É o número real,
    # da competência corrente. Antes este endpoint só sabia montar um preview do Anexo I, o que
    # fazia o espelho ignorar a apuração que já existia.
    E = EstabelecimentoEnquadramento
    hoje = date.today().replace(day=1)
    apurada = (await db.execute(
        select(E).where(E.estabelecimento_id == matriz.id, E.competencia <= hoje)
        .order_by(E.competencia.desc()).limit(1)
    )).scalars().first()
    if apurada is None:   # série inteira no futuro: mostra a primeira, dizendo qual é
        apurada = (await db.execute(
            select(E).where(E.estabelecimento_id == matriz.id)
            .order_by(E.competencia.asc()).limit(1)
        )).scalars().first()

    if apurada is not None and apurada.aliquota_devida is not None:
        devida = float(apurada.aliquota_devida)
        aplicada = float(apurada.aliquota_aplicada) if apurada.aliquota_aplicada is not None else None
        efetiva = float(apurada.aliquota_efetiva) if apurada.aliquota_efetiva is not None else None
        return {
            "existe": True,
            "estabelecimento_id": str(matriz.id),
            "enquadramento": {
                "cnae": apurada.cnae_preponderante,
                "grau_risco": apurada.grau_risco,
                "grau_label": GRAU_LABEL.get(apurada.grau_risco or 0, ""),
                "aliquota_rat": devida,
                "fap": float(apurada.fap) if apurada.fap is not None else None,
                "aliquota_efetiva": efetiva,
                "aliquota_aplicada": aplicada,
                "divergencia_pp": divergencia_de(efetiva, aplicada),
                "situacao": situacao_de(apurada.em_fila, devida, aplicada),
                "codigo_fpas": None,
                "competencia": apurada.competencia.isoformat(),
                "origem": "apurado pelo motor (atividade preponderante)",
                "confirmado": True,
            },
        }

    # SEGUNDA FONTE: preview do Anexo I, enquanto a série não existe. Vale para a matriz recém-
    # criada, antes de declarar quantitativo e FAP.
    ativ = (await db.execute(
        select(EstabelecimentoAtividade).where(
            EstabelecimentoAtividade.estabelecimento_id == matriz.id,
        ).order_by(EstabelecimentoAtividade.vigencia_fim.is_(None).desc(),
                   EstabelecimentoAtividade.quantitativo.desc().nullslast(),
                   EstabelecimentoAtividade.vigencia_inicio.desc())
    )).scalars().first()
    # CNAE base: atividade declarada da matriz; se ainda não houver, cai na CNAE principal da
    # empresa (a matriz pode existir sem atividade registrada — não deixar o espelho vazio).
    cnae_base = (ativ.cnae if ativ else None) or empresa_cnae_principal
    if not cnae_base:
        # Nunca devolver vazio mudo: dizer POR QUE está vazio é o que permite à tela orientar.
        return {
            "existe": True, "estabelecimento_id": str(matriz.id), "enquadramento": None,
            "motivo": ("A matriz ainda não tem atividade declarada nem CNAE principal na empresa. "
                       "Informe o CNAE principal aqui ou cadastre a atividade da matriz em "
                       "Estabelecimentos."),
        }
    grau = rat = fpas = None
    ce = (await db.execute(select(CnaeEnquadramento).where(CnaeEnquadramento.cnae == cnae_base))).scalar_one_or_none()
    if ce:
        grau, rat = ce.grau_risco, float(ce.aliquota_rat)
    try:
        div = int((cnae_base or "")[:2])
        sug = (await db.execute(select(CnaeFpasSugestao).where(
            CnaeFpasSugestao.divisao_ini <= div, CnaeFpasSugestao.divisao_fim >= div))).scalars().first()
        fpas = sug.fpas_sugerido if sug else None
    except ValueError:
        pass
    return {
        "existe": True,
        "estabelecimento_id": str(matriz.id),
        "enquadramento": {
            "cnae": cnae_base,          # BUG CORRIGIDO: era ativ.cnae, que estourava quando a
                                        # matriz não tinha atividade — 500 engolido pelo front,
                                        # que então exibia o texto de "aparece aqui depois".
            "grau_risco": grau,
            "grau_label": GRAU_LABEL.get(grau or 0, ""),
            "aliquota_rat": rat,
            "codigo_fpas": fpas,
            "competencia": None,
            "origem": ("derivado do Anexo I pela CNAE principal — a matriz ainda não tem "
                       "atividade declarada" if not ativ else
                       "derivado do Anexo I pela atividade declarada — série ainda não apurada"),
            "confirmado": False,
        },
        "motivo": ("Prévia: a série mensal ainda não foi apurada. Declare o quantitativo da "
                   "atividade e o FAP do ano em Estabelecimentos para o número virar apuração."),
    }


# ---- Regime tributário por período (RF-0.156) ----
@router.get("/{empresa_id}/regime")
async def listar_regime(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    rows = (await db.execute(
        select(EmpresaRegime).where(EmpresaRegime.empresa_id == empresa_id).order_by(EmpresaRegime.inicio)
    )).scalars().all()
    return [{"regime": r.regime, "anexo_simples": r.anexo_simples,
             "inicio": r.inicio.isoformat(), "fim": r.fim.isoformat() if r.fim else None} for r in rows]


@router.put("/{empresa_id}/regime")
async def salvar_regime(
    empresa_id: UUID,
    data: List[RegimeItem],
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """Substitui a lista de períodos de regime. Valida sem sobreposição (RF-0.156)."""
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    for it in data:
        if it.fim and it.fim < it.inicio:
            raise HTTPException(status_code=422, detail="Período de regime com fim anterior ao início.")
    if not _sem_sobreposicao([(it.inicio, it.fim) for it in data]):
        raise HTTPException(status_code=422, detail="Períodos de regime se sobrepõem.")
    existentes = (await db.execute(
        select(EmpresaRegime).where(EmpresaRegime.empresa_id == empresa_id)
    )).scalars().all()
    for e in existentes:
        await db.delete(e)
    for it in data:
        db.add(EmpresaRegime(empresa_id=empresa_id, regime=it.regime, anexo_simples=it.anexo_simples,
                             inicio=it.inicio, fim=it.fim))
    await db.commit()
    return {"ok": True, "total": len(data)}


# ---- CPRB: estado + períodos (RF-0.157/0.163..0.166) ----
@router.get("/{empresa_id}/cprb")
async def listar_cprb(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    empresa = (await db.execute(select(Empresa).where(Empresa.id == empresa_id))).scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    rows = (await db.execute(
        select(EmpresaCprb).where(EmpresaCprb.empresa_id == empresa_id).order_by(EmpresaCprb.inicio)
    )).scalars().all()
    return {
        "status": empresa.cprb_status or "nao_informado",
        "verificado_por": empresa.cprb_verificado_por,
        "verificado_em": empresa.cprb_verificado_em.isoformat() if empresa.cprb_verificado_em else None,
        "periodos": [{"inicio": r.inicio.isoformat(), "fim": r.fim.isoformat() if r.fim else None} for r in rows],
    }


@router.put("/{empresa_id}/cprb")
async def salvar_cprb(
    empresa_id: UUID,
    data: CprbPayload,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """RF-0.163..0.166: grava o ESTADO da CPRB e, só no 'optante', a lista de períodos.
    - nao_informado: padrão; sem autor/data; a conferência/memória registra que não foi verificada.
    - nao_optante: marcação explícita (autor + data); sem períodos; cálculo com patronal cheia.
    - optante: exige ao menos um período; valida ano-calendário, teto 12/2027 e fim em branco."""
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    if data.status not in _CPRB_STATUS:
        raise HTTPException(status_code=422, detail="Estado de CPRB inválido.")
    empresa = (await db.execute(select(Empresa).where(Empresa.id == empresa_id))).scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    resolvidos: list[tuple[date, Optional[date]]] = []
    if data.status == "optante":
        if not data.periodos:
            raise HTTPException(status_code=422, detail="Optante pela CPRB exige ao menos um período.")
        resolvidos = _resolver_e_validar_cprb(data.periodos, empresa)   # RF-0.164/0.165/0.166
        if not _sem_sobreposicao(resolvidos):
            raise HTTPException(status_code=422, detail="Períodos de CPRB se sobrepõem.")

    # regrava os períodos (vazios quando não é optante)
    existentes = (await db.execute(
        select(EmpresaCprb).where(EmpresaCprb.empresa_id == empresa_id)
    )).scalars().all()
    for e in existentes:
        await db.delete(e)
    for ini, fim in resolvidos:
        db.add(EmpresaCprb(empresa_id=empresa_id, inicio=ini, fim=fim))

    # estado + autoria (RF-0.163): carimba autor/data só numa marcação explícita (nao_optante/optante);
    # mantém o carimbo anterior se o estado não mudou; limpa no nao_informado.
    declarante = getattr(current_user, "email", None) or getattr(current_user, "nome", None)
    if data.status == "nao_informado":
        empresa.cprb_status = "nao_informado"
        empresa.cprb_verificado_por = None
        empresa.cprb_verificado_em = None
    else:
        novo = empresa.cprb_status != data.status or empresa.cprb_verificado_em is None
        empresa.cprb_status = data.status
        if novo:
            empresa.cprb_verificado_por = declarante
            empresa.cprb_verificado_em = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "status": empresa.cprb_status, "total": len(resolvidos)}
