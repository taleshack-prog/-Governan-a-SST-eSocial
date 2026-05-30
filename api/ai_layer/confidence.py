# ==============================================================
# SST ESOCIAL GOV — Confidence Scorer (GRADE-like)
# Arquivo: ai-layer/confidence.py
# Escala: A (≥0.90) B (≥0.75) C (≥0.60) D (≥0.40) F (<0.40)
# ==============================================================


class GradeScorer:
    """
    Calcula score de confiança da validação IA com modelo GRADE adaptado para SST.

    Fatores considerados:
    - Qualidade da extração (agentes encontrados vs esperados)
    - Correspondência com Tabela 24 (match score)
    - Ausência de inconsistências cross-document
    - Fundamentação normativa (NR citada)
    - Número de alertas gerados
    - Presença de dados quantitativos (dB, °C, ppm)
    """

    GRADE_LABELS = [
        (0.90, "A"),
        (0.75, "B"),
        (0.60, "C"),
        (0.40, "D"),
        (0.00, "F"),
    ]

    REVIEW_THRESHOLD = 0.75

    def calcular(self, pipeline_result) -> dict:
        score = 0.0
        detalhes = {}

        # Fator 1: Agentes extraídos (peso 0.30)
        n_agentes = len(pipeline_result.agentes_extraidos)
        fator_extracao = min(1.0, n_agentes / 3) * 0.30
        score += fator_extracao
        detalhes["fator_extracao"] = round(fator_extracao, 3)

        # Fator 2: Códigos Tabela 24 sugeridos (peso 0.30)
        n_codigos = len(pipeline_result.codigos_sugeridos)
        fator_codigos = min(1.0, n_codigos / max(n_agentes, 1)) * 0.30
        score += fator_codigos
        detalhes["fator_codigos"] = round(fator_codigos, 3)

        # Fator 3: Sem erros críticos (peso 0.20)
        n_erros = len(pipeline_result.erros)
        fator_erros = max(0.0, 1.0 - (n_erros * 0.25)) * 0.20
        score += fator_erros
        detalhes["fator_erros"] = round(fator_erros, 3)

        # Fator 4: Alertas (peso 0.20) — penaliza alertas
        n_alertas = len(pipeline_result.alertas)
        fator_alertas = max(0.0, 1.0 - (n_alertas * 0.15)) * 0.20
        score += fator_alertas
        detalhes["fator_alertas"] = round(fator_alertas, 3)

        score = round(min(score, 1.0), 4)

        # Determinar label GRADE
        label = "F"
        for threshold, lbl in self.GRADE_LABELS:
            if score >= threshold:
                label = lbl
                break

        return {
            "score": score,
            "label": label,
            "needs_review": score < self.REVIEW_THRESHOLD,
            "detalhes": detalhes,
        }
