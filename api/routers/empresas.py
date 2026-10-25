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
from api.auth import get_current_user, require_perfil, require_papel
from api.services.enquadramento_situacao import (
    situacao_de, divergencia_de, divergencia_confirmada, motivo_conferencia,
)

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


# Campos cuja origem é rastreada individualmente (item 1 da revisão). Os dois primeiros são os
# que importam de verdade: entram em cálculo e são citados na memória de enquadramento. Afirmar
# que vieram da Receita quando vieram do usuário é afirmação falsa em peça lida por fiscal.
CAMPOS_RASTREADOS = (
    "cnae_principal", "data_abertura",          # entram em cálculo
    "razao_social", "nome_fantasia", "data_encerramento",
    "tipo_logradouro", "endereco", "numero", "complemento", "bairro", "cidade", "uf", "cep",
)


def _autor_declaracao(u) -> str:
    """Quem declarou. Prefere o NOME, nao o e-mail.

    A diferenca aparece na peca: "Declarado por Carolina Burnett" e o que a Carolina pediu, e e
    o que um fiscal le. O e-mail entra so quando nao ha nome cadastrado — melhor um endereco do
    que uma declaracao sem dono.
    """
    return (getattr(u, "nome", None) or getattr(u, "email", None)
            or str(getattr(u, "id", "?")))


def _txt(v) -> str | None:
    """Normaliza para comparação: data vira ISO, vazio vira None."""
    if v is None:
        return None
    s = v.isoformat() if isinstance(v, (date, datetime)) else str(v)
    s = s.strip()
    return s or None


def _atualizar_campos_origem(empresa: Empresa, salvos: dict, consultados: dict | None,
                             consultado_em) -> dict:
    """Recalcula o mapa de origem por campo. Devolve o mapa novo.

    Regra: um campo é 'consultado' somente enquanto o valor salvo for IGUAL ao que a consulta
    devolveu. Editado, vira 'declarado' — e o valor consultado é PRESERVADO, porque a diferença
    entre os dois é ela própria um achado: cliente que troca o CNAE principal à mão para algo
    diferente do cadastro oficial fica registrado.

    O mapa anterior é preservado: salvar de novo sem reconsultar não apaga a procedência.
    """
    mapa = dict(empresa.campos_origem or {})
    agora = datetime.now(timezone.utc).isoformat()
    quando = consultado_em.isoformat() if isinstance(consultado_em, datetime) else (consultado_em or None)

    for campo in CAMPOS_RASTREADOS:
        if campo not in salvos:
            continue                     # não veio neste PUT: mantém o que já estava
        valor = _txt(salvos.get(campo))
        atual = dict(mapa.get(campo) or {})

        if consultados is not None and campo in consultados:
            # houve consulta nesta gravação: (re)ancora a procedência deste campo
            atual["valor_consultado"] = _txt(consultados.get(campo))
            atual["consultado_em"] = quando or atual.get("consultado_em")

        ancora = atual.get("valor_consultado")
        if ancora is None:
            atual["origem"] = "declarado" if valor is not None else None
        elif valor == ancora:
            atual["origem"] = "consultado"
            atual["alterado_em"] = None
        else:
            if atual.get("origem") != "declarado":
                atual["alterado_em"] = agora
            atual["origem"] = "declarado"

        if atual.get("origem") is None and not atual.get("valor_consultado"):
            mapa.pop(campo, None)        # campo vazio e nunca consultado: nada a registrar
        else:
            mapa[campo] = atual
    return mapa


def _resumo_origem(mapa: dict, consultado_em_empresa=None) -> dict:
    """Composição real do cadastro, para a linha de resumo da tela.

    'consultado_em_empresa' é a data da última consulta gravada na própria empresa. Serve de
    recurso quando o mapa por campo ainda não tem horário — caso dos cadastros salvos antes da
    migration 034. Sem isso a linha cairia no rótulo único "consultado", que é exatamente a
    afirmação imprecisa que o item 3 existe para eliminar.
    """
    consultados = [c for c, v in (mapa or {}).items() if (v or {}).get("origem") == "consultado"]
    alterados = [c for c, v in (mapa or {}).items()
                 if (v or {}).get("origem") == "declarado" and (v or {}).get("valor_consultado")]
    declarados = [c for c, v in (mapa or {}).items()
                  if (v or {}).get("origem") == "declarado" and not (v or {}).get("valor_consultado")]
    quando = None
    for v in (mapa or {}).values():
        q = (v or {}).get("consultado_em")
        if q and (quando is None or q > quando):
            quando = q
    if quando is None and consultado_em_empresa is not None:
        quando = (consultado_em_empresa.isoformat()
                  if hasattr(consultado_em_empresa, "isoformat") else str(consultado_em_empresa))
    return {
        "consultado_em": quando,
        "campos_consultados": sorted(consultados),
        "campos_alterados": sorted(alterados),     # vieram da consulta e foram editados
        "campos_declarados": sorted(declarados),   # nunca vieram da consulta
    }


