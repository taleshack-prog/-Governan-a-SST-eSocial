# api/services/memoria_enquadramento.py — SST ESOCIAL GOV
# Memória de enquadramento em PDF (Adendo 04, seção 6 / RF-0.183). É o documento que sustenta
# o critério adotado (art. 202, §5º: enquadramento é ato da empresa, revisável a qualquer tempo).
# Fonte do quantitativo = declaração da empresa; fonte do grau = anexo oficial. NÃO cita serviço
# de consulta de CNPJ. Itens [A CONFIRMAR] (portaria do FAP, incisos) ficam marcados, nunca inventados.
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

from api.services.enquadramento_situacao import (
    ROTULO, SITUACAO_CONFERENCIA, SITUACAO_APURADO,
)

GRAU_LABEL = {1: "leve (1%)", 2: "médio (2%)", 3: "grave (3%)"}
CRIT = {"maior_quantitativo": "maior quantitativo", "desempate_grau": "empate → maior grau", "fila_conferencia": "conferência"}


# Item 2 da revisao: virgula como separador decimal, ponto reservado para milhar. Este
# documento vai para cliente e eventualmente para fiscal; ponto decimal, lido por um contador
# brasileiro, parece defeito de sistema.
def _n(v, casas: int = 2, sufixo: str = "") -> str:
    if v is None:
        return "—"
    inteiro = f"{float(v):,.{casas}f}"
    # troca simultanea: milhar '.' e decimal ','
    return inteiro.replace(",", "\x00").replace(".", ",").replace("\x00", ".") + sufixo


def _pp(v) -> str:
    """Pontos percentuais com sinal. Menos tipografico, para nao ser lido como traco."""
    if v is None:
        return "—"
    sinal = "+" if v > 0 else ("−" if v < 0 else "")
    return f"{sinal}{_n(abs(float(v)), 2)}"


def _p(txt, style):
    return Paragraph(txt, style)


