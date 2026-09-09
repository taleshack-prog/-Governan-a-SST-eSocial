# api/services/cadastro_completo.py — SST ESOCIAL GOV
# Módulo 0 / RF-0.07 — Regra de cadastro bloqueante.
# Verifica se uma empresa tem os dados essenciais para que os módulos de cálculo
# possam rodar. Retorna o que falta, em texto claro, para o frontend exibir
# (RF-0.07) e para os futuros módulos de cálculo consultarem antes de calcular.
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.empresa import Empresa
from api.models.estabelecimento import Estabelecimento
from api.models.questionario_resposta import QuestionarioResposta

PERGUNTAS_ESSENCIAIS = ["alimentacao_forma"]


async def verificar_cadastro(empresa_id: UUID, db: AsyncSession) -> dict:
    """Retorna {'completo': bool, 'faltando': [str], 'detalhe': {...}}.

    Critérios (RF-0.07 + RF-0.01/0.03/0.06):
      1. Empresa com cnae_principal, regime_tributario e codigo_fpas.
      2. Pelo menos 1 estabelecimento com grau_risco e aliquota_rat definidos.
      3. Pelo menos 1 estabelecimento com posicao='matriz'.
      4. Perguntas essenciais do questionário respondidas.
    """
    faltando: list[str] = []

    empresa = (await db.execute(
        select(Empresa).where(Empresa.id == empresa_id)
    )).scalar_one_or_none()

    if empresa is None:
        return {"completo": False, "faltando": ["Empresa não encontrada"], "detalhe": {}}

    if not empresa.cnae_principal:
        faltando.append("CNAE principal da empresa")
    if not empresa.regime_tributario:
        faltando.append("Regime tributário da empresa")
    if not empresa.codigo_fpas:
        faltando.append("Código FPAS da empresa (define a composição de Terceiros)")

    estabs = (await db.execute(
        select(Estabelecimento).where(Estabelecimento.empresa_id == empresa_id)
    )).scalars().all()

    if not estabs:
        faltando.append("Pelo menos um estabelecimento cadastrado")
    else:
        com_rat = [e for e in estabs if e.grau_risco is not None and e.aliquota_rat is not None]
        if not com_rat:
            faltando.append("Grau de risco e RAT em pelo menos um estabelecimento")

        tem_matriz = any(e.posicao == "matriz" for e in estabs)
        if not tem_matriz:
            faltando.append("Um estabelecimento marcado como matriz (sede)")

    respondidas = (await db.execute(
        select(QuestionarioResposta.pergunta_codigo)
        .where(QuestionarioResposta.empresa_id == empresa_id)
        .distinct()
    )).scalars().all()
    respondidas_set = set(respondidas)

    for pergunta in PERGUNTAS_ESSENCIAIS:
        if pergunta not in respondidas_set:
            faltando.append(f"Resposta do questionário: {pergunta}")

    completo = len(faltando) == 0
    return {
        "completo": completo,
        "faltando": faltando,
        "detalhe": {
            "empresa_id": str(empresa_id),
            "num_estabelecimentos": len(estabs),
            "perguntas_respondidas": sorted(respondidas_set),
        },
    }
