# api/services/memoria_enquadramento.py — SST ESOCIAL GOV
# Memória de enquadramento em PDF (Adendo 04, seção 6 / RF-0.183). É o documento que sustenta
# o critério adotado (DECRETO 3.048/99, art. 202, §5º: enquadramento é ato da empresa, revisável
# a qualquer tempo pela Receita Federal).
#
# CITAR SEMPRE A NORMA JUNTO DO ARTIGO. Existem dois "art. 202" no vocabulário deste projeto, e
# a IN RFB 2.321/2026 tornou a confusão provável: o art. 202 do DECRETO 3.048/99 é o nosso — a
# atividade preponderante, o enquadramento por estabelecimento e a revisão a qualquer tempo. O
# art. 202 da IN RFB 2.110/2022 (alterado pela IN 2.321/2026) trata de alíquotas sobre a receita
# da comercialização da produção rural. Mesmo número, normas e matérias diferentes.
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
    ROTULO_ORIGEM, DEFESA_ORIGEM, ORIGEM_NENHUMA,
    ORIGEM_GRAU, ORIGEM_FAP, ORIGEM_AMBAS,
)

# Rotulo curto para a coluna Origem (a tabela ja tem treze colunas).
ORIGEM_CURTO = {
    ORIGEM_NENHUMA: "—", ORIGEM_GRAU: "grau", ORIGEM_FAP: "FAP", ORIGEM_AMBAS: "ambas",
}

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


def _cnae(v) -> str:
    """CNAE no formato oficial 4712-1/00 (item 6 da revisao de 19/10). E a grafia pela qual
    contadores e fiscais reconhecem o codigo; sete digitos corridos, num laudo, sugerem
    transcricao sem cuidado."""
    if not v:
        return "—"
    d = "".join(c for c in str(v) if c.isdigit())
    return f"{d[:4]}-{d[4:5]}/{d[5:]}" if len(d) == 7 else str(v)


def _d(iso: str | None) -> str:
    """Data ISO para dia/mes/ano (item 7 da revisao: vale tambem nos documentos gerados)."""
    if not iso:
        return "—"
    s = str(iso)
    return f"{s[8:10]}/{s[5:7]}/{s[0:4]}" if len(s) >= 10 else s


