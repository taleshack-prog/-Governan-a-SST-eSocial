import json
import uuid
import logging
from datetime import date, datetime, timedelta
from api.tasks.celery_app import app

logger = logging.getLogger("importacao_task")


def parse_data(valor):
    if not valor:
        return None
    try:
        if isinstance(valor, (date, datetime)):
            return valor if isinstance(valor, date) else valor.date()
        import pandas as pd
        return pd.to_datetime(str(valor), dayfirst=True).date()
    except:
        return None


@app.task(name="processar_documento_universal", bind=True, max_retries=2)
def processar_documento_universal(self, conteudo_hex, nome_arquivo, tipo_mime, empresa_id, texto_preview):
    import anthropic
    from api.config import settings

    logger.info(f"Processando {nome_arquivo} para empresa {empresa_id}")

    try:
        conteudo = bytes.fromhex(conteudo_hex)
        cliente = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        texto_completo = texto_preview
        if nome_arquivo.lower().endswith(".pdf"):
            import fitz
            doc = fitz.open(stream=conteudo, filetype="pdf")
            texto_completo = ""
            for p in doc:
                texto_completo += p.get_text()
                if len(texto_completo) > 40000:
                    break
            doc.close()

        prompt = f"""Você é especialista em SST, RH e previdenciário brasileiro.
Analise este documento e extraia TODOS os dados relevantes.
ARQUIVO: {nome_arquivo}
CONTEÚDO:
{texto_completo[:20000]}

Responda APENAS com JSON:
{{
  "tipo_documento": "LTCAT|PPP|ATESTADO|TRABALHADORES|AFASTAMENTOS|CAT|PCMSO|OUTRO",
  "confianca": 0.0,
  "resumo": "descrição",
  "dados": {{}}
}}

Para LTCAT inclua em dados: empresa (string), cnpj, data_emissao (YYYY-MM-DD), responsavel_tecnico(nome,registro,conselho), agentes_nocivos(codigo_tabela24,descricao,setor,nivel_exposicao,unidade_medida,epc_eficaz,epi_eficaz,epi_ca)
Para TRABALHADORES inclua em dados: trabalhadores(nome,cpf,cargo,setor,data_admissao,sexo,matricula,pis_pasep,tipo_contrato)
Para ATESTADO inclua em dados: paciente_nome, paciente_cpf, medico_nome, medico_crm, cid, dias_afastamento, data_emissao
Para CAT inclua em dados: acidentado_nome, acidentado_cpf, data_acidente, descricao, cid, parte_corpo
Responda SOMENTE o JSON."""

        msg = cliente.messages.create(
            model="claude-haiku-4-5",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )

        texto_resp = msg.content[0].text.strip()
        if "```" in texto_resp:
            texto_resp = texto_resp.split("```")[1]
            if texto_resp.startswith("json"):
                texto_resp = texto_resp[4:]

        resultado = json.loads(texto_resp.strip())
        tipo = resultado.get("tipo_documento", "OUTRO")
        dados = resultado.get("dados", {})

        logger.info(f"Tipo detectado: {tipo}")

        from api.database import get_sync_session
        with get_sync_session() as db:
            salvos = salvar_por_tipo(db, tipo, dados, empresa_id, nome_arquivo, conteudo, texto_completo)

        return {
            "status": "concluido",
            "tipo_documento": tipo,
            "confianca": resultado.get("confianca"),
            "resumo": resultado.get("resumo"),
            **salvos,
        }

    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        raise self.retry(exc=e, countdown=15)


TIPO_MAP = {
    "LTCAT": "LTCAT", "PPP": "PPP", "PCMSO": "PCMSO",
    "ATESTADO": "ASO", "ASO": "ASO", "CAT": "CAT",
    "PGR": "PGR", "AET": "AET", "AFASTAMENTOS": "OUTRO",
}


def salvar_por_tipo(db, tipo, dados, empresa_id, nome_arquivo, conteudo, texto_completo=""):
    emp_id = uuid.UUID(empresa_id)
    if tipo == "LTCAT":
        return salvar_ltcat(db, dados, emp_id, nome_arquivo, conteudo, texto_completo)
    elif tipo == "TRABALHADORES":
        return salvar_trabalhadores(db, dados, emp_id)
    elif tipo in ("ATESTADO", "ASO"):
        return salvar_atestado(db, dados, emp_id, nome_arquivo)
    elif tipo == "CAT":
        return salvar_cat(db, dados, emp_id)
    else:
        tipo_banco = TIPO_MAP.get(tipo, "OUTRO")
        return salvar_doc(db, dados, emp_id, tipo_banco, f"{tipo} — {nome_arquivo}")


