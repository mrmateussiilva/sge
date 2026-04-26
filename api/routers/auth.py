from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import auth
import schemas
from database import get_db


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def register(
    usuario_in: schemas.UsuarioCreate,
    db: Session = Depends(get_db),
) -> schemas.UsuarioResponse:
    if auth.get_usuario_by_email(db, usuario_in.email):
        raise HTTPException(status_code=400, detail="Email ja cadastrado.")

    return auth.create_usuario(db, usuario_in)


@router.post("/login", response_model=schemas.LoginResponse)
def login(
    credentials: schemas.UsuarioLogin,
    db: Session = Depends(get_db),
) -> schemas.LoginResponse:
    usuario = auth.authenticate_usuario(db, credentials.email, credentials.senha)
    if usuario is None:
        raise HTTPException(status_code=401, detail="Email ou senha invalidos.")

    access_token = auth.create_access_token(data={"sub": usuario.email})
    return schemas.LoginResponse(
        access_token=access_token,
        token_type="bearer",
        usuario=usuario,
    )


@router.get("/me", response_model=schemas.UsuarioResponse)
def me(usuario=Depends(auth.get_current_user)) -> schemas.UsuarioResponse:
    return usuario
