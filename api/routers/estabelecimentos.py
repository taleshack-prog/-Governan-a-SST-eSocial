# api/routers/estabelecimentos.py — SST ESOCIAL GOV
# Adendo 04: o estabelecimento guarda identificacao/natureza/datas; o enquadramento (grau/RAT)
# e DERIVADO da atividade preponderante (RN-20) — não é campo escolhido. A entrada do motor é a
# lista de atividades com quantitativo por periodo (RF-0.173).
import re
import logging
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, case
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
    divergencia_confirmada, motivo_conferencia,
)
from api.services.fundamentacao import citacoes_do_periodo, citacao_de
from api.services.cprb_transicao import ANO_INICIO_TRANSICAO as ANO_INICIO_TRANSICAO_CPRB
from api.services.memoria_registro import registrar_emissao, sha256_do_conteudo
# As agregacoes da serie. Fonte UNICA, compartilhada com a memoria de calculo — ver o cabecalho
# de resumo_enquadramento.py.
from api.services.resumo_enquadramento import (
    estado_na_janela, contagem_posicao, resumo_por_ano, o_que_falta,
)
from api.models.enquadramento_evento import EnquadramentoEvento, ROTULO_EVENTO
from api.services.enquadramento_eventos import registrar_ato_humano, retrato

router = APIRouter()

TIPOS_ESTABELECIMENTO = ("CNPJ", "CNO", "CAEPF")   # RF-0.171
POSICOES = ("matriz", "filial", "obra")
STATUS_VALIDOS = ("ativa", "paralisada", "encerrada")
GRAU_LABEL = {1: "leve", 2: "médio", 3: "grave"}

# A MATRIZ EM CIMA, SEMPRE (Carolina, 29/10). Ordenar so pelo codigo poria a matriz em primeiro
# apenas enquanto ela fosse a ordem 0001 — e a ressalva dela e exatamente essa: "a matriz nem
# sempre é 0001 (ex.: transferência de sede)". Depois de uma transferencia, a sede pode ser a
# 0007, e a lista a esconderia no meio das filiais.
_ORDEM_POSICAO = case(
    (Estabelecimento.posicao == "matriz", 0),
    (Estabelecimento.posicao == "filial", 1),
    else_=2,
)


logger = logging.getLogger(__name__)


def _autor(u: Usuario) -> str:
    """Quem assina. Nunca "sistema": o estado conferido registra pessoa.

    PREFERE O NOME, nao o e-mail — mesma regra de _autor_declaracao em empresas.py (048). Ate
    24/10 esta funcao preferia o e-mail e aquela preferia o nome, e o resultado apareceu na
    primeira conferencia gravada em producao: a mesma pessoa saiu como "Tales Hack" na declaracao
    do regime e como "talhack@yahoo.com" na conferencia. Numa peca lida por fiscal, duas grafias
    do mesmo autor na mesma pagina sao duas pessoas.

    O e-mail entra so quando nao ha nome cadastrado — melhor um endereco do que um ato sem dono.
    (As duas funcoes seguem duplicadas, em routers diferentes. Unifica-las e a correcao de
    verdade e esta na fila; a divergencia ja custou uma vez.)
    """
    return getattr(u, "nome", None) or getattr(u, "email", None) or str(getattr(u, "id", "?"))


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
    _validar_status_e_encerramento(data)


# ---- "Encerrada" deixa de ser escolhida e passa a vir da data (Carolina, 29/10, pergunta B) ----
#
# O DEFEITO. 'status' e 'data_encerramento' diziam a mesma coisa e podiam se contradizer: dava
# para salvar encerramento preenchido com status "ativa". Dois campos para um fato so, e o
# sistema nao sabia qual deles acreditar — numa tela que decide se o estabelecimento entra ou nao
# na apuracao.
#
# A PROPOSTA DELA ERA MAIS LARGA: "o status sai do formulario e passa a ser consequencia da data".
# Isso resolveria ativa/encerrada e apagaria o terceiro valor, 'paralisada', que data nenhuma
# expressa — um estado declarado sumiria sem ninguem ter decidido que devia sumir. Ela acolheu a
# ressalva: o usuario escolhe entre ATIVA e PARALISADA, e "encerrada" vem da data.
#
# NAO SE REESCREVE O QUE O USUARIO MANDOU. A regra e simetrica e recusa a contradicao nos dois
# sentidos, em vez de corrigir em silencio: num sistema que precisa ser auditavel, gravar algo
# diferente do que foi enviado e pior do que recusar. A tela nunca chega a ver estas mensagens —
# ela deriva o status da data antes de enviar —, mas a API nao depende da tela para se manter
# coerente.
def _validar_status_e_encerramento(data) -> None:
    fim = data.data_encerramento
    encerrada_de_fato = bool(fim and fim <= date.today())
    if data.status == "encerrada" and not encerrada_de_fato:
        raise HTTPException(
            status_code=422,
            detail=("Status 'encerrada' exige a data de encerramento, e ela não pode estar no "
                    "futuro. Informe a data em que o estabelecimento encerrou."),
        )
    if encerrada_de_fato and data.status != "encerrada":
        raise HTTPException(
            status_code=422,
            detail=(f"O encerramento em {fim.strftime('%d/%m/%Y')} já passou: o estabelecimento "
                    f"está encerrado e não pode ficar como '{data.status}'. Para mantê-lo "
                    f"{data.status}, apague a data de encerramento."),
        )


# ---- A raiz do CNPJ e a matriz única (Carolina, 29/10, defeitos 1 e 3) ----

