import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db


SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "change-this-secret-key-in-production-please",
)
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_usuario_by_email(db: Session, email: str) -> models.Usuario | None:
    stmt = select(models.Usuario).where(models.Usuario.email == email.lower())
    return db.scalar(stmt)


def count_usuarios(db: Session) -> int:
    return len(list(db.scalars(select(models.Usuario.id)).all()))


def create_usuario(db: Session, usuario_in: schemas.UsuarioCreate) -> models.Usuario:
    usuario = models.Usuario(
        nome=usuario_in.nome,
        email=usuario_in.email.lower(),
        senha_hash=get_password_hash(usuario_in.senha),
        perfil=usuario_in.perfil,
        ativo=getattr(usuario_in, "ativo", True),
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def authenticate_usuario(db: Session, email: str, senha: str) -> models.Usuario | None:
    usuario = get_usuario_by_email(db, email)
    if usuario is None or not usuario.ativo or not verify_password(senha, usuario.senha_hash):
        return None
    return usuario


def get_current_admin(
    usuario: models.Usuario = Depends(get_current_user),
) -> models.Usuario:
    if usuario.perfil != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores.",
        )
    return usuario


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais invalidas.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    usuario = get_usuario_by_email(db, email)
    if usuario is None or not usuario.ativo:
        raise credentials_exception

    return usuario
