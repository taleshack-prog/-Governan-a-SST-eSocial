# api/routers/documentos.py — SST ESOCIAL GOV
import hashlib
from uuid import UUID
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from api.database import get_db, set_tenant
from api.models.documento import DocumentoTecnico
from api.models.usuario import Usuario
from api.auth import get_current_user

router = APIRouter()


class DocumentoResponse(BaseModel):
    id: str
    tipo: str
    titulo: str
    status: str
    data_emissao: date
    data_validade: Optional[date]
    versao: int
    responsavel_tecnico_nome: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


@router.get("/", response_model=List[dict])
async def listar_documentos(
    tipo: Optional[str] = None,
    status_doc: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    query = select(DocumentoTecnico).where(
        DocumentoTecnico.empresa_id == current_user.empresa_id
    )
    if tipo:
        query = query.where(DocumentoTecnico.tipo == tipo)
    if status_doc:
        query = query.where(DocumentoTecnico.status == status_doc)

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

    # Hash do conteúdo
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
        "responsavel_tecnico_registro": doc.responsavel_tecnico_registro,
        "content_hash": doc.content_hash,
        "metadata": doc.metadata_doc,
    }


@router.post("/{doc_id}/validar")
async def solicitar_validacao(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Dispara validação IA assíncrona para o documento."""
    result = await db.execute(
        select(DocumentoTecnico).where(
            DocumentoTecnico.id == doc_id,
            DocumentoTecnico.empresa_id == current_user.empresa_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # Em produção: disparar task Celery aqui
    # from api.tasks.ai_tasks import validar_documento_task
    # task = validar_documento_task.delay(str(doc_id), str(current_user.empresa_id))

    return {
        "message": "Validação iniciada",
        "documento_id": str(doc_id),
        "status": "processando"
    }