def gerar_memoria_pdf(d: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.4 * cm, bottomMargin=1.4 * cm,
                            leftMargin=1.6 * cm, rightMargin=1.6 * cm)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=15, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=ss["Normal"], fontSize=8.5, textColor=colors.HexColor("#6b7280"))
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#0f766e"))
    body = ParagraphStyle("body", parent=ss["Normal"], fontSize=9, leading=13)
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=7.5, leading=10, textColor=colors.HexColor("#6b7280"))
    el = []

    el.append(_p("Memória de Enquadramento", h1))
    el.append(_p("Atividade preponderante, grau de risco e RAT devido — Decreto 3.048/99, art. 202, §§ 3º e 5º", sub))
    el.append(Spacer(1, 6))
    el.append(HRFlowable(width="100%", color=colors.HexColor("#e5e7eb")))

    emp = d.get("empresa", {})
    es = d.get("estab", {})
    per = d.get("periodo", {})
    el.append(_p("Identificação", h2))
    ident = (f"<b>Empresa:</b> {emp.get('razao_social') or '—'} — CNPJ raiz {emp.get('cnpj') or '—'}<br/>"
             f"<b>Estabelecimento:</b> {es.get('codigo') or ''} {es.get('nome') or ''} "
             f"({es.get('posicao') or '—'}, natureza {es.get('tipo') or '—'})<br/>"
             f"<b>Matrícula:</b> {es.get('identificador') or es.get('cnpj') or '—'}<br/>"
             f"<b>Abertura:</b> {es.get('abertura') or '—'} &nbsp;&nbsp; <b>Encerramento:</b> {es.get('encerramento') or 'em atividade'}<br/>"
             f"<b>Período analisado:</b> {per.get('inicio') or '—'} a {per.get('fim') or '—'}")
    el.append(_p(ident, body))

    # Atividades declaradas
    el.append(_p("Atividades declaradas (quantitativo de segurados empregados e trabalhadores avulsos)", h2))
    ativ = d.get("atividades", [])
    if ativ:
        data = [["CNAE", "Descrição", "Nº trab.", "Vigência"]]
        for a in ativ:
            vig = f"{a.get('inicio') or ''}" + (f" a {a['fim']}" if a.get("fim") else " (aberto)")
            data.append([a.get("cnae") or "", (a.get("descricao") or "")[:60], str(a.get("quantitativo") if a.get("quantitativo") is not None else "—"), vig])
        t = Table(data, colWidths=[2.2 * cm, 8.2 * cm, 1.8 * cm, 4.5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
            ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        el.append(t)
    else:
        el.append(_p("Nenhuma atividade declarada.", small))
    el.append(_p("Não contam: contribuintes individuais (sócios/diretores sem vínculo, autônomos), estagiários e terceirizados (Decreto 3.048/99, art. 202, §3º; CLT art. 428; Lei 11.788/2008).", small))

    # Série apurada
    el.append(_p("Enquadramento apurado por competência", h2))
    serie = d.get("serie", [])
    if serie:
        data = [["Comp.", "Preponderante", "Critério", "Grau", "Devido", "FAP", "Efetivo", "Aplicado", "Diverg.", "Sit."]]
        for r in serie:
            data.append([
                (r.get("competencia") or "")[:7], r.get("cnae_preponderante") or "—",
                CRIT.get(r.get("criterio"), r.get("criterio") or "—"),
                str(r.get("grau_risco") if r.get("grau_risco") is not None else "—"),
                _n(r.get("aliquota_devida"), 0, "%"),
                _n(r.get("fap"), 4),
                _n(r.get("aliquota_efetiva"), 4, "%"),
                _n(r.get("aliquota_aplicada"), 2, "%"),
                _pp(r.get("divergencia_pp")),
                ROTULO.get(r.get("situacao"), "—"),
            ])
        t = Table(data, repeatRows=1)
        style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                 ("FONTSIZE", (0, 0), (-1, -1), 7), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb"))]
        for i, r in enumerate(serie, start=1):
            # Âmbar = falta dado para apurar. Cinza = apurado, mas o aplicado não foi informado,
            # então nada foi comparado. Sem cor = conferido. Nenhuma competência sai como "ok"
            # sem que alguém tenha confrontado devido e aplicado.
            sit = r.get("situacao")
            if sit == SITUACAO_CONFERENCIA:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fef3c7")))
            elif sit == SITUACAO_APURADO:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f3f4f6")))
        t.setStyle(TableStyle(style))
        el.append(t)
        n_conf = sum(1 for r in serie if r.get("situacao") == SITUACAO_CONFERENCIA)
        n_apur = sum(1 for r in serie if r.get("situacao") == SITUACAO_APURADO)
        el.append(Spacer(1, 0.2 * cm))
        el.append(_p(
            "<b>Situação por competência.</b> "
            "<i>conferência</i> — falta dado para apurar o devido (FAP do ano, CNAE fora do "
            "Anexo I, quantitativo não declarado); nada é afirmado. "
            "<i>apurado</i> — o devido está calculado, mas a alíquota efetivamente aplicada pela "
            "empresa não foi informada; não houve comparação. "
            "<i>conferido</i> — devido e aplicado foram confrontados e a divergência consta na "
            "coluna anterior. "
            f"Neste período: {n_conf} em conferência, {n_apur} apuradas sem o aplicado informado.",
            small))
        el.append(_p(
            "A divergência é a diferença entre a alíquota aplicada e a alíquota <b>efetiva</b> "
            "(RAT × FAP), que é a base do recolhimento do GILRAT — não o RAT devido isolado.",
            small))
    else:
        el.append(_p("Nenhuma competência apurada no período.", small))

    # Fundamentação + autoria
    f = d.get("fundamentacao", {})
    el.append(_p("Fundamentação normativa", h2))
    el.append(_p(f"{f.get('dispositivo') or ''}.<br/>{f.get('ato') or ''}.<br/>Grau de risco: {f.get('anexo') or ''} — {f.get('vigencia') or ''}.", body))
    el.append(_p("Desempate pelo maior grau de risco: IN RFB 2.110/2022, art. 43, §1º — <i>inciso a confirmar (B.1)</i>. "
                 "Portaria interministerial do FAP de cada ano: <i>a confirmar (B.4)</i>. "
                 "Soluções de Consulta Cosit sobre atividade preponderante × principal: <i>a confirmar (B.2/B.3)</i>.", small))
    # CPRB — estado explícito da verificação (RF-0.163). O bloco nunca fica ambíguo: ou foi
    # verificado (optante/não optante, com autor e data), ou consta pendente de conferência.
    cprb = d.get("cprb") or {}
    st = cprb.get("status") or "nao_informado"
    el.append(_p("Contribuição previdenciária sobre a receita bruta (CPRB)", h2))
    if st == "optante":
        pers = cprb.get("periodos") or []
        linhas = "; ".join(f"{(p.get('inicio') or '')[:7]} a {(p.get('fim') or '')[:7] or 'vigente'}" for p in pers) or "sem períodos informados"
        verif = f" Verificado por {cprb['verificado_por']}" + (f" em {cprb['verificado_em']}" if cprb.get("verificado_em") else "") + "." if cprb.get("verificado_por") else ""
        el.append(_p(f"<b>Optante</b> pela desoneração da folha nos períodos: {linhas}. "
                     f"A partir de 01/2025 a CPRB coexiste com a cota patronal parcial (Lei 14.973/2024); "
                     f"RAT e Terceiros permanecem devidos.{verif}", body))
    elif st == "nao_optante":
        verif = f"Verificado por {cprb['verificado_por']}" + (f" em {cprb['verificado_em']}" if cprb.get("verificado_em") else "") + "." if cprb.get("verificado_por") else "Marcação explícita."
        el.append(_p(f"<b>Não optante</b> pela CPRB. {verif} O cálculo da contribuição patronal "
                     f"roda com a alíquota integral sobre a folha.", body))
    else:
        el.append(_p("<b>Não verificada.</b> Não há confirmação de opção ou não opção pela CPRB — "
                     "item pendente de conferência. Enquanto não verificada, não é afirmada "
                     "desoneração da folha.", body))

    aut = d.get("autoria") or []
    if aut:
        el.append(_p("Declaração dos quantitativos: " + "; ".join(aut) + ".", small))
    el.append(Spacer(1, 6))
    el.append(_p(f"Documento gerado em {d.get('gerado_em') or ''}. A fonte do quantitativo é a declaração da empresa; a fonte do grau é o anexo oficial.", small))

    doc.build(el)
    return buf.getvalue()