async def _descricoes_cnae(codigos, db: AsyncSession) -> dict:
    """Descrição oficial da subclasse, por código, a partir do Anexo I (migration 022).

    Carolina, 20/10, item 3: a descrição transforma um código, que só especialista confere, numa
    frase que qualquer um confere — inclusive o cliente, que conhece o próprio negócio e percebe
    na hora "Construção de edifícios" dentro de um comércio de alimentos.

    Vem do Anexo I, a MESMA tabela de onde sai o grau de risco, e não da consulta pública: a
    descrição fica disponível em toda leitura do cadastro, não só logo depois de consultar, e o
    laudo nunca passa a depender da API externa como fonte. CNAE sem linha no Anexo I devolve
    None — e essa ausência é a mesma que manda a competência à conferência, então não se inventa
    texto para ela.
    """
    cods = sorted({re.sub(r"\D", "", str(c or ""))[:7] for c in (codigos or []) if c})
    cods = [c for c in cods if len(c) == 7]
    if not cods:
        return {}
    linhas = (await db.execute(
        select(CnaeEnquadramento.cnae, CnaeEnquadramento.descricao).where(CnaeEnquadramento.cnae.in_(cods))
    )).all()
    return {c: d for c, d in linhas}


def _exigir_cobertura_regime(periodos: list, empresa: Empresa) -> None:
    """Recusa salvar regime que não cobre a janela de apuração inteira (item 4 da revisão).

    Sem regime tributário não existe base de cálculo. No Simples Nacional a contribuição
    patronal está no documento único para a maior parte dos anexos e só é devida à parte no
    Anexo IV — tratar uma empresa do Simples como se devesse patronal cheia produz achado falso
    de grande valor. Por isso lacuna é erro, não aviso: o cadastro não grava.

    Vale para QUALQUER buraco na janela, não só para a ausência total — a lacuna no meio é a
    mais perigosa, porque o cadastro parece preenchido.
    """
    ini, fim = empresa.periodo_apuracao_inicio, empresa.periodo_apuracao_fim
    if not ini or not fim:
        return   # sem janela definida não há o que cobrir; a janela é exigida em outro ponto
    if not periodos:
        raise HTTPException(
            status_code=422,
            detail=(f"Informe o regime tributário de {ini.strftime('%m/%Y')} a "
                    f"{fim.strftime('%m/%Y')}. Sem regime não há base de cálculo."),
        )
    ordenados = sorted(periodos, key=lambda p: p.inicio)
    if ordenados[0].inicio > ini:
        raise HTTPException(
            status_code=422,
            detail=(f"O regime começa em {ordenados[0].inicio.strftime('%m/%Y')}, depois do início "
                    f"da apuração ({ini.strftime('%m/%Y')}). Cubra o período inteiro."),
        )
    # procura buraco entre períodos consecutivos
    cobertura = ordenados[0].fim
    for prox in ordenados[1:]:
        if cobertura is None:
            break            # período aberto absorve o resto
        seguinte = date(cobertura.year + (cobertura.month // 12), (cobertura.month % 12) + 1, 1)
        if prox.inicio > seguinte:
            raise HTTPException(
                status_code=422,
                detail=(f"Lacuna no regime tributário entre {seguinte.strftime('%m/%Y')} e "
                        f"{prox.inicio.strftime('%m/%Y')}. Todo mês da apuração precisa de regime."),
            )
        cobertura = prox.fim   # ordenados e sem sobreposição: o fim do próximo é a nova cobertura
    if cobertura is not None and cobertura < fim:
        raise HTTPException(
            status_code=422,
            detail=(f"O regime termina em {cobertura.strftime('%m/%Y')}, antes do fim da apuração "
                    f"({fim.strftime('%m/%Y')}). Estenda o último período ou deixe o fim em branco."),
        )


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
    # O que a consulta pública devolveu, campo a campo. NÃO é o rótulo de origem: é a matéria
    # bruta com que o backend DECIDE a origem comparando com o valor salvo (item 1 da revisão).
    # A tela não tem como afirmar "consultado" sobre um dado digitado.
    campos_consultados: dict[str, str | None] | None = None
    # Item 8: a situação deixa de morrer na mensagem transitória da consulta
    situacao_cadastral: str | None = None
    situacao_cadastral_data: date | None = None
    situacao_cadastral_em: datetime | None = None
    tipo_logradouro: str | None = None                # RUA | AVENIDA | QUADRA... (migration 044)
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
    em: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Códigos FPAS oferecíveis NA competência informada (padrão: hoje).

    Filtrado por vigência: a tabela tem três vigências dentro da janela de apuração, e oferecer
    um código que não vigia naquela competência seria convidar a declarar o impossível. A fonte
    acompanha cada opção — o laudo cita o fundamento, e o fundamento muda.
    """
    from api.services.terceiros import opcoes_em
    rows = await opcoes_em(em or date.today(), db)
    return [{"codigo": r["codigo_fpas"], "descricao": r["descricao"],
             "aliquota_terceiros": r["aliquota_terceiros"], "fonte": r["fonte"],
             "vigencia_inicio": r["vigencia_inicio"], "vigencia_fim": r["vigencia_fim"]}
            for r in rows]


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
    # Item 3 da revisão de 20/10: código sozinho ninguém audita; a descrição é o que permite
    # conferir. Principal ganha linha de apoio na tela; secundários levam a descrição no hover,
    # porque cinco descrições viram um parágrafo.
    descr = await _descricoes_cnae([empresa.cnae_principal, *secundarios], db)
    return {
        "id": str(empresa.id),
        "razao_social": empresa.razao_social,
        "nome_fantasia": empresa.nome_fantasia,
        "cnpj": empresa.cnpj,
        "cnae_principal": empresa.cnae_principal,   # semente do enquadramento da matriz
        "cnae_principal_descricao": descr.get(empresa.cnae_principal),
        "cnaes_secundarios": [{"codigo": c, "descricao": descr.get(c)} for c in secundarios],
        "periodo_apuracao_inicio": empresa.periodo_apuracao_inicio.isoformat() if empresa.periodo_apuracao_inicio else None,
        "periodo_apuracao_fim": empresa.periodo_apuracao_fim.isoformat() if empresa.periodo_apuracao_fim else None,
        "data_abertura": empresa.data_abertura.isoformat() if empresa.data_abertura else None,
        "data_encerramento": empresa.data_encerramento.isoformat() if empresa.data_encerramento else None,
        "origem_cadastro": empresa.origem_cadastro,
        "consultado_em": empresa.consultado_em.isoformat() if empresa.consultado_em else None,
        # Origem por campo + composição real do cadastro (item 1 da revisão)
        "campos_origem": empresa.campos_origem or {},
        "resumo_origem": _resumo_origem(empresa.campos_origem or {}, empresa.consultado_em),
        # RF-0.207: a tela precisa saber se está arquivada para oferecer Restaurar
        # Item 8: situação cadastral é dado de cálculo, não recado de tela
        "situacao_cadastral": empresa.situacao_cadastral,
        "situacao_cadastral_data": empresa.situacao_cadastral_data.isoformat() if empresa.situacao_cadastral_data else None,
        "situacao_cadastral_em": empresa.situacao_cadastral_em.isoformat() if empresa.situacao_cadastral_em else None,
        "arquivada": bool(empresa.arquivada),
        "arquivada_em": empresa.arquivada_em.isoformat() if empresa.arquivada_em else None,
        "tipo_logradouro": empresa.tipo_logradouro,
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
    consultados = payload.pop("campos_consultados", None)
    for k, v in payload.items():
        setattr(empresa, k, v)
    # Origem POR CAMPO (item 1): decidida aqui comparando o que foi salvo com o que a consulta
    # devolveu — nunca aceita pronta do cliente.
    empresa.campos_origem = _atualizar_campos_origem(
        empresa, payload, consultados, payload.get("consultado_em") or empresa.consultado_em
    )
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


# ---- Arquivar e excluir (RF-0.207) — substituem o "Zerar empresa" ----
# A acao antiga apagava enquadramento ja apurado a UM CLIQUE de distancia, sem possibilidade de
# volta. Era o risco mais barato de eliminar no sistema inteiro. No lugar dela, duas acoes com
# naturezas diferentes e protecoes diferentes:
#   arquivar — REVERSIVEL: a empresa sai da lista principal, os dados permanecem integros;
#   excluir  — IRREVERSIVEL: exige digitar a razao social e e restrita ao titular.
# Nenhuma das duas depende da estrutura multiescritorio; so o seletor de empresa depende, e
# esse segue adiado.
class ExclusaoConfirmacao(BaseModel):
    razao_social: str


@router.post("/{empresa_id}/arquivar")
async def arquivar_empresa(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """Tira a empresa da lista principal SEM apagar nada. Reversivel."""
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    empresa = (await db.execute(select(Empresa).where(Empresa.id == empresa_id))).scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    empresa.arquivada = True
    empresa.arquivada_em = datetime.now(timezone.utc)
    await db.commit()
    return {"id": str(empresa.id), "arquivada": True,
            "mensagem": "Empresa arquivada. Os dados seguem íntegros e podem ser restaurados."}


@router.post("/{empresa_id}/desarquivar")
async def desarquivar_empresa(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    empresa = (await db.execute(select(Empresa).where(Empresa.id == empresa_id))).scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    empresa.arquivada = False
    empresa.arquivada_em = None
    await db.commit()
    return {"id": str(empresa.id), "arquivada": False}


@router.delete("/{empresa_id}")
async def excluir_empresa(
    empresa_id: UUID,
    confirmacao: ExclusaoConfirmacao,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_papel("titular")),
):
    """Apaga a empresa e tudo que pende dela. IRREVERSIVEL.

    Duas travas, porque o que se perde aqui e enquadramento apurado:
      - exige a RAZAO SOCIAL digitada e identica (nao e um clique);
      - restrita ao papel TITULAR do escritorio.
    """
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    empresa = (await db.execute(select(Empresa).where(Empresa.id == empresa_id))).scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    informada = (confirmacao.razao_social or "").strip()
    if informada.casefold() != (empresa.razao_social or "").strip().casefold():
        raise HTTPException(
            status_code=422,
            detail=(f"Para excluir, digite a razão social exatamente como cadastrada: "
                    f"\"{empresa.razao_social}\"."),
        )
    try:
        await db.execute(delete(Estabelecimento).where(Estabelecimento.empresa_id == empresa_id))
        await db.execute(delete(EmpresaRegime).where(EmpresaRegime.empresa_id == empresa_id))
        await db.execute(delete(EmpresaCprb).where(EmpresaCprb.empresa_id == empresa_id))
        await db.execute(delete(EmpresaCnaeSecundario).where(EmpresaCnaeSecundario.empresa_id == empresa_id))
        await db.delete(empresa)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=(
            "Não foi possível excluir: há dados vinculados (trabalhador, documento ou vínculo). "
            "Remova-os antes, ou use Arquivar, que preserva tudo."))
    return {"ok": True, "excluida": True, "razao_social": empresa.razao_social}


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

    async def _descricao_cnae(c):
        """Descrição da subclasse, da tabela do Anexo I já carregada (migration 022)."""
        if not c:
            return None
        return (await db.execute(
            select(CnaeEnquadramento.descricao).where(CnaeEnquadramento.cnae == c)
        )).scalar_one_or_none()

    # A CONDICAO ACEITA A COMPETENCIA SEM ALIQUOTA DEVIDA quando o REGIME a afastou (Carolina,
    # 24/10, item 3). Era so `aliquota_devida is not None`, e no Simples fora do Anexo IV o motor
    # grava a linha justamente com a devida NULA — nao ha RAT a apurar. A linha existia, com
    # rat_aplicavel=False, motivo_inaplicavel e o regime da competencia, e este endpoint a
    # IGNORAVA e caia no preview do Anexo I logo abaixo.
    #
    # Dai os dois sintomas que ela viu na mesma tela: o texto "declare o quantitativo da atividade
    # e o FAP para o numero virar apuracao" — afirmando que falta dado onde nao falta, porque no
    # Simples fora do Anexo IV nao ha RAT a apurar por mais quantitativo que se declare — e o CNAE
    # 4712-1/00 exibido sob o titulo "atividade preponderante da competencia", que e o CNAE
    # principal do cadastro e nao preponderante nenhuma: o preview o usa como base por nao ter
    # serie. Nas palavras dela: "um rotulo que chama um de outro, dentro da tela que fundamenta a
    # peca, ensina o erro que a peca combate".
    #
    # Nao era problema de texto: o preview nunca soube do regime porque nao chegava a olhar a
    # linha que ja tinha a resposta.
    if apurada is not None and (apurada.aliquota_devida is not None or not apurada.rat_aplicavel):
        devida = float(apurada.aliquota_devida) if apurada.aliquota_devida is not None else None
        aplicada = float(apurada.aliquota_aplicada) if apurada.aliquota_aplicada is not None else None
        efetiva = float(apurada.aliquota_efetiva) if apurada.aliquota_efetiva is not None else None
        # Resumo da SÉRIE INTEIRA (item 7): o espelho mostra uma competência de sessenta, e quem
        # olha a tela precisa saber disso antes de concluir qualquer coisa sobre o caso — na
        # mesma empresa a divergência de um ano pode ser crédito e a de outro, passivo.
        todas = (await db.execute(
            select(E).where(E.estabelecimento_id == matriz.id)
        )).scalars().all()
        # TRES estados e UM recorte. 'sem_aplicado' nao e um quarto balde ao lado dos tres: e
        # SUBCONJUNTO de 'apuradas' — as apuradas em que a empresa ainda nao informou a aliquota
        # que aplicou. Por isso os tres estados somam o total e sem_aplicado nao entra na soma.
        #
        # A primeira versao disto (21/10) fatiava 'apuradas' em dois baldes disjuntos, e o
        # contador passou a afirmar que 58 competencias estavam sem o RAT aplicado quando uma
        # delas tinha — justamente a que a tela exibia logo abaixo, com divergencia calculada.
        # Era o mesmo erro de 19/10 em outra roupa: deixar o atributo deslocar a contagem dos
        # estados. O estado conta inteiro; o atributo aparece entre parenteses.
        #
        # situacao_de() passou a QUATRO valores em 22/10: entrou 'nao_auditada', para a
        # competencia em que o regime afasta a apuracao. Continua sendo estado, e os quatro
        # somam o total.
        #
        # 'sem_aplicado' SAIU, e nao foi renomeado por gosto. Ele era recorte de 'apuradas' — as
        # apuradas em que o aplicado ainda nao fora informado. Desde 24/10 essa combinacao nao
        # existe: competencia sem o aplicado DESDOBRADO nao e apurada, porque a comparacao nao
        # fecha (ver enquadramento_situacao.situacao_de). O recorte continua util, mas agora
        # recorta 'em_conferencia': dentro da fila, quais esperam a empresa informar o que
        # recolheu, e quais esperam o motor concluir. Sao acoes diferentes para quem opera.
        resumo = {"total": len(todas), "conferidas": 0, "apuradas": 0,
                  "aguardando_aplicado": 0, "em_conferencia": 0, "nao_auditadas": 0}
        for r in todas:
            dev = float(r.aliquota_devida) if r.aliquota_devida is not None else None
            rat_a = float(r.rat_aplicado) if r.rat_aplicado is not None else None
            fap_a = float(r.fap_aplicado) if r.fap_aplicado is not None else None
            s = situacao_de(
                rat_aplicavel=r.rat_aplicavel, em_fila=r.em_fila, aliquota_devida=dev,
                rat_aplicado=rat_a, fap_aplicado=fap_a, conferido_por=r.conferido_por)
            if s == "nao_auditada":
                resumo["nao_auditadas"] += 1
            elif s == "conferido":
                resumo["conferidas"] += 1
            elif s == "apurado":
                resumo["apuradas"] += 1
            else:
                resumo["em_conferencia"] += 1
                # Recorte: o devido fechou, falta so o que a empresa aplicou.
                if not (r.em_fila or dev is None):
                    resumo["aguardando_aplicado"] += 1
        return {
            "existe": True,
            "estabelecimento_id": str(matriz.id),
            "serie_resumo": resumo,
            "enquadramento": {
                "cnae": apurada.cnae_preponderante,
                "cnae_descricao": await _descricao_cnae(apurada.cnae_preponderante),
                "grau_risco": apurada.grau_risco,
                "grau_label": GRAU_LABEL.get(apurada.grau_risco or 0, ""),
                "aliquota_rat": devida,
                "fap": float(apurada.fap) if apurada.fap is not None else None,
                "aliquota_efetiva": efetiva,
                "aliquota_aplicada": aplicada,
                # AS DUAS ORIGENS DO APLICADO (colunas da migration 036, ate aqui nao
                # serializadas). Sem elas a tela mostra so a efetiva aplicada e nao da para
                # dizer QUEM errou: quem usou grau errado, quem ignorou o FAP publicado, ou os
                # dois. Sao defesas diferentes — reenquadramento contra portaria do FAPWeb — e o
                # S-1005 separa os campos (aliqRat, fap, aliqRatAjust). Nulas nas linhas antigas,
                # que guardam so a efetiva: nesse caso a tela diz que nao sabe, e nao presume.
                "rat_base_aplicado": float(apurada.rat_aplicado) if apurada.rat_aplicado is not None else None,
                "fap_aplicado": float(apurada.fap_aplicado) if apurada.fap_aplicado is not None else None,
                "divergencia_pp": divergencia_de(efetiva, aplicada),
                # A divergencia existe como numero, mas so pode ser AFIRMADA com o aplicado
                # desdobrado. Sem isso o mesmo valor admite duas leituras opostas — era a tela
                # deste bloco que afirmava credito enquanto o quadro ao lado, no mesmo cartao,
                # dizia que a origem nao podia ser afirmada.
                "divergencia_confirmada": divergencia_confirmada(
                    float(apurada.rat_aplicado) if apurada.rat_aplicado is not None else None,
                    float(apurada.fap_aplicado) if apurada.fap_aplicado is not None else None),
                "situacao": situacao_de(
                    rat_aplicavel=apurada.rat_aplicavel, em_fila=apurada.em_fila,
                    aliquota_devida=devida,
                    rat_aplicado=float(apurada.rat_aplicado) if apurada.rat_aplicado is not None else None,
                    fap_aplicado=float(apurada.fap_aplicado) if apurada.fap_aplicado is not None else None,
                    conferido_por=apurada.conferido_por),
                "motivo_conferencia": motivo_conferencia(
                    rat_aplicavel=apurada.rat_aplicavel,
                    em_fila=apurada.em_fila, motivo_fila=apurada.motivo_fila,
                    aliquota_devida=devida,
                    rat_aplicado=float(apurada.rat_aplicado) if apurada.rat_aplicado is not None else None,
                    fap_aplicado=float(apurada.fap_aplicado) if apurada.fap_aplicado is not None else None),
                # O CNAE PRINCIPAL DO CADASTRO viaja junto, com nome proprio. Quando o regime
                # afasta a apuracao nao ha preponderante apurada — ela se apura pelo numero de
                # segurados em cada estabelecimento, nao pelo cartao CNPJ —, e a tela precisa
                # poder exibir o que tem sem chamar de preponderante o que nao e.
                "cnae_principal_cadastro": empresa_cnae_principal,
                "cnae_principal_descricao": await _descricao_cnae(empresa_cnae_principal),
                # O regime que decidiu a aplicabilidade viaja junto: a peca precisa dizer o
                # fato e a fonte, nao so que a competencia nao foi auditada.
                "rat_aplicavel": bool(apurada.rat_aplicavel),
                "motivo_inaplicavel": apurada.motivo_inaplicavel,
                "regime_competencia": apurada.regime_competencia,
                "anexo_competencia": apurada.anexo_competencia,
                "conferido_por": apurada.conferido_por,
                "conferido_em": apurada.conferido_em.isoformat() if apurada.conferido_em else None,
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
            "cnae_descricao": await _descricao_cnae(cnae_base),
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
             "inicio": r.inicio.isoformat(), "fim": r.fim.isoformat() if r.fim else None,
             # Autoria por periodo (048). A tela mostra no rodape a declaracao mais recente;
             # vem por linha porque periodos podem ter sido declarados por pessoas diferentes.
             "declarado_por": r.declarado_por,
             "declarado_em": r.declarado_em.isoformat() if r.declarado_em else None} for r in rows]


@router.put("/{empresa_id}/regime")
async def salvar_regime(
    empresa_id: UUID,
    data: List[RegimeItem],
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """Substitui a lista de períodos de regime. Valida sem sobreposição e SEM LACUNA (RF-0.156).

    A verificação de lacuna existia só no formulário. Qualquer caminho que não passasse pela
    tela gravava em silêncio — e sem regime tributário não há base de cálculo: tratar uma
    empresa do Simples como se devesse patronal cheia produz achado falso de grande valor.
    """
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    empresa = (await db.execute(select(Empresa).where(Empresa.id == empresa_id))).scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    for it in data:
        if it.fim and it.fim < it.inicio:
            raise HTTPException(status_code=422, detail="Período de regime com fim anterior ao início.")
    if not _sem_sobreposicao([(it.inicio, it.fim) for it in data]):
        raise HTTPException(status_code=422, detail="Períodos de regime se sobrepõem.")
    _exigir_cobertura_regime(data, empresa)
    existentes = (await db.execute(
        select(EmpresaRegime).where(EmpresaRegime.empresa_id == empresa_id)
    )).scalars().all()

    # AUTORIA DA DECLARACAO (migration 048). O endpoint apaga a lista inteira e recria a cada
    # salvamento. Se a autoria fosse gravada cega, abrir a tela e salvar sem mexer em nada
    # reescreveria o nome de quem declarou o regime pelo de quem apenas passou por ali — e a
    # memoria de calculo cita essa declaracao. Entao periodo IDENTICO herda a autoria que ja
    # tinha; so o que e novo ou mudou recebe o autor de agora.
    autoria_anterior = {
        (e.regime, e.anexo_simples, e.inicio, e.fim): (e.declarado_por, e.declarado_em)
        for e in existentes
    }
    quem = _autor_declaracao(current_user)
    agora_decl = datetime.now(timezone.utc)

    for e in existentes:
        await db.delete(e)
    for it in data:
        anterior = autoria_anterior.get((it.regime, it.anexo_simples, it.inicio, it.fim))
        por, em = anterior if anterior and anterior[0] else (quem, agora_decl)
        db.add(EmpresaRegime(empresa_id=empresa_id, regime=it.regime, anexo_simples=it.anexo_simples,
                             inicio=it.inicio, fim=it.fim, declarado_por=por, declarado_em=em))
    await db.commit()

    # REAPURA A SERIE (22/10). Desde que o motor passou a ler o regime, mudar o regime mudou a
    # base de calculo — e ate aqui nada reapurava: a tela gravava Simples/Anexo III e seguia
    # exibindo o credito calculado sob a regra antiga, como se o salvamento nao tivesse efeito.
    # As demais mutacoes que mexem em base de calculo (atividade, FAP, estabelecimento) ja
    # reapuram; o regime ficou de fora porque, quando elas foram escritas, ninguem o lia.
    #
    # A reapuracao REVOGA conferencias das competencias afetadas, com o rastro de quem havia
    # conferido — e isso e intencional: assinatura sobre numero que mudou nao corresponde mais
    # a nada. O aviso volta para a tela dizer quantas foram.
    from api.services.motor_enquadramento import apurar_estabelecimento
    estabs = (await db.execute(
        select(Estabelecimento.id).where(Estabelecimento.empresa_id == empresa_id)
    )).scalars().all()
    autor = getattr(current_user, "email", None) or getattr(current_user, "nome", None)
    revogadas = competencias = 0
    for eid in estabs:
        r = await apurar_estabelecimento(eid, db, autor=autor)
        if r.get("ok"):
            competencias += r.get("competencias") or 0
            revogadas += r.get("conferencias_revogadas") or 0
    return {"ok": True, "total": len(data), "estabelecimentos_reapurados": len(estabs),
            "competencias": competencias, "conferencias_revogadas": revogadas,
            "aviso": (f"{revogadas} competência(s) conferidas voltaram a pender de conferência: "
                      f"o regime mudou, então a validação anterior não vale mais.")
                     if revogadas else None}


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
