from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from auth import get_current_user
import crud
import schemas
from database import get_db


router = APIRouter(
    prefix="/categorias",
    tags=["categorias"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[schemas.CategoriaResponse])
def listar_categorias(db: Session = Depends(get_db)) -> list[schemas.CategoriaResponse]:
    return crud.get_categorias(db)


@router.post("/migrate", response_model=dict)
def migrar_categorias(db: Session = Depends(get_db)) -> dict:
    return crud.migrate_categorias_from_text(db)


@router.post("", response_model=schemas.CategoriaResponse, status_code=status.HTTP_201_CREATED)
def criar_categoria(
    categoria_in: schemas.CategoriaCreate,
    db: Session = Depends(get_db),
) -> schemas.CategoriaResponse:
    if crud.get_categoria_by_nome(db, categoria_in.nome):
        raise HTTPException(status_code=400, detail="Categoria ja cadastrada.")

    return crud.create_categoria(db, categoria_in)


@router.get("/{categoria_id}", response_model=schemas.CategoriaResponse)
def buscar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
) -> schemas.CategoriaResponse:
    categoria = crud.get_categoria(db, categoria_id)
    if categoria is None:
        raise HTTPException(status_code=404, detail="Categoria nao encontrada.")

    return categoria


@router.put("/{categoria_id}", response_model=schemas.CategoriaResponse)
def atualizar_categoria(
    categoria_id: int,
    categoria_in: schemas.CategoriaUpdate,
    db: Session = Depends(get_db),
) -> schemas.CategoriaResponse:
    categoria = crud.get_categoria(db, categoria_id)
    if categoria is None:
        raise HTTPException(status_code=404, detail="Categoria nao encontrada.")

    if categoria_in.nome:
        categoria_existente = crud.get_categoria_by_nome(db, categoria_in.nome)
        if categoria_existente and categoria_existente.id != categoria_id:
            raise HTTPException(status_code=400, detail="Nome da categoria ja cadastrado.")

    return crud.update_categoria(db, categoria, categoria_in)


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_categoria(categoria_id: int, db: Session = Depends(get_db)) -> Response:
    categoria = crud.get_categoria(db, categoria_id)
    if categoria is None:
        raise HTTPException(status_code=404, detail="Categoria nao encontrada.")

    crud.delete_categoria(db, categoria)
    return Response(status_code=status.HTTP_204_NO_CONTENT)