async def _raiz_do_cnpj_da_empresa(empresa_id, db: AsyncSession) -> str | None:
    """Os oito primeiros digitos que todo estabelecimento CNPJ da empresa tem que repetir.

    DE ONDE SAI. Da MATRIZ nao encerrada, que e a referencia que ela deu ("a filial tem que ter a
    raiz da matriz"). Quando ainda nao existe matriz — a empresa cadastrando o primeiro
    estabelecimento —, cai no CNPJ da propria empresa, que e NOT NULL e unico: sempre ha uma
    resposta, e ela nao depende da ordem em que os estabelecimentos foram cadastrados.

    Por que a matriz vem primeiro, e nao a empresa: e o que ela escreveu, e evita que um dado
    antigo divergente entre os dois comece a recusar edicoes de cadastros que ja existiam.
    """
    matriz = (await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.empresa_id == empresa_id,
            Estabelecimento.posicao == "matriz",
            Estabelecimento.status != "encerrada",
        ).limit(1)
    )).scalar_one_or_none()
    if matriz and matriz.cnpj and len(matriz.cnpj) == 14:
        return matriz.cnpj[:8]

    from api.models.empresa import Empresa
    empresa = (await db.execute(
        select(Empresa).where(Empresa.id == empresa_id)
    )).scalar_one_or_none()
    if empresa and empresa.cnpj and len(empresa.cnpj) == 14:
        return empresa.cnpj[:8]
    return None


def _raiz_formatada(raiz: str) -> str:
    return f"{raiz[:2]}.{raiz[2:5]}.{raiz[5:8]}"


async def _validar_no_contexto(data, empresa_id, db: AsyncSession, estab_id=None) -> None:
    """As regras que dependem dos OUTROS estabelecimentos da empresa.

    Ficam separadas de _validar porque precisam do banco. Valem na criacao e na edicao: a segunda
    matriz de teste entrou pelo cadastro, mas entraria igualmente trocando a posicao de uma filial
    que ja existia.
    """
    # (1) A RAIZ. "Estabelecimento de terceiro entra na apuração e soma crédito ou débito que não
    # é do cliente" — e o resultado sai dentro de peça assinada por advogado.
    #
    # Vale para QUALQUER estabelecimento CNPJ, nao so para a filial: uma matriz com raiz diferente
    # da empresa e outra empresa. Nao alcanca CNO nem CAEPF, que nao tem raiz.
    if data.tipo_estabelecimento == "CNPJ" and data.cnpj and len(data.cnpj) == 14:
        raiz = await _raiz_do_cnpj_da_empresa(empresa_id, db)
        # Sem raiz conhecida nao se afirma nada: recusar aqui bloquearia o cadastro por uma
        # ausencia que nao e culpa de quem esta cadastrando.
        if raiz and data.cnpj[:8] != raiz:
            raise HTTPException(
                status_code=422,
                detail=f"A raiz do CNPJ da filial deve ser a da matriz ({_raiz_formatada(raiz)}).",
            )

    # (2) UMA MATRIZ SO — e so a ATIVA bloqueia. Decisao dela: "matriz encerrada não bloqueia,
    # porque é o caso da transferência de sede", em que a sede antiga encerra e outra assume.
    if data.posicao == "matriz" and data.status != "encerrada":
        filtro = [
            Estabelecimento.empresa_id == empresa_id,
            Estabelecimento.posicao == "matriz",
            Estabelecimento.status != "encerrada",
        ]
        if estab_id is not None:
            filtro.append(Estabelecimento.id != estab_id)
        outra = (await db.execute(select(Estabelecimento).where(*filtro).limit(1))).scalar_one_or_none()
        if outra:
            raise HTTPException(status_code=409, detail="A empresa já tem matriz cadastrada.")


