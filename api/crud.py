from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

import models
import schemas


def get_produtos(db: Session) -> list[models.Produto]:
    stmt = select(models.Produto).order_by(models.Produto.nome)
    return list(db.scalars(stmt).all())


def get_produto(db: Session, produto_id: int) -> models.Produto | None:
    stmt = select(models.Produto).where(models.Produto.id == produto_id)
    return db.scalar(stmt)


def get_produto_by_sku(db: Session, sku: str) -> models.Produto | None:
    stmt = select(models.Produto).where(models.Produto.sku == sku)
    return db.scalar(stmt)


def create_produto(db: Session, produto_in: schemas.ProdutoCreate) -> models.Produto:
    produto = models.Produto(**produto_in.model_dump())
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto


def update_produto(
    db: Session,
    produto: models.Produto,
    produto_in: schemas.ProdutoUpdate,
) -> models.Produto:
    for field, value in produto_in.model_dump().items():
        setattr(produto, field, value)

    db.commit()
    db.refresh(produto)
    return produto


def delete_produto(db: Session, produto: models.Produto) -> None:
    db.delete(produto)
    db.commit()


def get_movimentacoes(db: Session) -> list[models.Movimentacao]:
    stmt = (
        select(models.Movimentacao)
        .options(joinedload(models.Movimentacao.produto))
        .order_by(models.Movimentacao.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def create_movimentacao(
    db: Session,
    movimentacao_in: schemas.MovimentacaoCreate,
) -> models.Movimentacao:
    produto = get_produto(db, movimentacao_in.produto_id)
    if produto is None:
        raise ValueError("Produto nao encontrado.")

    if movimentacao_in.tipo == "entrada":
        novo_estoque = produto.estoque_atual + movimentacao_in.quantidade
    elif movimentacao_in.tipo == "saida":
        novo_estoque = produto.estoque_atual - movimentacao_in.quantidade
        if novo_estoque < 0:
            raise ValueError("Estoque insuficiente para a saida.")
    else:
        novo_estoque = movimentacao_in.quantidade

    produto.estoque_atual = novo_estoque

    movimentacao = models.Movimentacao(**movimentacao_in.model_dump())
    db.add(movimentacao)
    db.commit()
    db.refresh(movimentacao)
    return db.scalar(
        select(models.Movimentacao)
        .options(joinedload(models.Movimentacao.produto))
        .where(models.Movimentacao.id == movimentacao.id)
    )


def get_dashboard_data(db: Session) -> dict:
    total_produtos = db.scalar(select(func.count(models.Produto.id))) or 0

    produtos_com_estoque_baixo = list(
        db.scalars(
            select(models.Produto)
            .where(models.Produto.estoque_atual <= models.Produto.estoque_minimo)
            .order_by(models.Produto.nome)
        ).all()
    )

    ultimas_movimentacoes = list(
        db.scalars(
            select(models.Movimentacao)
            .options(joinedload(models.Movimentacao.produto))
            .order_by(models.Movimentacao.created_at.desc())
            .limit(10)
        ).all()
    )

    return {
        "total_produtos": total_produtos,
        "produtos_com_estoque_baixo": produtos_com_estoque_baixo,
        "ultimas_movimentacoes": ultimas_movimentacoes,
    }
