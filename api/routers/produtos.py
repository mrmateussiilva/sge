from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from auth import get_current_user
import crud
import schemas
from database import get_db
import cache


router = APIRouter(
    prefix="/produtos",
    tags=["produtos"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[schemas.ProdutoResponse])
def listar_produtos(db: Session = Depends(get_db)) -> list[schemas.ProdutoResponse]:
    cached_data = cache.get_cached("produtos")
    if cached_data is not None:
        return cached_data
    
    data = crud.get_produtos(db)
    cache.set_cached("produtos", data)
    return data


@router.post("", response_model=schemas.ProdutoResponse, status_code=status.HTTP_201_CREATED)
def criar_produto(
    produto_in: schemas.ProdutoCreate,
    db: Session = Depends(get_db),
) -> schemas.ProdutoResponse:
    result = crud.create_produto(db, produto_in)
    cache.invalidate("produtos")
    cache.invalidate("dashboard")
    return result


@router.get("/{produto_id}", response_model=schemas.ProdutoResponse)
def buscar_produto(
    produto_id: int,
    db: Session = Depends(get_db),
) -> schemas.ProdutoResponse:
    produto = crud.get_produto(db, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto nao encontrado.")

    return produto


@router.put("/{produto_id}", response_model=schemas.ProdutoResponse)
def atualizar_produto(
    produto_id: int,
    produto_in: schemas.ProdutoUpdate,
    db: Session = Depends(get_db),
) -> schemas.ProdutoResponse:
    produto = crud.get_produto(db, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto nao encontrado.")

    result = crud.update_produto(db, produto, produto_in)
    cache.invalidate("produtos")
    cache.invalidate("dashboard")
    return result


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_produto(produto_id: int, db: Session = Depends(get_db)) -> Response:
    produto = crud.get_produto(db, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto nao encontrado.")

    crud.delete_produto(db, produto)
    cache.invalidate("produtos")
    cache.invalidate("dashboard")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
