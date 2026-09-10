# api/services/dossie_prova.py — SST ESOCIAL GOV
# Etapa 5 (v2) / Módulo 6 — Dossiê de prova por achado (PDF).
# v2 linha 191: fundamento só no perfil da advogada. incluir_fundamento=True só p/ advogada/admin.
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


def gerar_dossie_prova(dados: dict, incluir_fundamento: bool = False) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("t", parent=styles["Normal"], fontSize=14, fontName="Helvetica-Bold",
                            alignment=TA_CENTER, spaceAfter=4, textColor=NAVY)
    subt = ParagraphStyle("s", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER,
                          spaceAfter=2, textColor=colors.grey)
    secao = ParagraphStyle("sec", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold",
                           textColor=colors.white, backColor=NAVY, leftIndent=4, spaceAfter=6,
                           spaceBefore=10, borderPadding=4)
    normal = ParagraphStyle("n", parent=styles["Normal"], fontSize=9)
    obs = ParagraphStyle("o", parent=styles["Normal"], fontSize=7, fontName="Helvetica-Oblique",
                         textColor=colors.grey, alignment=TA_CENTER)

    achado = dados.get("achado", {})
    empresa = dados.get("empresa", {})
    estab = dados.get("estabelecimento", {})
    memoria = dados.get("memoria", [])
    fundamento = dados.get("fundamento")

    story = []
    story.append(Paragraph("Dossiê de Prova — Divergência de Custeio", titulo))
    story.append(Paragraph("RadarPrevi · Consultoria Previdenciária", subt))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"<b>Empresa:</b> {empresa.get('razao_social','—')} &nbsp;&nbsp; "
        f"<b>Estabelecimento:</b> {estab.get('nome','—')} ({estab.get('codigo','—')}) &nbsp;&nbsp; "
        f"<b>Emitido em:</b> {date.today().strftime('%d/%m/%Y')}", normal))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", color=NAVY, thickness=1))

    story.append(Paragraph("1. Identificação do achado", secao))
    ident = [
        ["Descrição", achado.get("descricao", "—")],
        ["Grau de segurança", (achado.get("grau_seguranca") or "—").capitalize()],
        ["Esfera", (achado.get("esfera") or "—").capitalize()],
        ["Natureza", "Recuperação (crédito)" if achado.get("tipo_valor") == "recuperacao" else achado.get("tipo", "—")],
    ]
    ti = Table(ident, colWidths=[5*cm, 12.5*cm])
    ti.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 8), ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#f2f5fb")),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(ti)

    story.append(Paragraph("2. Valores apurados", secao))
    vals = [
        ["Valor mensal indevido", _brl(achado.get("valor_mensal"))],
        ["Alíquota efetiva aplicada", f"{float(achado.get('aliquota_aplicada') or 0) * 100:.2f}%"],
        ["Valor recuperável (5 anos)", _brl(achado.get("valor_retroativo"))],
        ["Prescreve nos próximos 90 dias", _brl(dados.get("prescreve_90dias"))],
        ["Data-limite de prescrição", dados.get("data_prescricao", "—")],
    ]
    tv = Table(vals, colWidths=[7*cm, 10.5*cm])
    tv.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 8), ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#f2f5fb")),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(tv)

    story.append(Paragraph("3. Memória de cálculo por competência", secao))
    story.append(Paragraph(
        "Composição do valor recuperável competência a competência (art. 168 do CTN). "
        "Base de prova para pedido administrativo de restituição/compensação.", normal))
    story.append(Spacer(1, 4))
    if memoria:
        comps = sorted(m["competencia"] for m in memoria)
        valor_comp = memoria[0]["valor_competencia"] if memoria else 0
        total = sum(m["valor_competencia"] for m in memoria)
        linhas = [["Competência mais antiga", "Competência mais recente", "Competências", "Valor por competência", "Total"]]
        linhas.append([comps[0] if comps else "—", comps[-1] if comps else "—", str(len(memoria)),
                       _brl(valor_comp), _brl(total)])
        tm = Table(linhas, colWidths=[3.6*cm, 3.6*cm, 2.3*cm, 4*cm, 4*cm])
        tm.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 7),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(tm)
        story.append(Spacer(1, 2))
        story.append(Paragraph(f"Memória detalhada: {len(memoria)} competências registradas e auditáveis no sistema.", obs))
    else:
        story.append(Paragraph("Memória de cálculo não disponível — execute o recálculo mensal.", normal))

    if incluir_fundamento and fundamento:
        story.append(Paragraph("4. Fundamento normativo (uso interno — perfil jurídico)", secao))
        story.append(Paragraph(fundamento, normal))
        story.append(Spacer(1, 2))
        story.append(Paragraph(
            "Seção restrita ao perfil jurídico. Não deve ser compartilhada na versão do cliente.", obs))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", color=colors.grey, thickness=0.5))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Documento gerado pela plataforma RadarPrevi. Valores estimados, sujeitos a confirmação na análise jurídica.", obs))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
