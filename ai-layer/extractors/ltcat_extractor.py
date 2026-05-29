# ==============================================================
# SST ESOCIAL GOV — LTCAT Extractor
# Arquivo: ai-layer/extractors/ltcat_extractor.py
# ==============================================================

import re
from typing import Optional


class LTCATExtractor:
    """
    Extrai informações estruturadas de laudos LTCAT.
    Foco: agentes nocivos, níveis de exposição, EPC/EPI, datas de vigência.
    """

    SECOES_AGENTES = [
        r"agente(?:s)?\s+(?:nocivo|físico|químico|biológico)",
        r"exposição\s+(?:a\s+)?agente",
        r"fator(?:es)?\s+de\s+risco",
        r"riscos?\s+ambientais?",
    ]

    def extrair_agentes(self, texto: str) -> list[dict]:
        """Extrai lista de agentes nocivos do texto do LTCAT."""
        agentes = []
        paragrafos = texto.split("\n")

        for i, par in enumerate(paragrafos):
            par_lower = par.lower()

            # Detectar parágrafo relevante
            relevante = any(re.search(p, par_lower) for p in self.SECOES_AGENTES)
            if not relevante and len(par) < 30:
                continue

            agente = {}

            # Ruído
            nivel_ruido = self._extrair_ruido(par)
            if nivel_ruido:
                agente = {
                    "tipo": "fisico",
                    "descricao": f"Ruído — {nivel_ruido} dB(A)",
                    "valor": nivel_ruido,
                    "unidade": "dB(A)",
                    "trecho_original": par.strip(),
                }

            # Calor / IBUTG
            ibutg = self._extrair_ibutg(par)
            if ibutg:
                agente = {
                    "tipo": "fisico",
                    "descricao": f"Calor — IBUTG {ibutg}°C",
                    "valor": ibutg,
                    "unidade": "°C IBUTG",
                    "trecho_original": par.strip(),
                }

            # Químicos por nome
            quimico = self._extrair_quimico(par)
            if quimico:
                agente = {
                    "tipo": "quimico",
                    "descricao": quimico,
                    "trecho_original": par.strip(),
                }

            if agente:
                agente["epi_mencionado"] = "epi" in par_lower or "proteção" in par_lower
                agente["epc_mencionado"] = "epc" in par_lower or "controle coletivo" in par_lower
                agentes.append(agente)

        return agentes

    def extrair_responsavel(self, texto: str) -> dict:
        """Extrai dados do responsável técnico (engenheiro de segurança / médico)."""
        resultado = {}
        # CREA / CRQ / CRM
        match = re.search(r"CREA[:\s]*([A-Z0-9\-/]+)", texto, re.IGNORECASE)
        if match:
            resultado["conselho"] = "CREA"
            resultado["registro"] = match.group(1).strip()

        match = re.search(r"CRQ[:\s]*([A-Z0-9\-/]+)", texto, re.IGNORECASE)
        if match:
            resultado["conselho"] = "CRQ"
            resultado["registro"] = match.group(1).strip()

        return resultado

    def _extrair_ruido(self, texto: str) -> Optional[float]:
        patterns = [
            r"(\d{2,3}(?:[,.]\d)?)\s*dB\s*\(?A\)?",
            r"(\d{2,3}(?:[,.]\d)?)\s*dBA",
        ]
        for p in patterns:
            m = re.search(p, texto, re.IGNORECASE)
            if m:
                return float(m.group(1).replace(",", "."))
        return None

    def _extrair_ibutg(self, texto: str) -> Optional[float]:
        m = re.search(r"IBUTG[:\s=]*(\d{2}(?:[,.]\d)?)", texto, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(",", "."))
        return None

    def _extrair_quimico(self, texto: str) -> Optional[str]:
        QUIMICOS = ["benzeno", "chumbo", "mercúrio", "sílica", "amianto", "asbesto", "arsênio", "cromo"]
        texto_lower = texto.lower()
        for q in QUIMICOS:
            if q in texto_lower:
                return q.capitalize()
        return None
