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
from api.services.fundamentacao import TEXTO_CRITERIO_VIGENCIA

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


def _so_digitos(v) -> str:
    """Compara numeros, nao a grafia deles: '90.244.278/0001-05' e '90244278000105' sao o mesmo."""
    return "".join(c for c in str(v or "") if c.isdigit())


def _cnpj(v) -> str:
    """CNPJ no formato oficial 90.244.278/0001-05 (Carolina, 25/10, item 3).

    Pelo mesmo motivo do CNAE: e a grafia pela qual contador e fiscal reconhecem o numero, e
    catorze digitos corridos num laudo sugerem transcricao sem cuidado. Devolve o que recebeu
    quando nao tem catorze digitos — numero incompleto nao se maquia de completo.
    """
    if not v:
        return "—"
    d = "".join(c for c in str(v) if c.isdigit())
    if len(d) != 14:
        return str(v)
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


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


def _esc(v) -> str:
    """Escapa texto que veio do BANCO antes de entrar num Paragraph.

    O reportlab interpreta o conteudo do Paragraph como marcacao: um '&' ou um '<' solto num
    texto cadastrado pelo usuario levanta excecao e o PDF nao sai. A citacao normativa agora vem
    da tabela versionada, digitada por pessoa — "art. 22 & 23", "<ate 2022>" sao plausiveis. Nos
    textos que o proprio codigo escreve, as tags <b> continuam valendo; so o que vem de fora
    passa por aqui.
    """
    return (str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if v is not None else "")


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
    # O SUBTITULO NAO CITA NORMA. Citava "art. 202, §§ 3º e 5º", literal cravado aqui, enquanto a
    # tabela versionada diz "§§ 3º e 4º" — e a tabela esta certa: o § 3º define a preponderante e
    # o § 4º remete ao Anexo V, de onde sai o grau; o § 5º trata de QUEM faz o enquadramento, que
    # nao e nenhuma das tres coisas anunciadas nesta linha. O mesmo PDF citava dois dispositivos
    # diferentes para a mesma afirmacao, porque um vinha da tabela e o outro do codigo.
    #
    # A citacao sai inteira no bloco "Fundamentacao normativa", resolvida pela data de cada
    # competencia e com a vigencia declarada. Duplica-la aqui so cria uma segunda fonte para
    # divergir — exatamente o que a decisao da Carolina de 21/10 eliminou.
    el.append(_p("Atividade preponderante, grau de risco e RAT devido", sub))
    el.append(Spacer(1, 6))
    el.append(HRFlowable(width="100%", color=colors.HexColor("#e5e7eb")))

    emp = d.get("empresa", {})
    es = d.get("estab", {})
    per = d.get("periodo", {})
    el.append(_p("Identificação", h2))
    # "CNPJ da matriz", nao "raiz" (revisao da Carolina, 23/10): raiz sao os oito primeiros
    # digitos, e o que se mostra aqui e o CNPJ completo do estabelecimento matriz. A tela de
    # cadastro ja foi corrigida; a memoria e o documento que sai assinado e ficou para tras.
    # O CNPJ E A MATRICULA ESTAVAM TROCADOS (Carolina, 25/10, item 3). Saía "CNPJ da matriz
    # 90244278" — oito dígitos, que são a RAIZ — e "Matrícula: 90244278000105", que é o CNPJ
    # completo. Dois números rotulados um pelo nome do outro, e nenhum formatado.
    #
    # Matrícula é CEI/CNO: identifica OBRA, não estabelecimento com CNPJ próprio. A linha só
    # aparece quando existe, e quando o estabelecimento tem CNPJ é isso que se diz.
    _mat = es.get("identificador")
    ident = (f"<b>Empresa:</b> {emp.get('razao_social') or '—'} — CNPJ da matriz: {_cnpj(emp.get('cnpj'))}<br/>"
             f"<b>Estabelecimento:</b> {es.get('codigo') or ''} {es.get('nome') or ''} "
             f"({es.get('posicao') or '—'}, natureza {es.get('tipo') or '—'})<br/>"
             # O CNPJ do estabelecimento so aparece quando DIFERE do da matriz — numa filial ele
             # informa; na propria matriz seria o mesmo numero impresso duas vezes seguidas.
             + (f"<b>Matrícula CNO/CAEPF:</b> {_esc(_mat)}<br/>" if _mat
                else (f"<b>CNPJ do estabelecimento:</b> {_cnpj(es.get('cnpj'))}<br/>"
                      if es.get("cnpj") and _so_digitos(es.get("cnpj")) != _so_digitos(emp.get("cnpj"))
                      else ""))
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
    # O APRENDIZ CONTA (Carolina, 24/10). A nota o trazia implicitamente entre as exclusoes, ao
    # citar a CLT art. 428 na lista do que nao conta. Aprendiz e segurado empregado, com carteira
    # assinada, e entra no quantitativo que decide a preponderante — contá-lo de fora mudaria o
    # grau de risco apurado. O estagiario continua fora, e ai a Lei 11.788/2008 esta bem citada,
    # porque o estagio nao gera vinculo.
    #
    # A citacao continua cravada aqui, e isso e divida conhecida: deveria vir da tabela
    # versionada, com vigencia, como as demais. Esta na fila com a Carolina.
    el.append(_p("Contam: segurados empregados (inclusive o aprendiz) e trabalhadores avulsos. "
                 "Não contam: contribuintes individuais (sócios/diretores sem vínculo, autônomos), "
                 "estagiários e terceirizados (Decreto 3.048/99, art. 202, §3º; Lei 11.788/2008).", small))

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

        # ---- O SALDO DA JANELA (Carolina, 25/10, item 1) ----
        #
        # O documento listava as sessenta linhas e em nenhum ponto dizia que a janela tem crédito
        # E débito ao mesmo tempo. Quem lê precisava somar linha por linha para descobrir — e o
        # sinal se inverte duas vezes ao longo do período, porque o FAP publicado muda todo ano e
        # a empresa aplicou 1,0000 em todos eles.
        #
        # Isto NÃO conclui qual dos dois pesa mais em dinheiro, e a frase final diz por quê: a
        # divergência é em pontos percentuais e o valor depende da folha de cada competência, que
        # o sistema não tem. Dizer "há valor a recuperar" a partir de pontos percentuais seria o
        # mesmo erro que saiu do quadro de divergência hoje de manhã, em escala maior.
        def _onde(rs):
            """Lista as competências quando são poucas; os anos quando são muitas."""
            comps = sorted(_comp(r.get("competencia")) for r in rs)
            if len(comps) <= 3:
                return ", ".join(comps)
            anos = sorted({c[3:] for c in comps})
            return ", ".join(anos)

        _cred = [r for r in serie if (r.get("divergencia_pp") or 0) > 0]
        _deb = [r for r in serie if (r.get("divergencia_pp") or 0) < 0]
        _zero = [r for r in serie if r.get("divergencia_pp") == 0]
        _sem = [r for r in serie if r.get("divergencia_pp") is None]
        _partes = []
        if _cred:
            _partes.append(f"<b>{len(_cred)} com crédito</b> ({_onde(_cred)})")
        if _deb:
            _partes.append(f"<b>{len(_deb)} com débito</b> ({_onde(_deb)})")
        if _zero:
            _partes.append(f"{len(_zero)} sem divergência ({_onde(_zero)})")
        if _sem:
            _partes.append(f"{len(_sem)} não apurada(s) ({_onde(_sem)})")
        el.append(Spacer(1, 0.2 * cm))
        el.append(_p("<b>Na janela:</b> " + "; ".join(_partes) + ".", body))
        if _cred and _deb:
            el.append(_p(
                "O sinal da divergência <b>se inverte</b> ao longo do período analisado: há "
                "competências em que a empresa recolheu acima do devido e competências em que "
                "recolheu abaixo. Os dois grupos não se compensam automaticamente, e qual deles "
                "pesa mais <b>em valor</b> não decorre desta tabela: a divergência aqui é em "
                "pontos percentuais, e o valor de cada competência depende da folha de pagamento "
                "do mês, que não integra esta apuração.", small))
        elif _cred or _deb:
            el.append(_p(
                "A divergência é expressa em pontos percentuais. O valor em reais de cada "
                "competência depende da folha de pagamento do mês, que não integra esta apuração.",
                small))

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
        # DUAS AUSÊNCIAS DIFERENTES, antes somadas na mesma frase (Carolina, 25/10, item 6).
        #
        # O texto dizia que as competências "têm alíquota aplicada informada sem o desdobramento
        # em grau e fator" e que "nelas a divergência é apurada". As duas afirmações eram falsas
        # para o caso real: 11 e 12/2021 TÊM o desdobramento — RAT 3% e FAP 1,0000 — e o que
        # falta é o FAP PUBLICADO, do lado devido. Sem alíquota devida não há divergência a
        # apurar, e a tabela mostrava "—" na coluna enquanto o parágrafo dizia o contrário.
        #
        # A origem fica indeterminada nos dois casos, mas por motivos opostos: num falta o que a
        # empresa aplicou, no outro falta o que a lei devia. A ação para resolver também é outra.
        sem_devido = [r for r in serie if r.get("fap") is None and r.get("rat_aplicavel") is not False]
        sem_desdobramento = [r for r in serie
                             if r.get("aliquota_aplicada") is not None
                             and r.get("fap") is not None
                             and (r.get("rat_aplicado") is None or r.get("fap_aplicado") is None)]
        amparadas = sum(1 for r in serie if r.get("amparada"))

        if por_origem or sem_devido or sem_desdobramento:
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
            if sem_devido:
                _q = len(sem_devido)
                el.append(_p(
                    f"<b>{_q} competência{'s' if _q > 1 else ''} sem FAP publicado no ano</b> "
                    f"({_onde(sem_devido)}). Sem o fator não há alíquota efetiva devida, e sem ela "
                    "<b>não há divergência a apurar</b> — não se trata de divergência cuja origem "
                    "seja desconhecida. Informe o FAP publicado do exercício para que "
                    f"{'essas competências sejam apuradas' if _q > 1 else 'essa competência seja apurada'}.",
                    small))
            if sem_desdobramento:
                _q = len(sem_desdobramento)
                el.append(_p(
                    f"<b>{_q} competência{'s' if _q > 1 else ''}</b> têm alíquota aplicada "
                    "informada sem o desdobramento em RAT base e FAP. Nelas a comparação não "
                    "fecha: o mesmo percentual admite leitura como alíquota base ou como efetiva, "
                    "com resultados opostos, e o sistema <b>não escolhe entre as duas</b>. Informe "
                    "a alíquota RAT e o FAP aplicados no período.", small))
    else:
        el.append(_p("Nenhuma competência apurada no período.", small))

    # Fundamentação + autoria
    #
    # A CITACAO NAO E ESCRITA AQUI, e nao e mais uma so. Vem da tabela versionada, resolvida pela
    # DATA DE CADA COMPETENCIA, em blocos de redacao igual: se a norma mudou no meio do periodo
    # analisado, o documento mostra as duas redacoes e o intervalo de competencias que cada uma
    # governa. Antes imprimia um unico texto, copiado da primeira linha apurada, para a serie
    # inteira — afirmacao sobre meses que aquela redacao nao alcancava.
    #
    # Lista vazia nao chega aqui: a emissao e recusada antes, no router, quando falta citacao em
    # qualquer competencia. Nao ha texto de reserva em nenhum ponto deste caminho.
    el.append(_p("Fundamentação normativa", h2))

    def _imprime_blocos(blocos, titulo: str):
        """Um campo fundamentado, com seus blocos de vigência."""
        if not blocos:
            return
        el.append(_p(f"<b>{titulo}</b>", body))
        _varias = len(blocos) > 1
        for b in blocos:
            if _varias:
                faixa = _comp(b.get("de")) + (f" a {_comp(b.get('ate'))}" if b.get("ate") != b.get("de") else "")
                el.append(_p(f"Competências {faixa}", small))
            # Linha a linha, omitindo o que nao existe. A versao anterior interpolava vazio e
            # imprimia pontuacao orfa — ".<br/>.<br/>Grau de risco:  — ." —, que e a mesma classe
            # de defeito: valor ausente virando texto no documento. O que nao existe nao se escreve.
            _linhas = [x for x in [
                _esc(b.get("dispositivo")) or None,
                _esc(b.get("ato")) or None,
                (f"Grau de risco: {_esc(b['anexo'])}" if b.get("anexo") else None),
            ] if x]
            if _linhas:
                el.append(_p(".<br/>".join(_linhas) + ".", body))
            if b.get("observacao"):
                el.append(_p(_esc(b["observacao"]), small))
            # A vigencia da REDACAO citada, e o rotulo diz que e isso. No lugar dela vinha impressa
            # a versao das tabelas de calculo da apuracao, rotulada como se fosse vigencia de norma.
            _vig = ("Redação vigente desde " + _d(b.get("vigencia_inicio"))
                    + (f" até {_d(b['vigencia_fim'])}." if b.get("vigencia_fim") else ", em vigor."))
            el.append(_p(_vig, small))
        el.append(Spacer(1, 4))

    # DOIS CAMPOS, não um (Carolina, 25/10, item 4). O documento citava apenas o RAT devido, e a
    # Súmula 351 do STJ — cadastrada em 'atividade preponderante', nas duas vigências — não
    # aparecia em lugar nenhum. É ela que sustenta a apuração individualizada por CNPJ, que é a
    # tese central da peça: sem citá-la, o documento afirma o enquadramento por estabelecimento
    # sem dizer o que o ampara.
    #
    # A preponderante vem PRIMEIRO porque é o antecedente: ela decide o grau, e o grau decide a
    # alíquota. A ordem do documento acompanha a ordem do raciocínio.
    _imprime_blocos(d.get("fundamentacao_preponderante") or [],
                    "Atividade preponderante e grau de risco")
    _imprime_blocos(d.get("fundamentacao_blocos") or [], "RAT devido")
    # O CRITERIO DO CORTE, ESCRITO (Carolina, 25/10, item 7): "o criterio precisa estar escrito no
    # documento, nao so no codigo". So aparece quando ha mais de um bloco — sem corte, nao ha o
    # que explicar.
    if len(d.get("fundamentacao_blocos") or []) > 1 or len(d.get("fundamentacao_preponderante") or []) > 1:
        el.append(_p(TEXTO_CRITERIO_VIGENCIA, small))
    # SAIRAM as tres pendencias que vinham impressas aqui: o inciso do desempate (B.1), a
    # portaria do FAP de cada exercicio (B.4) e as Solucoes de Consulta sobre preponderante x
    # principal (B.2/B.3). Eram marcadores de rascunho — "a confirmar" — dentro da peca que leva
    # assinatura de advogado: citacao nao verificada impressa como se fosse fundamento. Apagar o
    # marcador e manter a citacao seria pior, porque viraria afirmacao confiante sobre dispositivo
    # que ninguem conferiu. Voltam quando o dispositivo estiver confirmado e vindo da tabela
    # versionada, lido pela data da competencia, como as demais citacoes.
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
