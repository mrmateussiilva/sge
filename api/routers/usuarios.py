from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import auth
import models
import schemas
from database import get_db


router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=list[schemas.UsuarioResponse])
def list_usuarios(
    db: Session = Depends(get_db),
    _admin=Depends(auth.get_current_admin),
) -> list[schemas.UsuarioResponse]:
    return list(db.scalars(select(models.Usuario).order_by(models.Usuario.created_at.desc())).all())


@router.post("", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def create_usuario(
    usuario_in: schemas.UsuarioAdminCreate,
    db: Session = Depends(get_db),
    _admin=Depends(auth.get_current_admin),
) -> schemas.UsuarioResponse:
    if auth.get_usuario_by_email(db, usuario_in.email):
        raise HTTPException(status_code=400, detail="Email ja cadastrado.")

    return auth.create_usuario(db, usuario_in)


@router.put("/{usuario_id}", response_model=schemas.UsuarioResponse)
def update_usuario(
    usuario_id: int,
    usuario_in: schemas.UsuarioUpdate,
    db: Session = Depends(get_db),
    admin=Depends(auth.get_current_admin),
) -> schemas.UsuarioResponse:
    usuario = db.get(models.Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")

    email_owner = auth.get_usuario_by_email(db, usuario_in.email)
    if email_owner is not None and email_owner.id != usuario.id:
        raise HTTPException(status_code=400, detail="Email ja cadastrado.")

    if usuario.id == admin.id and not usuario_in.ativo:
        raise HTTPException(status_code=400, detail="Voce nao pode desativar sua propria conta.")
    if usuario.id == admin.id and usuario_in.perfil != "admin":
        raise HTTPException(status_code=400, detail="Voce nao pode remover seu proprio perfil de administrador.")

    usuario.nome = usuario_in.nome
    usuario.email = usuario_in.email.lower()
    usuario.perfil = usuario_in.perfil
    usuario.ativo = usuario_in.ativo

    db.commit()
    db.refresh(usuario)
    return usuario
