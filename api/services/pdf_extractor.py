# ==============================================================
# SST ESOCIAL GOV — Extrator de PDF
# Arquivo: api/services/pdf_extractor.py
# ==============================================================

def extrair_texto_pdf(conteudo_bytes: bytes) -> str:
    """Extrai texto completo de um PDF usando PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=conteudo_bytes, filetype="pdf")
        texto = ""
        for pagina in doc:
            texto += pagina.get_text()
        doc.close()
        return texto.strip()
    except Exception as e:
        return f"Erro ao extrair PDF: {str(e)}"


def extrair_texto_docx(conteudo_bytes: bytes) -> str:
    """Extrai texto de DOCX."""
    try:
        import docx, io
        doc = docx.Document(io.BytesIO(conteudo_bytes))
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except Exception as e:
        return f"Erro ao extrair DOCX: {str(e)}"


def extrair_texto(conteudo_bytes: bytes, filename: str) -> str:
    """Detecta o tipo e extrai o texto."""
    nome = filename.lower()
    if nome.endswith(".pdf"):
        return extrair_texto_pdf(conteudo_bytes)
    elif nome.endswith(".docx") or nome.endswith(".doc"):
        return extrair_texto_docx(conteudo_bytes)
    else:
        try:
            return conteudo_bytes.decode("utf-8", errors="ignore")
        except:
            return ""
