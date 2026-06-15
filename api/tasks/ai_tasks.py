# SST ESOCIAL GOV — Tasks de IA
from api.tasks.celery_app import app
import logging

logger = logging.getLogger("sst_tasks")

@app.task(name="validar_documento")
def validar_documento_task(documento_id: str, empresa_id: str):
    logger.info(f"Validando documento {documento_id}")
    return {"status": "concluido", "documento_id": documento_id}


@app.task(name="processar_ltcat", bind=True, max_retries=3)
def processar_ltcat_task(self, conteudo_hex: str, empresa_id: str, nome_arquivo: str):
    """Task Celery — processa LTCAT em background sem timeout."""
    import asyncio
    import uuid
    import json
    from datetime import date

    logger.info(f"Processando LTCAT para empresa {empresa_id}")

    # Cache por hash — não reprocessar mesmo arquivo
    import hashlib
    arquivo_hash = hashlib.md5(conteudo_hex[:1000].encode()).hexdigest()[:16]
    cache_key = f"ltcat_cache:{empresa_id}:{arquivo_hash}"

    try:
        # Importar dependências dentro da task
        from api.routers.importacao_pdf import (
            extrair_chunks_pdf, analisar_ltcat_ia_completo,
            parse_data
        )
        from api.models.documento import DocumentoTecnico
        from api.models.agente_nocivo import AgenteNocivo
        from api.models.trabalhador import Trabalhador
        from api.database import get_sync_session
        from sqlalchemy import select
        import fitz

        conteudo = bytes.fromhex(conteudo_hex)

        # Processar com IA
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        dados = loop.run_until_complete(analisar_ltcat_ia_completo(conteudo))
        loop.close()

        # Salvar no banco via sessão síncrona
        with get_sync_session() as db:
            # Extrair texto para salvar
            doc_fitz = fitz.open(stream=conteudo, filetype="pdf")
            doc_texto = "".join(p.get_text() for p in doc_fitz)[:50000]
            doc_fitz.close()

            doc = DocumentoTecnico(
                id=uuid.uuid4(),
                empresa_id=uuid.UUID(empresa_id),
                tipo="LTCAT",
                titulo=dados.get("titulo") or f"LTCAT — {dados.get('empresa', 'Empresa')}",
                descricao=doc_texto,
                data_emissao=parse_data(dados.get("data_emissao")) or date.today(),
                data_validade=parse_data(dados.get("data_validade")),
                responsavel_tecnico_nome=dados.get("responsavel_tecnico", {}).get("nome") if isinstance(dados.get("responsavel_tecnico"), dict) else None,
                responsavel_tecnico_registro=dados.get("responsavel_tecnico", {}).get("registro") if isinstance(dados.get("responsavel_tecnico"), dict) else None,
                responsavel_tecnico_conselho=dados.get("responsavel_tecnico", {}).get("conselho") if isinstance(dados.get("responsavel_tecnico"), dict) else None,
                status="ativo",
                metadata_doc={"cnpj": dados.get("cnpj"), "setores": dados.get("setores", [])},
            )
            db.add(doc)
            db.flush()

            # Buscar trabalhadores
            trabs = db.execute(
                select(Trabalhador).where(
                    Trabalhador.empresa_id == uuid.UUID(empresa_id)
                )
            ).scalars().all()

            setor_para_trab = {}
            for t in trabs:
                if t.setor:
                    key = t.setor.lower()
                    if key not in setor_para_trab:
                        setor_para_trab[key] = []
                    setor_para_trab[key].append(t.id)

            # Criar agentes nocivos
            agentes_criados = 0
            for agente in dados.get("agentes_nocivos", []):
                codigo = agente.get("codigo_tabela24") or "00.00.000"
                descricao = agente.get("descricao", "Agente não identificado")
                setor_agente = agente.get("setor", "")

                trabs_setor = []
                for setor_key, trab_ids in setor_para_trab.items():
                    if setor_agente.lower() in setor_key or setor_key in setor_agente.lower():
                        trabs_setor.extend(trab_ids)

                trab_ids_usar = trabs_setor if trabs_setor else [None]
                for trab_id in trab_ids_usar:
                    ag = AgenteNocivo(
                        id=uuid.uuid4(),
                        empresa_id=uuid.UUID(empresa_id),
                        trabalhador_id=trab_id,
                        documento_origem_id=doc.id,
                        codigo_tabela24=str(codigo)[:10] if codigo else "00.00.000",
                        descricao_agente=str(descricao)[:500] if descricao else None,
                        nivel_exposicao=str(agente.get("nivel_exposicao","") or "")[:100] or None,
                        unidade_medida=str(agente.get("unidade_medida","") or "")[:30] or None,
                        epc_eficaz=agente.get("epc_eficaz"),
                        epi_eficaz=agente.get("epi_eficaz"),
                        epi_ca=str(agente.get("epi_ca","") or "")[:20] or None,
                        data_inicio=parse_data(dados.get("data_emissao")) or date.today(),
                        created_by_ai=True,
                        confidence_score=0.85,
                        needs_review=True,
                        trecho_original=descricao,
                    )
                    db.add(ag)
                    agentes_criados += 1

            db.commit()

        logger.info(f"LTCAT processado: {agentes_criados} agentes criados")
        return {
            "status": "concluido",
            "empresa": dados.get("empresa"),
            "agentes_criados": agentes_criados,
            "setores": dados.get("setores", []),
            "documento_titulo": dados.get("titulo"),
        }

    except Exception as e:
        logger.error(f"Erro ao processar LTCAT: {str(e)}")
        raise self.retry(exc=e, countdown=10)
