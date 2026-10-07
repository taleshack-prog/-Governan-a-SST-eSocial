# api/services/cnpj_lookup.py — SST ESOCIAL GOV
# Consulta de dados publicos cadastrais do CNPJ (Adendo 03 RF-0.150).
# A chamada sai do BACKEND (cache/limite/auditoria/chave), nunca do navegador.
# O provedor fica atras de um adapter: trocar BrasilAPI por Serpro e CONFIG, nao reescrita.
# Todo dado consultado volta marcado como "consultado, nao confirmado" (origem + data/hora);
# o usuario confirma antes de valer. A memoria de enquadramento NUNCA cita a API como fonte.
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx

from api.config import settings


class CnpjConsultaError(Exception):
    """Falha de consulta (indisponivel, nao encontrado, limite). O chamador cai para manual."""


class CnpjProvider(ABC):
    nome: str = "abstract"

    @abstractmethod
    async def consultar(self, cnpj: str) -> dict:
        ...


class BrasilAPIProvider(CnpjProvider):
    nome = "brasilapi"
    BASE = "https://brasilapi.com.br/api/cnpj/v1"

    async def consultar(self, cnpj: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=settings.cnpj_timeout) as client:
                resp = await client.get(f"{self.BASE}/{cnpj}")
        except httpx.HTTPError as e:
            raise CnpjConsultaError(f"Consulta indisponivel: {e}") from e
        if resp.status_code == 404:
            raise CnpjConsultaError("CNPJ nao encontrado na base publica.")
        if resp.status_code == 429:
            raise CnpjConsultaError("Limite de consultas atingido. Tente mais tarde ou preencha manualmente.")
        if resp.status_code >= 400:
            raise CnpjConsultaError(f"Consulta retornou {resp.status_code}.")
        d = resp.json()
        cnae_principal = str(d.get("cnae_fiscal") or "").zfill(7) if d.get("cnae_fiscal") else None
        secundarios = [
            {"codigo": str(c.get("codigo") or "").zfill(7), "descricao": c.get("descricao")}
            for c in (d.get("cnaes_secundarios") or []) if c.get("codigo")
        ]
        cep = re.sub(r"\D", "", str(d.get("cep") or ""))
        return {
            "razao_social": d.get("razao_social"),
            "nome_fantasia": d.get("nome_fantasia"),
            "cnae_principal": cnae_principal,
            "cnae_principal_descricao": d.get("cnae_fiscal_descricao"),
            "cnaes_secundarios": secundarios,
            "logradouro": d.get("logradouro"),
            "numero": d.get("numero"),
            "complemento": d.get("complemento"),
            "bairro": d.get("bairro"),
            "municipio": d.get("municipio"),
            "uf": d.get("uf"),
            "cep": f"{cep[:5]}-{cep[5:]}" if len(cep) == 8 else (cep or None),
            "situacao_cadastral": d.get("descricao_situacao_cadastral"),
            "data_abertura": d.get("data_inicio_atividade"),   # excecao ano-calendario CPRB (RF-0.164)
        }


_PROVIDERS = {"brasilapi": BrasilAPIProvider}


def get_provider() -> CnpjProvider:
    cls = _PROVIDERS.get((settings.cnpj_provider or "brasilapi").lower())
    if cls is None:
        raise CnpjConsultaError(f"Provider de CNPJ '{settings.cnpj_provider}' nao configurado.")
    return cls()


async def consultar_cnpj(cnpj_raw: str) -> dict:
    """Consulta e devolve os dados normalizados, carimbados com origem e data/hora.
    Marca 'consultado, nao confirmado' — o usuario confirma antes de o dado valer."""
    cnpj = re.sub(r"\D", "", cnpj_raw or "")
    if len(cnpj) != 14:
        raise CnpjConsultaError("CNPJ deve ter 14 digitos.")
    provider = get_provider()
    dados = await provider.consultar(cnpj)
    dados.update({
        "origem": "consultado",
        "confirmado": False,
        "provedor": provider.nome,
        "consultado_em": datetime.now(timezone.utc).isoformat(),
    })
    return dados
