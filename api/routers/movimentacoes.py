from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user
import crud
import schemas
from database import get_db
import cache


router = APIRouter(
    prefix="/movimentacoes",
    tags=["movimentacoes"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[schemas.MovimentacaoResponse])
def listar_movimentacoes(db: Session = Depends(get_db)) -> list[schemas.MovimentacaoResponse]:
    cached_data = cache.get_cached("movimentacoes")
    if cached_data is not None:
        return cached_data
    
    data = crud.get_movimentacoes(db)
    cache.set_cached("movimentacoes", data)
    return data


@router.post(
    "",
    response_model=schemas.MovimentacaoResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_movimentacao(
    movimentacao_in: schemas.MovimentacaoCreate,
    db: Session = Depends(get_db),
) -> schemas.MovimentacaoResponse:
    try:
        result = crud.create_movimentacao(db, movimentacao_in)
        cache.invalidate("movimentacoes")
        cache.invalidate("dashboard")
        cache.invalidate("produtos")
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
