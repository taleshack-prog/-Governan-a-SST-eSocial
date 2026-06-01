# ==============================================================
# SST ESOCIAL GOV — Serviço: Geração de PDF do PPP
# Arquivo: api/services/ppp_pdf.py
# ==============================================================

from io import BytesIO
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def gerar_ppp_pdf(ppp: dict) -> bytes:
    """Gera o PDF do PPP conforme modelo INSS."""
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()

    # Estilos customizados
    titulo_style = ParagraphStyle(
        "titulo", parent=styles["Normal"],
        fontSize=14, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=4,
    )
    subtitulo_style = ParagraphStyle(
        "subtitulo", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica",
        alignment=TA_CENTER, spaceAfter=2, textColor=colors.grey,
    )
    secao_style = ParagraphStyle(
        "secao", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica-Bold",
        textColor=colors.white, spaceAfter=4,
        backColor=colors.HexColor("#1e3a5f"),
        leftIndent=4, rightIndent=4,
    )
    label_style = ParagraphStyle(
        "label", parent=styles["Normal"],
        fontSize=7, fontName="Helvetica",
        textColor=colors.grey,
    )
    valor_style = ParagraphStyle(
        "valor", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica-Bold",
        textColor=colors.black,
    )
    obs_style = ParagraphStyle(
        "obs", parent=styles["Normal"],
        fontSize=7, fontName="Helvetica-Oblique",
        textColor=colors.grey, alignment=TA_CENTER,
    )

    story = []
    empresa = ppp.get("empresa", {})
    trabalhador = ppp.get("trabalhador", {})
    agentes = ppp.get("agentes_nocivos", [])
    ltcat = ppp.get("ltcat", {})
    resp = ppp.get("responsavel_tecnico", {})
    completude = ppp.get("completude", {})

    # ── CABEÇALHO ──────────────────────────────────────────────
    story.append(Paragraph("PERFIL PROFISSIOGRÁFICO PREVIDENCIÁRIO — PPP", titulo_style))
    story.append(Paragraph("Lei 8.213/1991 art. 58 | Decreto 3.048/1999 art. 68 | IN INSS 128/2022", subtitulo_style))
    story.append(Paragraph(f"Completude: {completude.get('percentual', 0)}% — Gerado em {date.today().strftime('%d/%m/%Y')}", subtitulo_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e3a5f"), spaceAfter=8))

    # ── SEÇÃO I — EMPRESA ──────────────────────────────────────
    story.append(Paragraph("  I — DADOS DA EMPRESA", secao_style))
    story.append(Spacer(1, 4))

    dados_empresa = [
        [
            Paragraph("Razão Social", label_style),
            Paragraph("CNPJ", label_style),
            Paragraph("CNAE", label_style),
            Paragraph("Grau de Risco", label_style),
        ],
        [
            Paragraph(empresa.get("razao_social", "—"), valor_style),
            Paragraph(empresa.get("cnpj", "—"), valor_style),
            Paragraph(empresa.get("cnae", "—"), valor_style),
            Paragraph(str(empresa.get("grau_risco", "—")), valor_style),
        ],
    ]
    t_empresa = Table(dados_empresa, colWidths=[7*cm, 4*cm, 3*cm, 3*cm])
    t_empresa.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4f8")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_empresa)
    story.append(Spacer(1, 8))

    # ── SEÇÃO II — TRABALHADOR ─────────────────────────────────
    story.append(Paragraph("  II — DADOS DO TRABALHADOR", secao_style))
    story.append(Spacer(1, 4))

    dados_trab = [
        [
            Paragraph("Nome Completo", label_style),
            Paragraph("CPF", label_style),
            Paragraph("Sexo", label_style),
        ],
        [
            Paragraph(trabalhador.get("nome", "—"), valor_style),
            Paragraph(trabalhador.get("cpf", "—"), valor_style),
            Paragraph("Masculino" if trabalhador.get("sexo") == "M" else "Feminino" if trabalhador.get("sexo") == "F" else "—", valor_style),
        ],
        [
            Paragraph("Cargo", label_style),
            Paragraph("Setor/GES", label_style),
            Paragraph("Data Admissão", label_style),
        ],
        [
            Paragraph(trabalhador.get("cargo", "Não informado"), valor_style),
            Paragraph(trabalhador.get("setor", "Não informado"), valor_style),
            Paragraph(trabalhador.get("data_admissao", "—"), valor_style),
        ],
    ]
    t_trab = Table(dados_trab, colWidths=[7*cm, 7*cm, 3*cm])
    t_trab.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4f8")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f0f4f8")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_trab)
    story.append(Spacer(1, 8))

    # ── SEÇÃO III — AGENTES NOCIVOS ────────────────────────────
    story.append(Paragraph(f"  III — REGISTROS AMBIENTAIS ({len(agentes)} agente(s) nocivo(s))", secao_style))
    story.append(Spacer(1, 4))

    if not agentes:
        story.append(Paragraph("Nenhum agente nocivo cadastrado.", valor_style))
    else:
        header_agentes = [
            Paragraph("Código Tab.24", label_style),
            Paragraph("Descrição", label_style),
            Paragraph("Nível/Dose", label_style),
            Paragraph("Técnica", label_style),
            Paragraph("EPI Eficaz", label_style),
            Paragraph("At. Especial", label_style),
        ]
        rows_agentes = [header_agentes]
        for a in agentes:
            rows_agentes.append([
                Paragraph(a.get("codigo_tabela24", "—"), valor_style),
                Paragraph(a.get("descricao", "—")[:50], valor_style),
                Paragraph(str(a.get("nivel_exposicao", "Qualit.")), valor_style),
                Paragraph(a.get("tecnica_avaliacao", "—"), valor_style),
                Paragraph("Sim" if a.get("epi_eficaz") else "Não", valor_style),
                Paragraph("Sim" if a.get("enquadramento_especial") else "Não", valor_style),
            ])

        t_agentes = Table(rows_agentes, colWidths=[2.5*cm, 6*cm, 2.5*cm, 2.5*cm, 1.8*cm, 1.7*cm])
        t_agentes.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4f8")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
        ]))
        story.append(t_agentes)
    story.append(Spacer(1, 8))

    # ── SEÇÃO IV — LTCAT ───────────────────────────────────────
    story.append(Paragraph("  IV — LTCAT DE REFERÊNCIA", secao_style))
    story.append(Spacer(1, 4))

    dados_ltcat = [
        [Paragraph("Título do LTCAT", label_style), Paragraph("Data de Emissão", label_style), Paragraph("Responsável", label_style)],
        [
            Paragraph(ltcat.get("titulo", "Não informado"), valor_style),
            Paragraph(ltcat.get("data_emissao", "—"), valor_style),
            Paragraph(ltcat.get("responsavel", "—"), valor_style),
        ],
    ]
    t_ltcat = Table(dados_ltcat, colWidths=[9*cm, 3*cm, 5*cm])
    t_ltcat.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4f8")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_ltcat)
    story.append(Spacer(1, 8))

    # ── SEÇÃO V — RESPONSÁVEL TÉCNICO ─────────────────────────
    story.append(Paragraph("  V — RESPONSÁVEL TÉCNICO", secao_style))
    story.append(Spacer(1, 4))

    dados_resp = [
        [Paragraph("Nome", label_style), Paragraph("Registro", label_style), Paragraph("Função", label_style), Paragraph("Conselho", label_style)],
        [
            Paragraph(resp.get("nome", "Não informado"), valor_style),
            Paragraph(resp.get("registro", "—"), valor_style),
            Paragraph(resp.get("funcao", "—"), valor_style),
            Paragraph(resp.get("conselho", "—"), valor_style),
        ],
    ]
    t_resp = Table(dados_resp, colWidths=[6*cm, 3*cm, 5*cm, 3*cm])
    t_resp.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4f8")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_resp)
    story.append(Spacer(1, 12))

    # ── ASSINATURA ─────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=8))

    assinatura_data = [
        [
            Paragraph("_______________________________\nAssinatura do Responsável Técnico", obs_style),
            Paragraph("_______________________________\nAssinatura do Representante Legal", obs_style),
            Paragraph(f"_______________________________\nData: {date.today().strftime('%d/%m/%Y')}", obs_style),
        ]
    ]
    t_ass = Table(assinatura_data, colWidths=[6*cm, 6*cm, 5*cm])
    t_ass.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("PADDING", (0, 0), (-1, -1), 5)]))
    story.append(t_ass)
    story.append(Spacer(1, 8))

    # ── RODAPÉ ─────────────────────────────────────────────────
    story.append(Paragraph(
        "Documento gerado pelo sistema SST eSocial Gov | Base legal: Lei 8.213/1991 | IN INSS 128/2022 | "
        f"Emitido em {date.today().strftime('%d/%m/%Y')}",
        obs_style
    ))

    doc.build(story)
    return buffer.getvalue()
