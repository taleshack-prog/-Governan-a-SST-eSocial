# api/services/relatorio_executivo.py — SST ESOCIAL GOV
# Etapa 5 (v2) / Módulo 6 — Relatório executivo mensal (PDF).
# Regra de ouro: mostra o QUE e QUANTO, nunca o fundamento jurídico.
from io import BytesIO
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER

NAVY = colors.HexColor("#1e3a5f")


def _brl(v):
    if v is None:
        return "—"
    return "R$ " + f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_relatorio_executivo(dados: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("t", parent=styles["Normal"], fontSize=15, fontName="Helvetica-Bold",
                            alignment=TA_CENTER, spaceAfter=4, textColor=NAVY)
    subt = ParagraphStyle("s", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER,
                          spaceAfter=2, textColor=colors.grey)
    secao = ParagraphStyle("sec", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold",
                           textColor=colors.white, backColor=NAVY, leftIndent=4, spaceAfter=6,
                           spaceBefore=10, borderPadding=4)
    normal = ParagraphStyle("n", parent=styles["Normal"], fontSize=9)
    obs = ParagraphStyle("o", parent=styles["Normal"], fontSize=7, fontName="Helvetica-Oblique",
                         textColor=colors.grey, alignment=TA_CENTER)
    destaque = ParagraphStyle("d", parent=styles["Normal"], fontSize=11, fontName="Helvetica-Bold",
                              textColor=NAVY)

    empresa = dados.get("empresa", {})
    blocos = dados.get("blocos", [])
    creditos = dados.get("creditos", {})
    achados = dados.get("achados", [])

    story = []
    story.append(Paragraph("RadarPrevi — Relatório Executivo de Custeio", titulo))
    story.append(Paragraph("Consultoria Previdenciária", subt))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"<b>Empresa:</b> {empresa.get('razao_social','—')} &nbsp;&nbsp; "
        f"<b>Competência:</b> {dados.get('competencia','—')} &nbsp;&nbsp; "
        f"<b>Emitido em:</b> {date.today().strftime('%d/%m/%Y')}", normal))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", color=NAVY, thickness=1))

    story.append(Paragraph("1. Diagnóstico de custeio", secao))
    linhas = [["Bloco", "Valor pago/mês", "Valor esperado/mês", "Situação"]]
    for b in blocos:
        linhas.append([b.get("bloco","—"), _brl(b.get("valor_pago_mensal")),
                       _brl(b.get("valor_esperado_mensal")), b.get("exibicao","—")])
    t1 = Table(linhas, colWidths=[4.5*cm, 4*cm, 4*cm, 5*cm])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f2f5fb")]),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(t1)

    story.append(Paragraph("2. Créditos identificados na folha", secao))
    story.append(Paragraph(f"Crédito estimado a recuperar (últimos 5 anos): {_brl(creditos.get('total_credito'))}", destaque))
    if creditos.get("total_prescreve_90dias"):
        story.append(Spacer(1, 2))
        story.append(Paragraph(
            f"<b>Atenção:</b> {_brl(creditos.get('total_prescreve_90dias'))} prescrevem nos próximos 90 dias "
            f"(art. 168 do CTN — recuperação quinquenal).", normal))

    story.append(Paragraph("3. Ordens de serviço", secao))
    if achados:
        linhas2 = [["Achado", "Tipo", "Esfera", "Prazo", "Valor"]]
        TIPO_LBL = {"credito": "Crédito", "passivo": "Passivo", "alerta": "Alerta"}
        for a in achados:
            linhas2.append([
                Paragraph(a.get("descricao","—"), ParagraphStyle("c", parent=normal, fontSize=7)),
                TIPO_LBL.get(a.get("tipo"), a.get("tipo","—")),
                (a.get("esfera") or "—").capitalize(),
                (str(a.get("prazo_dias")) + "d") if a.get("prazo_dias") else "—",
                _brl(a.get("valor_retroativo")) if a.get("tipo") == "credito" else "—",
            ])
        t2 = Table(linhas2, colWidths=[7*cm, 2*cm, 2.5*cm, 1.5*cm, 3.5*cm])
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 7),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f2f5fb")]),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(t2)
    else:
        story.append(Paragraph("Nenhuma ordem de serviço no período.", normal))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", color=colors.grey, thickness=0.5))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Valores estimados com base na parametrização informada, confirmados na análise jurídica. "
        "Documento gerado automaticamente pela plataforma RadarPrevi.", obs))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
