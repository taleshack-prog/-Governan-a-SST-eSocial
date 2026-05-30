# ==============================================================
# SST ESOCIAL GOV — PGR Extractor
# Arquivo: ai-layer/extractors/pgr_extractor.py
# ==============================================================


class PGRExtractor:
    """Extrai riscos e medidas de controle do PGR."""

    NIVEIS_RISCO = {"trivial": 1, "tolerável": 2, "moderado": 3, "substancial": 4, "intolerável": 5}

    def extrair_riscos(self, texto: str) -> list[dict]:
        riscos = []
        linhas = texto.split("\n")
        for linha in linhas:
            linha_lower = linha.lower()
            nivel = None
            for n, v in self.NIVEIS_RISCO.items():
                if n in linha_lower:
                    nivel = {"nome": n, "valor": v}
                    break
            if nivel and len(linha) > 20:
                riscos.append({
                    "descricao": linha.strip()[:200],
                    "nivel_risco": nivel,
                    "trecho_original": linha.strip(),
                })
        return riscos
