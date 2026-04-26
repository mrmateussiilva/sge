from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import crud
import schemas
from database import get_db


router = APIRouter(prefix="/movimentacoes", tags=["movimentacoes"])


@router.get("", response_model=list[schemas.MovimentacaoResponse])
def listar_movimentacoes(db: Session = Depends(get_db)) -> list[schemas.MovimentacaoResponse]:
    return crud.get_movimentacoes(db)


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
        return crud.create_movimentacao(db, movimentacao_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
