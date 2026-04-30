from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from auth import get_current_user
import crud
import schemas
from database import get_db
import cache


router = APIRouter(
    prefix="/tags",
    tags=["tags"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[schemas.TagResponse])
def listar_tags(db: Session = Depends(get_db)) -> list[schemas.TagResponse]:
    cached_data = cache.get_cached("tags")
    if cached_data is not None:
        return cached_data
    
    data = crud.get_tags(db)
    cache.set_cached("tags", data)
    return data


@router.post("", response_model=schemas.TagResponse, status_code=status.HTTP_201_CREATED)
def criar_tag(
    tag_in: schemas.TagCreate,
    db: Session = Depends(get_db),
) -> schemas.TagResponse:
    result = crud.create_tag(db, tag_in)
    cache.invalidate("tags")
    return result


@router.get("/{tag_id}", response_model=schemas.TagResponse)
def buscar_tag(
    tag_id: int,
    db: Session = Depends(get_db),
) -> schemas.TagResponse:
    tag = crud.get_tag(db, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag nao encontrada.")

    return tag


@router.put("/{tag_id}", response_model=schemas.TagResponse)
def atualizar_tag(
    tag_id: int,
    tag_in: schemas.TagUpdate,
    db: Session = Depends(get_db),
) -> schemas.TagResponse:
    tag = crud.get_tag(db, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag nao encontrada.")

    result = crud.update_tag(db, tag, tag_in)
    cache.invalidate("tags")
    return result


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_tag(tag_id: int, db: Session = Depends(get_db)) -> Response:
    tag = crud.get_tag(db, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag nao encontrada.")

    crud.delete_tag(db, tag)
    cache.invalidate("tags")
    return Response(status_code=status.HTTP_204_NO_CONTENT)