def _comp(iso: str | None) -> str:
    """Competencia ISO para mes/ano."""
    if not iso:
        return "—"
    s = str(iso)
    return f"{s[5:7]}/{s[0:4]}" if len(s) >= 7 else s


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
             + (f"<b>Endereço:</b> {es.get('endereco')}<br/>" if es.get("endereco") else "")
             + f"<b>Abertura:</b> {_d(es.get('abertura'))} &nbsp;&nbsp; <b>Encerramento:</b> {_d(es.get('encerramento')) if es.get('encerramento') else 'em atividade'}<br/>"
             f"<b>Período analisado:</b> {_d(per.get('inicio'))} a {_d(per.get('fim'))}")
    el.append(_p(ident, body))

    # Atividades declaradas
    el.append(_p("Atividades declaradas (quantitativo de segurados empregados e trabalhadores avulsos)", h2))
    ativ = d.get("atividades", [])
    if ativ:
        data = [["CNAE", "Descrição", "Nº trab.", "Vigência"]]
        for a in ativ:
            vig = _d(a.get("inicio")) + (f" a {_d(a['fim'])}" if a.get("fim") else " (aberto)")
            data.append([_cnae(a.get("cnae")), (a.get("descricao") or "")[:60], str(a.get("quantitativo") if a.get("quantitativo") is not None else "—"), vig])
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
        # "RAT apl." e "FAP apl." são as DUAS origens declaradas pela empresa (S-1005 aliqRat e
        # fap). Separá-las é o que permite dizer qual delas causou a divergência — e cada uma se
        # defende de um jeito diferente.
        data = [["Comp.", "Preponderante", "Crit.", "Grau", "Devido", "FAP", "Efetivo",
                 "RAT apl.", "FAP apl.", "Aplicado", "Diverg.", "Origem", "Sit."]]
        for r in serie:
            data.append([
                _comp(r.get("competencia")), _cnae(r.get("cnae_preponderante")),
                CRIT.get(r.get("criterio"), r.get("criterio") or "—"),
                str(r.get("grau_risco") if r.get("grau_risco") is not None else "—"),
                _n(r.get("aliquota_devida"), 0, "%"),
                _n(r.get("fap"), 4),
                _n(r.get("aliquota_efetiva"), 4, "%"),
                _n(r.get("rat_aplicado"), 0, "%"),
                _n(r.get("fap_aplicado"), 4),
                _n(r.get("aliquota_aplicada"), 4, "%"),
                _pp(r.get("divergencia_pp")),
                ORIGEM_CURTO.get(r.get("origem_divergencia"), "n/d")
                + ("*" if r.get("amparada") else ""),
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
        n_conferido = sum(1 for r in serie if r.get("situacao") == "conferido")
        quem = sorted({r.get("conferido_por") for r in serie if r.get("conferido_por")})
        el.append(_p(
            "<b>Situação por competência — quem afirma o quê.</b> "
            "<i>Em conferência</i> — há pendência e o motor não concluiu (FAP do ano, CNAE fora "
            "do Anexo I, quantitativo não declarado). Nada é afirmado. "
            "<i>Apurado</i> — o motor calculou até o fim sem pendência. É <b>afirmação do "
            "sistema</b>, não validação profissional. "
            "<i>Conferido</i> — uma <b>pessoa</b> examinou e validou a competência, e o nome e a "
            "data constam abaixo. Nenhuma competência chega a este estado por cálculo.",
            small))
        el.append(_p(
            f"Neste período: <b>{n_apur} apuradas</b> pelo sistema, <b>{n_conf} em conferência</b>, "
            f"<b>{n_conferido} conferidas</b> por pessoa"
            + (f" ({'; '.join(quem)})." if quem else
               ". Nenhuma competência deste período foi validada por pessoa — o que consta aqui "
               "é apuração do sistema, e não substitui a conferência profissional."),
            small))
        revogadas = [r for r in serie if r.get("revogado_em")]
        if revogadas:
            el.append(_p(
                f"<b>{len(revogadas)} competência(s)</b> tinham sido conferidas e a validação foi "
                "revogada porque um dado de cálculo mudou depois. Conferir é assinar sobre um "
                "número determinado: se o número muda, a assinatura anterior não corresponde "
                "mais ao que está apurado.", small))
        el.append(_p(
            "A divergência é a diferença entre a alíquota aplicada e a alíquota <b>efetiva</b> "
            "(RAT × FAP), que é a base do recolhimento do GILRAT — não o RAT devido isolado.",
            small))

        # ---- Origem da divergência: a pergunta que decide a defesa ----
        # O eSocial (S-1005) valida que aliqRatAjust é o produto de aliqRat por fap. Logo o erro
        # nunca está no ajustado: está no grau ou no fator. Sem esta decomposição a memória
        # afirmaria que há divergência sem dizer o que precisa ser corrigido.
        por_origem: dict[str, list] = {}
        for r in serie:
            o = r.get("origem_divergencia")
            if o and o != ORIGEM_NENHUMA:
                por_origem.setdefault(o, []).append(_comp(r.get("competencia")))
        nao_decomposto = [r for r in serie
                          if r.get("aliquota_aplicada") is not None
                          and r.get("origem_divergencia") is None]
        amparadas = sum(1 for r in serie if r.get("amparada"))

        if por_origem or nao_decomposto:
            el.append(_p("Origem da divergência", h2))
            for o, comps in sorted(por_origem.items()):
                faixa = f"{comps[0]} a {comps[-1]}" if len(comps) > 1 else comps[0]
                # Primeira letra em maiuscula SEM mexer no resto: .capitalize() transformaria
                # "FAP" em "Fap", que num documento juridico e erro de sigla.
                rot = ROTULO_ORIGEM.get(o, o)
                rot = rot[:1].upper() + rot[1:]
                el.append(_p(
                    f"<b>{rot}</b> — {len(comps)} competência(s), {faixa}. "
                    f"{DEFESA_ORIGEM.get(o, '')}", small))
            if amparadas:
                el.append(_p(
                    f"<b>{amparadas} competência(s)</b> têm processo administrativo ou judicial "
                    "informado amparando a alíquota divergente (assinaladas com * na coluna "
                    "Origem). O leiaute do eSocial só admite alíquota diversa da prevista com "
                    "processo informado; nessas competências a divergência não constitui achado.",
                    small))
            if nao_decomposto:
                el.append(_p(
                    f"<b>{len(nao_decomposto)} competência(s)</b> têm alíquota aplicada informada "
                    "sem o desdobramento em grau e fator. Nelas a divergência é apurada, mas a "
                    "origem <b>não é afirmada</b>: o sistema não presume a decomposição. "
                    "Informe a alíquota RAT e o FAP aplicados no período para que a origem conste.",
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
