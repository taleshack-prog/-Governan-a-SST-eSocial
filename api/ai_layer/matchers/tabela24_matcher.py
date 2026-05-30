# ==============================================================
# SST ESOCIAL GOV — Tabela 24 Matcher
# Arquivo: ai-layer/matchers/tabela24_matcher.py
# Mapeia descrições textuais de agentes nocivos → código Tabela 24 eSocial
# ==============================================================

import re
from typing import Optional


# Whitelist completa dos 23 códigos implementados
TABELA24_WHITELIST = {
    "01.01.001": {"grupo": "fisico",    "descricao": "Ruído acima dos limites de tolerância NR-15 Anexo I",               "keywords": ["ruído", "ruido", "decibel", "db", "dba", "noise"]},
    "01.02.001": {"grupo": "fisico",    "descricao": "Calor acima dos limites NR-15 Anexo III",                            "keywords": ["calor", "temperatura", "ibutg", "heat", "thermal"]},
    "01.03.001": {"grupo": "fisico",    "descricao": "Frio abaixo dos limites NR-15 Anexo IX",                             "keywords": ["frio", "câmara fria", "cold", "temperatura baixa"]},
    "01.04.001": {"grupo": "fisico",    "descricao": "Umidade acima dos limites NR-15 Anexo X",                            "keywords": ["umidade", "umido", "úmido", "humidity"]},
    "01.05.001": {"grupo": "fisico",    "descricao": "Radiações ionizantes",                                               "keywords": ["radiação", "raio x", "raio gama", "ionizante", "radiation"]},
    "01.06.001": {"grupo": "fisico",    "descricao": "Vibrações localizadas mãos e braços NR-15 Anexo VIII",              "keywords": ["vibração", "vibracao", "mãos", "braços", "segmental", "hand arm"]},
    "01.06.002": {"grupo": "fisico",    "descricao": "Vibrações de corpo inteiro NR-15 Anexo VIII",                       "keywords": ["vibração corpo inteiro", "whole body", "vibração de corpo"]},
    "01.07.001": {"grupo": "fisico",    "descricao": "Pressões hiperbáricas",                                              "keywords": ["hiperbárica", "hiperbar", "pressão elevada", "mergulho"]},
    "02.01.001": {"grupo": "quimico",   "descricao": "Arsênio e seus compostos",                                           "keywords": ["arsênio", "arsenio", "arsenic"]},
    "02.02.001": {"grupo": "quimico",   "descricao": "Chumbo e seus compostos iônicos",                                    "keywords": ["chumbo", "lead", "plumbum"]},
    "02.03.001": {"grupo": "quimico",   "descricao": "Cromo hexavalente e seus compostos",                                 "keywords": ["cromo", "cromato", "chromium", "cromo hexavalente"]},
    "02.04.001": {"grupo": "quimico",   "descricao": "Benzeno e seus derivados",                                           "keywords": ["benzeno", "benzene", "tolueno", "xileno"]},
    "02.05.001": {"grupo": "quimico",   "descricao": "Mercúrio e seus compostos",                                          "keywords": ["mercúrio", "mercurio", "mercury"]},
    "02.06.001": {"grupo": "quimico",   "descricao": "Sílica livre cristalizada",                                          "keywords": ["sílica", "silica", "quartzo", "quartz", "silicose"]},
    "02.07.001": {"grupo": "quimico",   "descricao": "Asbesto (amianto)",                                                  "keywords": ["asbesto", "amianto", "asbestos", "amiante"]},
    "02.08.001": {"grupo": "quimico",   "descricao": "Poeiras minerais (exceto sílica e amianto)",                        "keywords": ["poeira mineral", "poeira", "dust", "particulado"]},
    "03.01.001": {"grupo": "biologico", "descricao": "Agentes biológicos: vírus",                                          "keywords": ["vírus", "virus", "viral", "viremia"]},
    "03.02.001": {"grupo": "biologico", "descricao": "Agentes biológicos: bactérias",                                      "keywords": ["bactéria", "bacteria", "bacteriana", "microbio"]},
    "03.03.001": {"grupo": "biologico", "descricao": "Agentes biológicos: fungos",                                         "keywords": ["fungo", "fungi", "mold", "mofo"]},
    "03.04.001": {"grupo": "biologico", "descricao": "Agentes biológicos: parasitas",                                      "keywords": ["parasita", "parasitic", "helminto"]},
    "03.05.001": {"grupo": "biologico", "descricao": "Agentes biológicos: coleta de lixo",                                 "keywords": ["lixo", "resíduo", "coleta", "aterro", "residuo"]},
    "03.06.001": {"grupo": "biologico", "descricao": "Agentes biológicos: atividades em cemitérios",                      "keywords": ["cemitério", "velório", "necropsia", "funeral"]},
    "03.07.001": {"grupo": "biologico", "descricao": "Agentes biológicos: hospitais/laboratórios",                        "keywords": ["hospital", "laboratório", "laboratorio", "clínica", "saúde", "material biológico"]},
}


class Tabela24Matcher:
    """
    Mapeia descrições textuais de agentes nocivos para códigos da Tabela 24 eSocial.
    Usa correspondência por keywords com scoring de confiança.
    """

    def codigo_valido(self, codigo: str) -> bool:
        """HAL-001: Verifica se o código está na whitelist."""
        return codigo in TABELA24_WHITELIST

    def buscar_por_descricao(self, descricao: str) -> list[dict]:
        """
        Retorna lista de correspondências ordenadas por score.
        Cada item: {codigo, descricao, score, grupo}
        """
        descricao_lower = descricao.lower()
        resultados = []

        for codigo, info in TABELA24_WHITELIST.items():
            score = 0
            matches = []
            for kw in info["keywords"]:
                if kw in descricao_lower:
                    score += 1
                    matches.append(kw)

            if score > 0:
                resultados.append({
                    "codigo": codigo,
                    "descricao": info["descricao"],
                    "grupo": info["grupo"],
                    "score": score / len(info["keywords"]),
                    "keywords_matched": matches,
                })

        # Ordenar por score decrescente
        return sorted(resultados, key=lambda x: x["score"], reverse=True)

    def melhor_match(self, descricao: str) -> Optional[dict]:
        """Retorna o melhor match ou None se score < 0.1."""
        resultados = self.buscar_por_descricao(descricao)
        if resultados and resultados[0]["score"] >= 0.1:
            return resultados[0]
        return None

    def extrair_nivel_ruido(self, texto: str) -> Optional[float]:
        """Extrai nível de ruído em dB(A) do texto do LTCAT."""
        patterns = [
            r"(\d{2,3}(?:[,.]\d)?)\s*dB\(?A\)?",
            r"(\d{2,3}(?:[,.]\d)?)\s*decibels?",
            r"nível de ruído[^\d]*(\d{2,3}(?:[,.]\d)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", "."))
        return None
