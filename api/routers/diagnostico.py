# api/routers/diagnostico.py — SST ESOCIAL GOV
# Etapa 2 (v2) / Alteração 2 — tela inicial: diagnóstico dos 4 blocos.
# RAT×FAP é calculado de verdade (motor 2A); Cota Patronal, Terceiros e FGTS ficam
# em "pendência" (amarelo) até o módulo de Folha existir (Etapa 3).
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.usuario import Usuario
from api.auth import get_current_user
from api.services.motor_ratfap import calcular_ratfap

router = APIRouter()


def _bloco_pendente(nome: str, motivo: str) -> dict:
    return {
        "bloco": nome,
        "semaforo": "amarelo",
        "exibicao": "Pendência de informação",
        "valor_pago_mensal": None,
        "valor_esperado_mensal": None,
        "diferenca_mensal": None,
        "impacto_anual_estimado": None,
        "motivo": motivo,
    }


_EXIBICAO = {
    "verde": "Conferido",
    "amarelo": "Pendência de informação",
    "vermelho": "Divergência identificada",
}


@router.get("/blocos")
async def diagnostico_blocos(
    ano: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Os 4 blocos da tela inicial para a empresa do usuário logado."""
    empresa_id = current_user.empresa_id

    ratfap = await calcular_ratfap(empresa_id, db, ano=ano)
    ratfap["exibicao"] = _EXIBICAO.get(ratfap.get("semaforo"), "")

    cota_patronal = _bloco_pendente(
        "Cota Patronal", "Depende da folha de pagamento importada (Módulo de Folha)")
    terceiros = _bloco_pendente(
        "Terceiros", "Depende do código FPAS e da folha (Módulo de Folha)")
    fgts = _bloco_pendente(
        "FGTS", "Depende da folha de pagamento importada (Módulo de Folha)")

    blocos = [cota_patronal, ratfap, terceiros, fgts]

    divergentes = sum(1 for b in blocos if b.get("semaforo") == "vermelho")
    pendentes = sum(1 for b in blocos if b.get("semaforo") == "amarelo")

    return {
        "empresa_id": str(empresa_id),
        "resumo": {
            "blocos_divergentes": divergentes,
            "blocos_pendentes": pendentes,
            "blocos_conferidos": sum(1 for b in blocos if b.get("semaforo") == "verde"),
        },
        "blocos": blocos,
    }