# ---- O código deixa de ser digitado (Carolina, 29/10, pergunta A) ----
#
# O QUE ELE ERA. Campo obrigatorio que o usuario inventava. Procurado no codigo inteiro, nao
# corresponde a campo nenhum do eSocial e nao sai em documento: serve para impedir dois cadastros
# iguais na mesma empresa, para ordenar a lista e para nomear o estabelecimento sem nome. Pedir ao
# usuario que invente um identificador interno e pedir que ele faca o trabalho do sistema.
#
# O QUE PASSA A SER. A ORDEM do proprio CNPJ — os quatro digitos entre a raiz e o verificador —,
# que e o numero que a Receita ja deu ao estabelecimento. Nao e inventado, e e conferivel contra o
# cartao CNPJ. CNO e CAEPF nao tem ordem, e caem numa sequencia com prefixo, que nunca colide com
# os quatro digitos de um CNPJ.
#
# GERADO UMA VEZ, NA CRIACAO. A edicao nunca o regrava: e a chave que identifica a linha, e trocar
# identificador de registro existente e reescrever historia.
#
# A ORDEM NAO ORDENA SOZINHA. Ressalva dela: "a matriz nem sempre é 0001 (ex.: transferência de
# sede)". Por isso a lista ordena primeiro pela POSICAO e so depois pelo codigo — ver _ORDEM_POSICAO.
async def _codigo_novo(empresa_id, data, db: AsyncSession) -> str:
    usados = {c for c in (await db.execute(
        select(Estabelecimento.codigo).where(Estabelecimento.empresa_id == empresa_id)
    )).scalars().all()}

    if data.tipo_estabelecimento == "CNPJ" and data.cnpj and len(data.cnpj) == 14:
        base = data.cnpj[8:12]
        if base not in usados:
            return base
        # Dois estabelecimentos com o MESMO CNPJ na mesma empresa — o cadastro ainda nao recusa
        # isso. O sufixo evita que a colisao vire erro de banco; a duplicidade em si fica anotada.
        n = 2
        while f"{base}-{n}" in usados:
            n += 1
        return f"{base}-{n}"

    prefixo = "CNO" if data.tipo_estabelecimento == "CNO" else "CAEPF"
    n = 1
    while f"{prefixo}-{n:04d}" in usados:
        n += 1
    return f"{prefixo}-{n:04d}"


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
    # OPCIONAL E IGNORADO (Carolina, 29/10, pergunta A). O servidor gera na criacao e preserva na
    # edicao. Continua aceito no corpo para nao quebrar quem ainda o envia — e descartado.
    codigo: str | None = None
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
                                    aliquota_devida=devida, rat_aplicado=rat_apl,
                                    fap_aplicado=fap_apl, conferido_por=r.conferido_por),
            # A divergencia so pode ser AFIRMADA com o aplicado desdobrado: sem isso o mesmo
            # numero admite duas leituras opostas (ver enquadramento_situacao.situacao_de).
            "divergencia_confirmada": divergencia_confirmada(rat_apl, fap_apl),
            "motivo_conferencia": motivo_conferencia(
                rat_aplicavel=r.rat_aplicavel, em_fila=r.em_fila, motivo_fila=r.motivo_fila,
                aliquota_devida=devida, rat_aplicado=rat_apl, fap_aplicado=fap_apl),
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
        .order_by(_ORDEM_POSICAO, Estabelecimento.codigo)
    )
    estabs = list(result.scalars())
    ids = [e.id for e in estabs]
    corrente = await _enquadramento_corrente(ids, db)
    completo = await _completude(ids, db)
    resumos = await _resumos_da_janela(ids, db)
    saida = []
    for e in estabs:
        d = _to_dict(e)
        d["enquadramento_atual"] = corrente.get(str(e.id))   # None = serie ainda nao apurada
        d["completude"] = completo.get(str(e.id))
        # O QUE A LISTA-ÍNDICE MOSTRA (revisão de 27/10): o estado das competências, quantas têm
        # crédito ou débito, e o que falta escrito por extenso. Sai dela a divergência de um mês
        # só, que dizia pouco sobre uma janela de cinco anos.
        d["resumo"] = resumos.get(str(e.id))
        saida.append(d)
    return saida


async def _resumos_da_janela(estab_ids: list, db: AsyncSession) -> dict:
    """O resumo da janela de CADA estabelecimento, numa consulta só.

    Uma consulta por estabelecimento seria N+1 — com trinta estabelecimentos, trinta idas ao
    banco para desenhar uma lista. Aqui as competências de todos vêm juntas e são agrupadas em
    memória; a agregação em si fica nas funções compartilhadas, que é o que garante que estes
    números sejam os mesmos da página e os mesmos do documento.
    """
    if not estab_ids:
        return {}
    rows = (await db.execute(
        select(EstabelecimentoEnquadramento)
        .where(EstabelecimentoEnquadramento.estabelecimento_id.in_(estab_ids))
        .order_by(EstabelecimentoEnquadramento.estabelecimento_id,
                  EstabelecimentoEnquadramento.competencia)
    )).scalars().all()

    por_estab: dict[str, list] = {}
    comps: dict[str, list] = {}
    for r in rows:
        k = str(r.estabelecimento_id)
        por_estab.setdefault(k, []).append(_linha_enquadramento(r))
        comps.setdefault(k, []).append(r.competencia)

    return {
        k: {
            "janela": {"inicio": comps[k][0].isoformat(), "fim": comps[k][-1].isoformat()},
            "estado": estado_na_janela(serie),
            "posicao": contagem_posicao(serie),
            "o_que_falta": o_que_falta(serie),
        }
        for k, serie in por_estab.items()
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_estabelecimento(
    data: EstabelecimentoIn,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    _validar(data)
    await _validar_no_contexto(data, current_user.empresa_id, db)
    campos = data.model_dump()
    # O codigo enviado pela tela e DESCARTADO: quem decide e o servidor. A verificacao de
    # duplicidade que existia aqui perdeu o objeto — o gerador ja devolve um codigo livre.
    campos["codigo"] = await _codigo_novo(current_user.empresa_id, data, db)
    e = Estabelecimento(empresa_id=current_user.empresa_id, **campos)
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
    await _validar_no_contexto(data, current_user.empresa_id, db, estab_id=estab_id)
    e = (await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.id == estab_id, Estabelecimento.empresa_id == current_user.empresa_id
        )
    )).scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail="Estabelecimento não encontrado.")
    for k, v in data.model_dump().items():
        # O CODIGO NAO SE REGRAVA. Gerado na criacao, e dali em diante identifica a linha: trocá-lo
        # numa edicao seria renomear um registro que ja existe — e a tela nem o envia mais.
        if k == "codigo":
            continue
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


