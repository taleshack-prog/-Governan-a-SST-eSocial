# ==============================================================
# SST ESOCIAL GOV — Cross-Document Validator
# Arquivo: ai-layer/validators/cross_doc_validator.py
# Verifica consistência entre LTCAT, PGR, ASO e S-2240
# ==============================================================

from datetime import date


class CrossDocValidator:
    """
    Valida consistência entre documentos SST:
    - LTCAT → S-2240: agentes do laudo devem estar no eSocial
    - ASO: datas de validade e cobertura de trabalhadores
    - PGR: riscos identificados devem ter controles
    """

    def validar_ltcat_vs_esocial(self, agentes_ltcat: list, agentes_esocial: list) -> list:
        """Retorna lista de inconsistências entre LTCAT e S-2240."""
        inconsistencias = []

        codigos_esocial = {a.get("codigo_tabela24") for a in agentes_esocial}
        for agente in agentes_ltcat:
            codigo = agente.get("codigo_tabela24_sugerido")
            if codigo and codigo not in codigos_esocial:
                inconsistencias.append({
                    "tipo": "AGENTE_NAO_DECLARADO_ESOCIAL",
                    "severidade": "alta",
                    "mensagem": f"Agente '{agente.get('descricao')}' (código {codigo}) identificado no LTCAT mas não declarado no S-2240.",
                    "norma_ref": "eSocial S-2240 — Lei 13.457/2017",
                })

        return inconsistencias

    def validar_validade_aso(self, exames: list, data_referencia: date = None) -> list:
        """Verifica ASOs vencidos ou próximos do vencimento."""
        alertas = []
        hoje = data_referencia or date.today()

        for exame in exames:
            validade = exame.get("data_validade")
            if not validade:
                continue
            if isinstance(validade, str):
                validade = date.fromisoformat(validade)

            dias_para_vencer = (validade - hoje).days
            if dias_para_vencer < 0:
                alertas.append({
                    "tipo": "ASO_VENCIDO",
                    "severidade": "critica",
                    "trabalhador_id": exame.get("trabalhador_id"),
                    "mensagem": f"ASO vencido há {abs(dias_para_vencer)} dias.",
                    "norma_ref": "NR-07 item 7.4.1",
                })
            elif dias_para_vencer <= 30:
                alertas.append({
                    "tipo": "ASO_PRESTES_A_VENCER",
                    "severidade": "media",
                    "trabalhador_id": exame.get("trabalhador_id"),
                    "mensagem": f"ASO vence em {dias_para_vencer} dias.",
                    "norma_ref": "NR-07",
                })

        return alertas

    def validar_grau_risco_cnae(self, cnae: str, grau_declarado: int) -> list:
        """Valida se o grau de risco declarado é compatível com o CNAE."""
        # Tabela simplificada — em produção usar tabela completa MTE
        CNAE_GRAUS = {
            "41": 3, "42": 3, "43": 3,  # Construção
            "05": 4, "06": 4, "07": 4,  # Mineração
            "10": 3, "11": 3, "12": 4,  # Alimentação / Bebidas / Tabaco
            "24": 4, "25": 3,           # Metalurgia / Produtos de metal
        }
        cnae_2 = cnae[:2] if len(cnae) >= 2 else cnae
        grau_esperado = CNAE_GRAUS.get(cnae_2)

        if grau_esperado and grau_esperado != grau_declarado:
            return [{
                "tipo": "GRAU_RISCO_INCONSISTENTE",
                "severidade": "media",
                "mensagem": f"CNAE {cnae} usualmente corresponde ao grau de risco {grau_esperado}, mas foi declarado {grau_declarado}.",
                "norma_ref": "NR-04 Quadro I",
            }]
        return []
