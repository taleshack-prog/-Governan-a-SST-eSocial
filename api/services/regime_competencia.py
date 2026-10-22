# api/services/regime_competencia.py — SST ESOCIAL GOV
# Qual regime vigia numa competencia, e se ele afasta a apuracao do RAT.
#
# POR QUE ESTE MODULO EXISTE. Ate 22/10 o motor nunca consultou o regime: a tabela
# 'empresa_regime' era gravada pela tela e lida de volta pela tela, e nenhum calculo a tocava.
# O efeito so apareceu quando a Carolina gravou uma empresa como Simples Nacional, Anexo III,
# cobrindo toda a janela: o enquadramento seguiu apurando RAT devido de 3,00% e concluindo que
# havia credito a recuperar, em 58 competencias. Credito que nao existe.
#
# A REGRA, confirmada pela Carolina em 21/10:
#   - No Simples Nacional a contribuicao patronal do art. 22 da Lei 8.212/91 integra o documento
#     unico de arrecadacao nos Anexos I, II, III e V — e o RAT vai junto, por ser o inciso II
#     daquele artigo —, por forca do art. 13, VI, da LC 123/2006.
#   - So as atividades do art. 18, §5o-C (Anexo IV) ficam de fora: nelas a patronal e recolhida
#     pela legislacao geral, com RAT e FAP.
#   - Nenhum optante deve contribuicoes a Terceiros, em anexo nenhum (art. 13, §3o).
#
# A REGRA DE ENGENHARIA, dela tambem: caso nao coberto vai para a FILA DE CONFERENCIA, nunca
# para uma premissa no codigo. Por isso este modulo distingue "nao se aplica" de "nao sei", e
# jamais transforma o segundo no primeiro.
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.empresa_regime import EmpresaRegime

# Os cinco anexos, como a lista fechada da tela grava desde 21/10.
ANEXOS_VALIDOS = {"I", "II", "III", "IV", "V"}
ANEXO_COM_PATRONAL_APARTE = "IV"

CERTO = "certo"
AUSENTE = "ausente"
AMBIGUO = "ambiguo"


def _comp(c: date) -> str:
    return f"{c.month:02d}/{c.year}"


async def regime_da_competencia(empresa_id, comp: date, db: AsyncSession) -> dict:
    """Regime e anexo vigentes na competencia, com veredito de certeza.

    Devolve sempre um dict com 'certeza'. So 'certo' autoriza decidir; 'ausente' e 'ambiguo'
    mandam a competencia a conferencia, com o motivo escrito.
    """
    linhas = (await db.execute(
        select(EmpresaRegime).where(EmpresaRegime.empresa_id == empresa_id)
        .order_by(EmpresaRegime.inicio)
    )).scalars().all()

    vigentes = [r for r in linhas
                if r.inicio <= comp and (r.fim is None or r.fim >= comp)]

    if not vigentes:
        return {"certeza": AUSENTE, "regime": None, "anexo": None,
                "motivo": f"Nenhum período de regime tributário cobre {_comp(comp)}."}

    if len(vigentes) > 1:
        # A tela passou a barrar sobreposicao em 21/10, mas dado antigo pode ter passado antes
        # disso. Dois regimes na mesma competencia nao tem desempate possivel — e nao se
        # inventa um aqui.
        quais = ", ".join(sorted({r.regime for r in vigentes}))
        return {"certeza": AMBIGUO, "regime": None, "anexo": None,
                "motivo": (f"Mais de um período de regime cobre {_comp(comp)} ({quais}). "
                           f"Corrija a sobreposição no cadastro da empresa.")}

    r = vigentes[0]
    if r.regime != "simples":
        return {"certeza": CERTO, "regime": r.regime, "anexo": None, "motivo": None}

    bruto = (r.anexo_simples or "").strip().upper()
    if bruto not in ANEXOS_VALIDOS:
        # Texto livre anterior a lista fechada — "4", "anexo 4", vazio. NAO se adivinha: o anexo
        # decide se ha ou nao RAT a apurar, e errar aqui troca credito por passivo no laudo.
        visto = f" (consta \"{r.anexo_simples}\")" if (r.anexo_simples or "").strip() else ""
        return {"certeza": AMBIGUO, "regime": "simples", "anexo": None,
                "motivo": (f"Simples Nacional em {_comp(comp)} sem anexo reconhecido{visto}. "
                           f"Informe o anexo (I a V) no cadastro da empresa.")}

    return {"certeza": CERTO, "regime": "simples", "anexo": bruto, "motivo": None}


def rat_se_aplica(regime: str | None, anexo: str | None) -> tuple[bool, str | None]:
    """Se ha RAT a apurar sob esse regime. Chamar APENAS com veredito 'certo'.

    Devolve (aplica, motivo_quando_nao_aplica). O motivo e escrito para ser lido por quem assina
    a peca, nao por quem le o codigo.
    """
    if regime == "simples" and anexo and anexo != ANEXO_COM_PATRONAL_APARTE:
        return False, (
            f"Simples Nacional, Anexo {anexo}: a contribuição patronal integra o documento único "
            f"de arrecadação, e o RAT vai com ela. Não há RAT nem contribuições a Terceiros a "
            f"apurar nesta competência."
        )
    return True, None
