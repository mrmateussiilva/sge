from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from auth import get_current_user
import crud
import schemas
from database import get_db
import app_cache as cache


router = APIRouter(
    prefix="/categorias",
    tags=["categorias"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[schemas.CategoriaResponse])
def listar_categorias(db: Session = Depends(get_db)) -> list[schemas.CategoriaResponse]:
    cached_data = cache.get_cached("categorias")
    if cached_data is not None:
        return cached_data
    
    data = crud.get_categorias(db)
    cache.set_cached("categorias", data)
    return data


@router.post("/migrate", response_model=dict)
def migrar_categorias(db: Session = Depends(get_db)) -> dict:
    return crud.migrate_categorias_from_text(db)


@router.post("", response_model=schemas.CategoriaResponse, status_code=status.HTTP_201_CREATED)
def criar_categoria(
    categoria_in: schemas.CategoriaCreate,
    db: Session = Depends(get_db),
) -> schemas.CategoriaResponse:
    result = crud.create_categoria(db, categoria_in)
    cache.invalidate("categorias")
    return result


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

    result = crud.update_categoria(db, categoria, categoria_in)
    cache.invalidate("categorias")
    return result


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_categoria(categoria_id: int, db: Session = Depends(get_db)) -> Response:
    categoria = crud.get_categoria(db, categoria_id)
    if categoria is None:
        raise HTTPException(status_code=404, detail="Categoria nao encontrada.")

    crud.delete_categoria(db, categoria)
    cache.invalidate("categorias")
    return Response(status_code=status.HTTP_204_NO_CONTENT)