def sobreposicao_mesmo_cnae(linhas: list[tuple]) -> str | None:
    """Mensagem do conflito, ou None quando nao ha. Recebe [(cnae, inicio, fim), ...].

    A MESMA atividade nao pode ter duas vigencias cobrindo a mesma competencia. Atividades
    DIFERENTES podem e devem coexistir: e comparando os quantitativos delas que a preponderante
    se apura — copiar aqui a regra do bloco de regime, que proibe qualquer sobreposicao, quebraria
    a apuracao inteira.

    Funcao de modulo, e nao bloco dentro do endpoint, para poder ser exercitada sem banco: e a
    regra que impediu a memoria de sair com o 4712-1/00 duas vezes, 50 e 50, ao lado do 4120-4/00
    com 60 — e quem soma 100 contra 60 conclui que a preponderante apurada esta errada, dentro do
    documento que a afirma.
    """
    def _mes(d) -> str:
        return d.strftime("%m/%Y") if d else "em aberto"

    por_cnae: dict[str, list] = {}
    for cnae, inicio, fim in linhas:
        por_cnae.setdefault(cnae, []).append((inicio, fim))
    for cnae, periodos in por_cnae.items():
        ordenados = sorted(periodos, key=lambda p: p[0])
        for (ini_a, fim_a), (ini_b, fim_b) in zip(ordenados, ordenados[1:]):
            # Fim aberto sobrepoe tudo o que vier depois: e o caso mais comum, a linha antiga que
            # nunca foi fechada quando a atividade mudou.
            if fim_a is None or fim_a >= ini_b:
                fmt = f"{cnae[:4]}-{cnae[4:5]}/{cnae[5:]}" if len(cnae) == 7 else cnae
                return (f"O CNAE {fmt} aparece em dois períodos que se sobrepõem: "
                        f"{_mes(ini_a)} a {_mes(fim_a)} e {_mes(ini_b)} a {_mes(fim_b)}. "
                        "Feche o período anterior antes de abrir o seguinte — a mesma atividade "
                        "não pode ter dois quantitativos na mesma competência.")
    return None


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
    Grava autoria (RN-23).

    SOBREPOSICAO DO MESMO CNAE (Carolina, 25/10, item 2). A tabela de atividades da memoria saiu
    com o 4712-1/00 duas vezes, em periodos sobrepostos — 50 trabalhadores em cada —, ao lado do
    4120-4/00 com 60. Quem soma 50 + 50 = 100 contra 60 conclui que a preponderante apurada esta
    errada, DENTRO do documento que a afirma.

    A regra NAO e a do bloco de regime, e copia-la seria pior que nao ter. Duas atividades
    DIFERENTES precisam coexistir na mesma competencia: e comparando os quantitativos delas que a
    preponderante se apura. O que nao pode e o MESMO CNAE ter duas vigencias cobrindo o mesmo mes
    — ali nao ha o que comparar, ha um numero duplicado, e o motor pega a primeira linha que
    encontrar, de modo que o resultado passa a depender da ordem das linhas no banco.
    """
    await _tenant_estab(estab_id, current_user, db)
    # Normaliza uma vez e guarda a descricao oficial junto: ela e usada na validacao e na gravacao.
    itens: list[tuple] = []
    for it in data:
        cnae = re.sub(r"\D", "", it.cnae or "")
        if len(cnae) != 7:
            raise HTTPException(status_code=422, detail=f"CNAE '{it.cnae}' deve ter 7 dígitos.")
        oficial = (await db.execute(
            select(CnaeEnquadramento.descricao).where(CnaeEnquadramento.cnae == cnae)
        )).scalar_one_or_none()
        if oficial is None:
            raise HTTPException(status_code=422, detail=f"CNAE {cnae} não existe no Anexo I. Confira a subclasse.")
        if it.fim and it.fim < it.inicio:
            raise HTTPException(status_code=422, detail="Atividade com fim anterior ao início.")
        # A DESCRICAO VEM EM TODAS AS LINHAS, e vem do Anexo I. Era opcional, e linha sem ela
        # saia muda na memoria — um codigo de sete digitos sem nada ao lado, no documento que
        # precisa justificar por que aquela atividade e a preponderante. Nao se pede ao usuario
        # que digite o que a tabela oficial ja diz: o que ele informou prevalece, e o que faltar
        # e completado pela fonte.
        itens.append((cnae, (it.descricao or "").strip() or oficial, it))

    conflito = sobreposicao_mesmo_cnae([(c, it.inicio, it.fim) for c, _d, it in itens])
    if conflito:
        raise HTTPException(status_code=422, detail=conflito)

    antigas = (await db.execute(
        select(EstabelecimentoAtividade).where(EstabelecimentoAtividade.estabelecimento_id == estab_id)
    )).scalars().all()

    # AUTORIA PRESERVADA, MESMA REGRA DO REGIME (Carolina, 25/10).
    #
    # Este endpoint apaga a lista inteira e recria a cada salvamento. Gravar o autor cego faria
    # com que abrir a tela e salvar sem mexer em nada transferisse para quem salvou a declaracao
    # de quem declarou — e quantitativo de trabalhadores e declaracao, nao dado de cadastro:
    # e dela que sai a atividade preponderante, e e por ela que alguem responde.
    #
    # Nas palavras dela: "salvar sem alterar nao transfere autoria. O que muda e so a forma, de
    # e-mail para o nome."
    #
    # A chave e a LINHA DECLARADA inteira — atividade, quantitativo e periodo. Mudou qualquer um
    # dos tres, e outra declaracao, e o autor passa a ser quem a fez agora. A descricao fica de
    # fora de proposito: ela vem do Anexo I, nao e declarada por ninguem.
    autoria_anterior = {
        (a.cnae, a.quantitativo, a.vigencia_inicio, a.vigencia_fim): (a.declarado_por, a.declarado_em)
        for a in antigas
    }
    # NORMALIZA A GRAFIA, nao a pessoa: as linhas antigas gravaram o e-mail, e e o nome que o
    # documento imprime. Trocar "talhack@yahoo.com" por "Tales Hack" nao muda quem declarou;
    # trocar por quem esta salvando, sim — e e isso que a preservacao acima impede.
    _nomes = {e: n for e, n in (await db.execute(select(Usuario.email, Usuario.nome))).all() if e}
    quem = _autor(current_user)
    agora = datetime.now(timezone.utc)

    for a in antigas:
        await db.delete(a)
    for cnae, descricao, it in itens:
        anterior = autoria_anterior.get((cnae, it.quantitativo, it.inicio, it.fim))
        por, em = anterior if anterior and anterior[0] else (quem, agora)
        db.add(EstabelecimentoAtividade(
            estabelecimento_id=estab_id, cnae=cnae, descricao=descricao,
            quantitativo=it.quantitativo, vigencia_inicio=it.inicio, vigencia_fim=it.fim,
            declarado_por=_nomes.get(por, por), declarado_em=em or agora,
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
    return [_linha_enquadramento(r) for r in rows]


def _linha_enquadramento(r) -> dict:
    """UMA competência serializada. Extraída do corpo do endpoint da série (27/10).

    Existe como função porque três lugares precisam da mesma linha: a série mensal, o resumo do
    estabelecimento e a lista. Repetir a conversão em cada um faria a divergência ser calculada
    de três formas — e é exatamente o que a revisão da estrutura mandou evitar.
    """
    devida = float(r.aliquota_devida) if r.aliquota_devida is not None else None
    apl = float(r.aliquota_aplicada) if r.aliquota_aplicada is not None else None
    efet = float(r.aliquota_efetiva) if r.aliquota_efetiva is not None else None
    fap_dev = float(r.fap) if r.fap is not None else None
    rat_apl = float(r.rat_aplicado) if r.rat_aplicado is not None else None
    fap_apl = float(r.fap_aplicado) if r.fap_aplicado is not None else None
    orig = origem_divergencia(devida, fap_dev, rat_apl, fap_apl)
    return {
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
        "divergencia_confirmada": divergencia_confirmada(rat_apl, fap_apl),
        "situacao": situacao_de(rat_aplicavel=r.rat_aplicavel, em_fila=r.em_fila,
                                aliquota_devida=devida, rat_aplicado=rat_apl,
                                fap_aplicado=fap_apl, conferido_por=r.conferido_por),
        "motivo_conferencia": motivo_conferencia(
            rat_aplicavel=r.rat_aplicavel, em_fila=r.em_fila, motivo_fila=r.motivo_fila,
            aliquota_devida=devida, rat_aplicado=rat_apl, fap_aplicado=fap_apl),
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
    }
    return out


# ---- Resumo da janela: o que a página do estabelecimento lê no topo (revisão de 27/10) ----
#
# Endpoint PRÓPRIO, e não campos a mais em /enquadramento, porque aquele devolve uma lista pura e
# transformá-la em objeto quebraria quem já a consome. A série mensal continua como está; quem
# quer o resumo pede o resumo.
#
# Todos os números saem de api/services/resumo_enquadramento.py — as MESMAS funções que a memória
# de cálculo usa. Nas palavras dela: "a lista e a página têm que usar a mesma função, não uma
# conta nova, para a tela e o documento nunca mostrarem números diferentes."
@router.get("/{estab_id}/enquadramento/resumo")
async def resumo_enquadramento_estab(
    estab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Estado das competências, posição na janela, resumo por ano e o que falta."""
    await _tenant_estab(estab_id, current_user, db)
    rows = (await db.execute(
        select(EstabelecimentoEnquadramento)
        .where(EstabelecimentoEnquadramento.estabelecimento_id == estab_id)
        .order_by(EstabelecimentoEnquadramento.competencia)
    )).scalars().all()
    serie = [_linha_enquadramento(r) for r in rows]
    comps = [r.competencia for r in rows]
    return {
        # A janela é o período efetivamente apurado, lido da própria série — e não o período
        # cadastrado na empresa. Quando os dois divergem, é a série que diz o que existe.
        "janela": {"inicio": comps[0].isoformat() if comps else None,
                   "fim": comps[-1].isoformat() if comps else None},
        "estado": estado_na_janela(serie),
        "posicao": contagem_posicao(serie),
        "resumo_ano": resumo_por_ano(serie),
        "o_que_falta": o_que_falta(serie),
        # OS INSUMOS DO CADASTRO, ao lado das pendencias da serie (Carolina, 29/10, defeito 2).
        #
        # 'o_que_falta' le a SERIE APURADA. Estabelecimento sem atividade, sem FAP e sem RAT
        # aplicado nao tem serie nenhuma: a lista volta vazia, e a tela concluia "completo" de uma
        # lista vazia. Completo e vazio nao sao a mesma coisa — um diz que nada falta, o outro que
        # nada foi apurado, e o segundo escondia da apuracao justamente os estabelecimentos que
        # ninguem cadastrou ainda.
        #
        # A lista ja recebia este campo e nao o usava desde que as etiquetas "At · FAP · RAT"
        # sairam. A pagina nao o recebia. As duas passam a ler o mesmo, pelo mesmo motivo de
        # sempre: duas telas que respondem "o que falta" nao podem responder coisas diferentes.
        "completude": (await _completude([estab_id], db)).get(str(estab_id)),
        # AS VIGENCIAS QUE A SERIE ATRAVESSA (Carolina, 27/10, item 10 da etapa C).
        #
        # A tela dizia "Fundamentação vigente em 11/2021, início da série" e citava UMA redacao
        # para cinco anos de competencias. A serie da KRETA atravessa duas: a IN 971/2009 ate
        # 09/2022 e a IN 2.110/2022 de 10/2022 em diante. Afirmar uma so e dizer, sobre tres anos
        # de competencias, que valia uma norma que ja tinha sido substituida.
        #
        # E o mesmo defeito que a memoria de calculo corrigiu em 25/10, e a correcao e a mesma
        # funcao: citacoes_do_periodo resolve competencia por competencia, no FECHAMENTO de cada
        # uma, e colapsa em blocos de redacao igual. A tela passa a mostrar o que o documento
        # mostra, porque le do mesmo lugar.
        "fundamentacao_blocos": [
            {"de": b["de"].isoformat(), "ate": b["ate"].isoformat(),
             "dispositivo": (b["citacao"] or {}).get("dispositivo"),
             "ato": (b["citacao"] or {}).get("ato_normativo"),
             # O ANEXO FALTAVA AQUI (Carolina, 28/10, lendo a tela: "o Anexo V não aparece").
             #
             # Nao era dado ausente: as duas linhas de 'rat_devido' tem anexo cadastrado — Anexo V
             # do Decreto 3.048/99 no periodo da IN 971/2009 (migration 050) e Anexo I da propria
             # IN 2.110/2022 no periodo vigente (migration 043). A tela ja renderiza `b.anexo`.
             # Era ESTE serializador que nao mandava o campo, enquanto o da memoria (_blocos,
             # abaixo) mandava — e e o anexo que diz de onde sai o grau do CNAE, isto e, a base do
             # RAT devido. Sem ele a tela afirmava o grau sem citar a fonte.
             #
             # Os dois serializadores desenham o MESMO bloco e vivem a 300 linhas um do outro. Essa
             # duplicacao e a causa: a divergencia nao e detectavel por tipo, so por leitura. Fica
             # anotada como divida tecnica — um serializador unico, como resumo_enquadramento.py fez
             # com as agregacoes.
             "anexo": (b["citacao"] or {}).get("anexo"),
             "observacao": (b["citacao"] or {}).get("observacao"),
             "vigencia_inicio": (b["citacao"] or {}).get("vigencia_inicio"),
             "vigencia_fim": (b["citacao"] or {}).get("vigencia_fim")}
            for b in await citacoes_do_periodo("rat_devido", comps, db)
        ],
    }


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

    # NAO CONFERIVEL = a comparacao nao fecha, por qualquer das duas causas. A segunda entrou em
    # 24/10 (Carolina): aplicado sem desdobramento em RAT base e FAP admite duas leituras com
    # resultados opostos, e conferir ali seria assinar embaixo de um numero que o sistema escolheu
    # entre dois. Mesma regra de situacao_de(); se divergirem, a tela oferece o que a API recusa.
    def _nao_fecha(r) -> bool:
        return (r.em_fila or r.aliquota_devida is None
                or r.rat_aplicado is None or r.fap_aplicado is None)

    pendentes = [r for r in rows if _nao_fecha(r)]
    if pendentes and data.competencias:
        comps = ", ".join(r.competencia.strftime("%m/%Y") for r in pendentes[:5])
        falta_aplicado = all(not (r.em_fila or r.aliquota_devida is None) for r in pendentes)
        oque = ("Informe o RAT base e o FAP aplicados antes de validar."
                if falta_aplicado else
                "Resolva a pendência (FAP, atividade, CNAE) antes de validar.")
        raise HTTPException(
            status_code=422,
            detail=(f"Não é possível conferir competência em conferência: {comps}"
                    f"{'…' if len(pendentes) > 5 else ''}. {oque}"),
        )

    autor = _autor(current_user)
    agora = datetime.now(timezone.utc)
    conferidas = 0
    for r in rows:
        if _nao_fecha(r):
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
            "divergencia_confirmada": divergencia_confirmada(rat_apl, fap_apl),
            "situacao": situacao_de(rat_aplicavel=r.rat_aplicavel, em_fila=r.em_fila,
                                    aliquota_devida=devida, rat_aplicado=rat_apl,
                                    fap_aplicado=fap_apl, conferido_por=r.conferido_por),
            "motivo_conferencia": motivo_conferencia(
                rat_aplicavel=r.rat_aplicavel, em_fila=r.em_fila, motivo_fila=r.motivo_fila,
                aliquota_devida=devida, rat_aplicado=rat_apl, fap_aplicado=fap_apl),
            "rat_aplicavel": bool(r.rat_aplicavel),
            "motivo_inaplicavel": r.motivo_inaplicavel,
            "conferido_em": r.conferido_em.strftime("%d/%m/%Y") if r.conferido_em else None,
            "conferido_por": r.conferido_por,
            "em_fila": r.em_fila, "motivo_fila": r.motivo_fila,
        })
    # AUTORIA POR NOME E DATA EM FORMATO BRASILEIRO (Carolina, 25/10, item 8). Saia
    # "talhack@yahoo.com em 2026-10-19" — e-mail pessoal do desenvolvedor como autor da declaracao
    # dos quantitativos, e data no formato do banco, dentro de documento que chega ao cliente e
    # eventualmente a Receita.
    #
    # O e-mail esta GRAVADO assim nas linhas antigas, de antes de _autor() passar a preferir o
    # nome. Em vez de reescrever o dado — que seria falsificar quem declarou —, o e-mail e
    # RESOLVIDO para o nome na hora de imprimir, pela tabela de usuarios. Linha cujo autor nao
    # corresponda a usuario algum sai como esta: melhor um endereco do que um nome inventado.
    _nomes = {e: n for e, n in (await db.execute(select(Usuario.email, Usuario.nome))).all() if e}
    autoria = sorted({
        f"{_nomes.get(a.declarado_por, a.declarado_por) or 'n/d'}, "
        f"em {a.declarado_em.strftime('%d/%m/%Y')}"
        for a in ativ if a.declarado_em
    })
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
    # DOIS CAMPOS FUNDAMENTADOS, nao um (Carolina, 25/10, item 4). A memoria citava apenas
    # 'rat_devido', e por isso a Sumula 351 do STJ — que esta cadastrada em
    # 'atividade_preponderante', nas duas vigencias — nao aparecia em lugar nenhum do documento.
    # Ela sustenta a apuracao individualizada por CNPJ, que e a tese central da peca: sem ela, o
    # documento afirma o enquadramento por estabelecimento sem citar o que o ampara.
    #
    # O campo entra tambem na PORTA DE EMISSAO, pela mesma regra que ja vale para o outro: se a
    # competencia nao tem como ser fundamentada, o documento nao se completa com texto de reserva.
    _campos_fund = {"rat_devido": "RAT devido",
                    "atividade_preponderante": "atividade preponderante"}
    _comps = [r.competencia for r in serie_rows]
    fund_por_campo = {c: await citacoes_do_periodo(c, _comps, db) for c in _campos_fund}
    for _campo, _rotulo in _campos_fund.items():
        lacunas = [b for b in fund_por_campo[_campo] if b["citacao"] is None]
        if lacunas:
            faixas = "; ".join(
                b["de"].strftime("%m/%Y") + (f" a {b['ate'].strftime('%m/%Y')}" if b["ate"] != b["de"] else "")
                for b in lacunas
            )
            raise HTTPException(
                status_code=409,
                detail=("A memória não pode ser emitida: não há fundamentação cadastrada para "
                        f"{_rotulo} ('{_campo}') nestas competências: {faixas}. Cadastre a "
                        "vigência correspondente na tabela de fundamentação antes de gerar o "
                        "documento."),
            )
    fund_blocos = fund_por_campo["rat_devido"]
    def _blocos(lista):
        """Serializa os blocos de vigencia. Existe porque agora sao DOIS campos fundamentados."""
        return [
            {"de": b["de"].isoformat(), "ate": b["ate"].isoformat(),
             "dispositivo": b["citacao"]["dispositivo"],
             "ato": b["citacao"]["ato_normativo"],
             "anexo": b["citacao"]["anexo"],
             "observacao": b["citacao"]["observacao"],
             "estruturado": b["citacao"]["estruturado"],
             "vigencia_inicio": b["citacao"]["vigencia_inicio"],
             "vigencia_fim": b["citacao"]["vigencia_fim"]}
            for b in lista
        ]

    # AS CITACOES DO BLOCO CPRB (Carolina, 26/10). A tela passou a ter um campo por regra:
    # 'cprb' fundamenta a opcao anual, 'cprb_proporcao' as proporcoes da transicao e
    # 'cprb_decimo_terceiro' a ressalva do 13º junto da permanencia do RAT e dos Terceiros. A
    # memoria imprime as MESMAS frases, e o pedido foi explicito: "a mesma frase sai na memoria de
    # calculo, entao confere que la tambem aparecem as duas citacoes".
    #
    # Resolve no FECHAMENTO do ano-calendario, pelo mesmo criterio que governa os demais cortes de
    # vigencia do documento (ver TEXTO_CRITERIO_VIGENCIA). Ano sem linha cadastrada sai da lista em
    # silencio — e a mesma regra da tela: sem citacao, nao se exibe citacao. E por isso que este
    # agrupamento nao precisa saber quais anos sao de transicao: quem decide e a vigencia da linha.
    _anos_cprb = sorted({c.inicio.year for c in cprb_rows})

    def _rotulo_cprb(campo: str, c: dict) -> str:
        """O rotulo descreve a REGRA daquela redacao, nao o campo (Carolina, 26/10, à noite).

        Ela: "'Proporcoes da transicao (anos 2023, 2024)' deve se chamar 'Substituicao integral'.
        Transicao e so de 2025 a 2027."

        O rotulo era fixo por campo, e 'cprb_proporcao' tem duas vigencias de naturezas opostas:
        ate 2024 a CPRB substitui os incisos I e III por INTEIRO, e de 2025 a 2027 convive com
        eles em proporcao. Chamar as duas de "transicao" dava ao periodo antigo o nome do regime
        que o sucedeu — e e o tipo de rotulo que, lido depressa, faz supor patronal parcial onde
        nao havia nenhuma.

        O corte vem de ANO_INICIO_TRANSICAO, a mesma constante que governa o resto do bloco, e
        nao de um ano escrito aqui.
        """
        if campo == "cprb":
            return "Opção anual"
        if campo == "cprb_proporcao":
            return ("Proporções da transição"
                    if c["vigencia_inicio"] >= f"{ANO_INICIO_TRANSICAO_CPRB}-01-01"
                    else "Substituição integral")
        return "Décimo terceiro, RAT e Terceiros"

    async def _fund_cprb(campo: str) -> list[dict]:
        """Uma entrada por REDACAO, com os anos que ela governa — nao uma por ano.

        Empresa optante desde 2021 tem seis ou sete anos declarados; repetir a mesma citacao
        sete vezes dentro de peca assinada e ruido que esconde a unica coisa que importa ali,
        que e onde a redacao mudou.

        Agrupa por (dispositivo, rotulo), e nao so pelo dispositivo: desde que o rotulo passou a
        depender da vigencia, duas redacoes com o mesmo texto de citacao e nomes diferentes
        precisam sair em linhas separadas, cada uma com os seus anos.
        """
        agrupado: dict[tuple, dict] = {}
        for ano in _anos_cprb:
            c = await citacao_de(campo, date(ano, 12, 31), db)
            if not c:
                continue
            rot = _rotulo_cprb(campo, c)
            bloco = agrupado.setdefault((c["dispositivo"], rot), {
                "rotulo": rot,
                "dispositivo": c["dispositivo"],
                "observacao": c["observacao"],
                "anos": [],
            })
            bloco["anos"].append(str(ano))
        return [{**b, "anos": ", ".join(b["anos"])} for b in agrupado.values()]

    fund_cprb = (
        await _fund_cprb("cprb")
        + await _fund_cprb("cprb_proporcao")
        + await _fund_cprb("cprb_decimo_terceiro")
    )

    # A CITACAO DA SUBSTITUICAO INTEGRAL, para dentro da frase (Carolina, 26/10, à noite).
    #
    # A frase que ela redigiu cita o dispositivo no meio do texto — "a CPRB as substitui
    # integralmente (Lei 12.546/2011, arts. 7º e 8º)". A citacao vem da TABELA, e nao escrita no
    # gerador: literal de citacao dentro do codigo da memoria foi uma das tres fontes que a
    # decisao de 21/10 eliminou, e e justamente o documento assinado que ela atingia.
    #
    # Resolve no ano de opcao mais recente ate 2024, que e o fim do periodo que a frase descreve.
    # Vem sem as notas do dispositivo: a nota desta linha diz "substituicao total das
    # contribuicoes dos incisos I e III do art. 22 da Lei 8.212/91", que e exatamente o que a
    # frase acabou de dizer — repeti-la entre parenteses dentro de parenteses nao se le.
    _anos_integrais = [a for a in _anos_cprb if a < ANO_INICIO_TRANSICAO_CPRB]
    _cit_integral = None
    if _anos_integrais:
        _c = await citacao_de("cprb_proporcao", date(max(_anos_integrais), 12, 31), db)
        _cit_integral = _c["dispositivo_curto"] if _c else None

    dados = {
        # CNPJ DA MATRIZ INTEIRO, nao a raiz (Carolina, 25/10, item 3). Era truncado em [:8] de
        # quando o rotulo dizia "CNPJ raiz"; o rotulo mudou em 23/10 e o truncamento ficou, entao
        # o documento exibia oito digitos chamados de CNPJ da matriz. A formatacao e feita no
        # gerador, junto das demais.
        "empresa": {"razao_social": empresa.razao_social if empresa else None,
                    "cnpj": (empresa.cnpj if empresa and empresa.cnpj else None)},
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
        "fundamentacao_blocos": _blocos(fund_blocos),
        "fundamentacao_preponderante": _blocos(fund_por_campo["atividade_preponderante"]),
        "autoria": autoria,
        "cprb": {
            "status": (empresa.cprb_status if empresa else None) or "nao_informado",
            # AUTOR PELO NOME, como a autoria das atividades logo acima (ponto 2 da revisao de
            # 26/10). O mapa _nomes ja estava montado algumas linhas acima e servia a um bloco so:
            # a memoria imprimia "Tales Hack" na declaracao dos quantitativos e o e-mail aqui, na
            # mesma pagina. Autor que nao corresponda a usuario algum sai como esta gravado.
            "verificado_por": (_nomes.get(empresa.cprb_verificado_por, empresa.cprb_verificado_por)
                               if empresa else None),
            # HORA, e de Brasilia. O campo e gravado com timezone.utc; imprimir %H:%M cru mostraria
            # 13:51 onde foram 10:51 — o item 8 da revisao de 25/10, repetido neste bloco. Mesmo
            # offset fixo do gerado_em, logo abaixo, e pela mesma razao.
            "verificado_em": (empresa.cprb_verificado_em
                              .astimezone(timezone(timedelta(hours=-3)))
                              .strftime("%d/%m/%Y às %H:%M")
                              if (empresa and empresa.cprb_verificado_em) else None),
            "periodos": [{"inicio": c.inicio.isoformat(), "fim": c.fim.isoformat() if c.fim else None} for c in cprb_rows],
            "fundamentacao": fund_cprb,
            "citacao_substituicao_integral": _cit_integral,
        },
        # HORARIO DE BRASILIA, nao UTC (Carolina, 25/10, item 8). "13:51 UTC" num documento que o
        # cliente le obriga quem o le a converter de cabeca, e convida a erro de uma hora em
        # discussao de prazo. Offset fixo de -3h de proposito, sem depender da base de fusos do
        # sistema: o Brasil nao adota horario de verao desde 2019, e um container sem tzdata
        # devolveria UTC em silencio — que e o defeito que estamos corrigindo.
        "gerado_em": datetime.now(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y às %H:%M"),
    }
    pdf = gerar_memoria_pdf(dados)

    # A EMISSAO PASSA A SER REGISTRADA, COM O DOCUMENTO (Carolina, 27/10). "Os dados mudam e a
    # memoria gerada depois sai diferente. Se um dia questionarem o que constava numa memoria que
    # foi para uma peca, o registro precisa conseguir mostrar o documento exatamente como saiu."
    #
    # A chave e o CONTEUDO, nao o arquivo: o PDF imprime a hora de geracao e muda a cada clique.
    # Reemitir o mesmo caso atualiza a ultima emissao; dados diferentes viram registro novo, com
    # a sua propria copia — que e o fato a provar.
    #
    # ESTE REGISTRO NAO PODE DERRUBAR A EMISSAO. Recusar o documento a quem pediu porque o
    # arquivamento falhou seria trocar um problema por um pior; a falha vai para o log e o PDF
    # segue. O commit e explicito porque este endpoint, ate aqui, so lia.
    try:
        await registrar_emissao(
            db,
            empresa_id=estab.empresa_id,
            estabelecimento_id=estab.id,
            pdf=pdf,
            chave_conteudo=sha256_do_conteudo(dados),
            autor=_autor(current_user),
            competencia_inicio=_comps[0] if _comps else None,
            competencia_fim=_comps[-1] if _comps else None,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Falha ao registrar a emissão da memória do estabelecimento %s", estab.id)

    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename=memoria_enquadramento_{estab.codigo}.pdf"})