def salvar_ltcat(db, dados, empresa_id, nome_arquivo, conteudo=None, texto_completo=""):
    from api.models.documento import DocumentoTecnico
    from api.models.agente_nocivo import AgenteNocivo
    from api.models.trabalhador import Trabalhador
    from sqlalchemy import select

    resp = dados.get("responsavel_tecnico", {}) or {}
    if isinstance(resp, list):
        resp = resp[0] if resp else {}

    empresa_nome = dados.get("empresa") or dados.get("razao_social") or nome_arquivo
    if isinstance(empresa_nome, dict):
        empresa_nome = empresa_nome.get("razao_social") or nome_arquivo

    doc = DocumentoTecnico(
        id=uuid.uuid4(),
        empresa_id=empresa_id,
        tipo="LTCAT",
        titulo=f"LTCAT — {empresa_nome}",
        descricao=texto_completo[:50000] or None,
        data_emissao=parse_data(dados.get("data_emissao")) or date.today(),
        data_validade=parse_data(dados.get("data_validade")),
        responsavel_tecnico_nome=str(resp.get("nome", "") or "")[:300] or None,
        responsavel_tecnico_registro=str(resp.get("registro", "") or "")[:50] or None,
        responsavel_tecnico_conselho=str(resp.get("conselho", "") or "")[:20] or None,
        status="ativo",
        metadata_doc={"cnpj": dados.get("cnpj")},
    )
    db.add(doc)
    db.flush()

    trabs = db.execute(select(Trabalhador).where(Trabalhador.empresa_id == empresa_id)).scalars().all()
    setor_map = {}
    for t in trabs:
        if t.setor:
            setor_map.setdefault(t.setor.lower(), []).append(t.id)

    agentes_criados = 0
    for ag in dados.get("agentes_nocivos", []):
        if not ag or not isinstance(ag, dict):
            continue
        descricao = str(ag.get("descricao", "") or "")[:500] or "Agente"
        codigo = str(ag.get("codigo_tabela24", "") or "")[:10] or "00.00.000"
        setor_ag = str(ag.get("setor", "") or "").lower()
        trab_ids = []
        for sk, tv in setor_map.items():
            if setor_ag and (setor_ag in sk or sk in setor_ag):
                trab_ids.extend(tv)
        for trab_id in (trab_ids or [None]):
            db.add(AgenteNocivo(
                id=uuid.uuid4(),
                empresa_id=empresa_id,
                trabalhador_id=trab_id,
                documento_origem_id=doc.id,
                codigo_tabela24=codigo,
                descricao_agente=descricao,
                nivel_exposicao=str(ag.get("nivel_exposicao", "") or "")[:100] or None,
                unidade_medida=str(ag.get("unidade_medida", "") or "")[:30] or None,
                epc_eficaz=ag.get("epc_eficaz"),
                epi_eficaz=ag.get("epi_eficaz"),
                epi_ca=str(ag.get("epi_ca", "") or "")[:20] or None,
                data_inicio=parse_data(dados.get("data_emissao")) or date.today(),
                created_by_ai=True,
                confidence_score=0.85,
                needs_review=True,
                trecho_original=descricao,
            ))
            agentes_criados += 1

    db.commit()
    return {"documento_id": str(doc.id), "agentes_criados": agentes_criados}


def salvar_trabalhadores(db, dados, empresa_id):
    from api.models.trabalhador import Trabalhador
    from api.models.vinculo import Vinculo
    from sqlalchemy import select

    importados = 0
    duplicados = 0
    for t in dados.get("trabalhadores", []):
        if not t or not isinstance(t, dict):
            continue
        nome = str(t.get("nome", "") or "").strip()
        if not nome:
            continue
        cpf = "".join(c for c in str(t.get("cpf", "") or "") if c.isdigit()) or None
        if cpf:
            if db.execute(select(Trabalhador).where(
                Trabalhador.empresa_id == empresa_id, Trabalhador.cpf == cpf
            )).scalar_one_or_none():
                duplicados += 1
                continue
        data_adm = parse_data(t.get("data_admissao"))
        trab_id = uuid.uuid4()
        db.add(Trabalhador(
            id=trab_id, empresa_id=empresa_id, nome=nome, cpf=cpf,
            cargo=str(t.get("cargo", "") or "")[:200] or None,
            setor=str(t.get("setor", "") or "")[:200] or None,
            matricula=str(t.get("matricula", "") or "")[:50] or None,
            pis_pasep=str(t.get("pis_pasep", "") or "")[:20] or None,
            data_admissao=data_adm,
            sexo=(t.get("sexo", "M") or "M")[0].upper(),
        ))
        if data_adm:
            db.add(Vinculo(
                id=uuid.uuid4(), trabalhador_id=trab_id, empresa_id=empresa_id,
                cargo=str(t.get("cargo", "") or "")[:200] or None,
                data_admissao=data_adm,
                tipo_contrato=str(t.get("tipo_contrato", "CLT") or "CLT")[:30],
                status="ativo",
            ))
        importados += 1
    db.commit()
    return {"trabalhadores_importados": importados, "duplicados": duplicados}


