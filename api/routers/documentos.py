# api/routers/documentos.py — SST ESOCIAL GOV
import hashlib, sys, os
from uuid import UUID
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.database import get_db, set_tenant
from api.models.documento import DocumentoTecnico
from api.models.ai_validacao import AiValidacao
from api.models.usuario import Usuario
from api.auth import get_current_user

router = APIRouter()


@router.get("/")
async def listar_documentos(
    tipo: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    query = select(DocumentoTecnico).where(
        DocumentoTecnico.empresa_id == current_user.empresa_id
    )
    if tipo:
        query = query.where(DocumentoTecnico.tipo == tipo)
    result = await db.execute(query)
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "tipo": d.tipo,
            "titulo": d.titulo,
            "status": d.status,
            "data_emissao": str(d.data_emissao),
            "data_validade": str(d.data_validade) if d.data_validade else None,
            "versao": d.versao,
            "responsavel_tecnico_nome": d.responsavel_tecnico_nome,
        }
        for d in docs
    ]


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_documento(
    tipo: str = Form(...),
    titulo: str = Form(...),
    data_emissao: str = Form(...),
    responsavel_nome: Optional[str] = Form(None),
    responsavel_registro: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if tipo not in ("LTCAT", "PGR", "PCMSO", "ASO", "CAT", "AET", "OUTRO"):
        raise HTTPException(status_code=422, detail="Tipo de documento inválido")

    contents = await file.read()
    content_hash = hashlib.sha256(contents).hexdigest()

    doc = DocumentoTecnico(
        empresa_id=current_user.empresa_id,
        tipo=tipo,
        titulo=titulo,
        data_emissao=date.fromisoformat(data_emissao),
        responsavel_tecnico_nome=responsavel_nome,
        responsavel_tecnico_registro=responsavel_registro,
        status="rascunho",
        content_hash=content_hash,
        storage_path=f"uploads/{tipo}/{file.filename}",
        created_by=current_user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return {"id": str(doc.id), "titulo": doc.titulo, "status": doc.status}


@router.get("/{doc_id}")
async def obter_documento(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(DocumentoTecnico).where(
            DocumentoTecnico.id == doc_id,
            DocumentoTecnico.empresa_id == current_user.empresa_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return {
        "id": str(doc.id),
        "tipo": doc.tipo,
        "titulo": doc.titulo,
        "status": doc.status,
        "data_emissao": str(doc.data_emissao),
        "data_validade": str(doc.data_validade) if doc.data_validade else None,
        "versao": doc.versao,
        "responsavel_tecnico_nome": doc.responsavel_tecnico_nome,
        "content_hash": doc.content_hash,
    }


@router.post("/{doc_id}/validar")
async def solicitar_validacao(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(DocumentoTecnico).where(
            DocumentoTecnico.id == doc_id,
            DocumentoTecnico.empresa_id == current_user.empresa_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # Criar registro de validação
    val = AiValidacao(
        empresa_id=current_user.empresa_id,
        documento_id=doc_id,
        tipo_validacao=f"VALIDACAO_{doc.tipo}",
        status="processando",
    )
    db.add(val)
    await db.commit()
    await db.refresh(val)

    # Rodar pipeline IA
    try:
        sys.path.insert(0, "/app")
        from ai_layer.pipeline import SSTAIPipeline
        pipeline = SSTAIPipeline()
        texto = f"Documento: {doc.titulo}\nTipo: {doc.tipo}\nResponsável: {doc.responsavel_tecnico_nome}\nEmpresa: empresa_id={doc.empresa_id}"
        pipe_result = await pipeline.run(str(doc_id), str(current_user.empresa_id), texto, doc.tipo)

        val.status = "concluido"
        val.confidence_score = pipe_result.confidence_score
        val.grade_label = pipe_result.grade_label
        val.needs_human_review = pipe_result.needs_human_review
        val.model_used = pipe_result.model_used
        val.tokens_used = pipe_result.tokens_total
        val.latency_ms = pipe_result.latency_total_ms
        val.erros = pipe_result.erros
        val.alertas = pipe_result.alertas
        val.sugestoes = [str(c) for c in pipe_result.codigos_sugeridos]
        val.resultado = {"etapas": pipe_result.etapas, "agentes": pipe_result.agentes_extraidos}
    except Exception as e:
        val.status = "erro"
        val.erros = [str(e)]

    await db.commit()

    return {
        "message": "Validação concluída",
        "validacao_id": str(val.id),
        "status": val.status,
        "grade": val.grade_label,
        "confidence": val.confidence_score,
    }