def salvar_atestado(db, dados, empresa_id, nome_arquivo):
    from api.models.documento import DocumentoTecnico
    from api.models.trabalhador import Trabalhador
    from api.models.afastamento import Afastamento
    from sqlalchemy import select

    trab = None
    cpf = "".join(c for c in str(dados.get("paciente_cpf", "") or "") if c.isdigit())
    nome_pac = str(dados.get("paciente_nome", "") or "").strip()

    if cpf:
        trab = db.execute(select(Trabalhador).where(
            Trabalhador.empresa_id == empresa_id, Trabalhador.cpf == cpf
        )).scalar_one_or_none()

    if not trab and nome_pac:
        for t in db.execute(select(Trabalhador).where(
            Trabalhador.empresa_id == empresa_id
        )).scalars().all():
            if nome_pac.lower() in t.nome.lower() or t.nome.lower() in nome_pac.lower():
                trab = t
                break

    doc = DocumentoTecnico(
        id=uuid.uuid4(), empresa_id=empresa_id, tipo="ASO",
        titulo=f"Atestado — {nome_pac or nome_arquivo}",
        responsavel_tecnico_nome=str(dados.get("medico_nome", "") or "")[:300] or None,
        responsavel_tecnico_registro=str(dados.get("medico_crm", "") or "")[:50] or None,
        responsavel_tecnico_conselho="CRM",
        data_emissao=parse_data(dados.get("data_emissao")) or date.today(),
        status="ativo",
        metadata_doc=dados,
    )
    db.add(doc)
    db.flush()

    afastamento_id = None
    dias = dados.get("dias_afastamento")
    if trab and dias:
        try:
            data_inicio = parse_data(dados.get("data_emissao")) or date.today()
            data_fim = data_inicio + timedelta(days=int(str(dias).split()[0]))
            af = Afastamento(
                id=uuid.uuid4(), empresa_id=empresa_id, trabalhador_id=trab.id,
                data_inicio=data_inicio, data_fim=data_fim,
                motivo="doenca", cid=str(dados.get("cid", "") or "")[:10] or None,
                status="encerrado",
            )
            db.add(af)
            afastamento_id = str(af.id)
        except:
            pass

    db.commit()
    return {
        "documento_id": str(doc.id), "tipo": "ATESTADO",
        "trabalhador_vinculado": trab.nome if trab else None,
        "afastamento_criado": afastamento_id is not None,
        "aviso": None if trab else f"Trabalhador '{nome_pac}' não encontrado",
    }


def salvar_doc(db, dados, empresa_id, tipo, titulo):
    from api.models.documento import DocumentoTecnico
    doc = DocumentoTecnico(
        id=uuid.uuid4(), empresa_id=empresa_id, tipo=tipo[:20],
        titulo=titulo[:500], data_emissao=date.today(), status="ativo", metadata_doc=dados,
    )
    db.add(doc)
    db.commit()
    return {"documento_id": str(doc.id), "tipo": tipo}


def salvar_cat(db, dados, empresa_id):
    from api.models.cat_registro import CatRegistro
    from api.models.trabalhador import Trabalhador
    from sqlalchemy import select

    trab = None
    cpf = "".join(c for c in str(dados.get("acidentado_cpf", "") or "") if c.isdigit())
    if cpf:
        trab = db.execute(select(Trabalhador).where(
            Trabalhador.empresa_id == empresa_id, Trabalhador.cpf == cpf
        )).scalar_one_or_none()

    cat = CatRegistro(
        id=uuid.uuid4(), empresa_id=empresa_id,
        trabalhador_id=trab.id if trab else None,
        data_acidente=parse_data(dados.get("data_acidente")) or date.today(),
        descricao=str(dados.get("descricao", "") or "")[:1000],
        cid=str(dados.get("cid", "") or "")[:10] or None,
        parte_corpo_atingida=str(dados.get("parte_corpo", "") or "")[:200] or None,
        status="registrado",
    )
    db.add(cat)
    db.commit()
    return {"cat_id": str(cat.id), "tipo": "CAT"}
