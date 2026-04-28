from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

import models
import schemas


def get_categorias(db: Session) -> list[models.Categoria]:
    stmt = select(models.Categoria).order_by(models.Categoria.nome)
    return list(db.scalars(stmt).all())


def get_categoria(db: Session, categoria_id: int) -> models.Categoria | None:
    stmt = select(models.Categoria).where(models.Categoria.id == categoria_id)
    return db.scalar(stmt)


def get_categoria_by_nome(db: Session, nome: str) -> models.Categoria | None:
    stmt = select(models.Categoria).where(models.Categoria.nome == nome)
    return db.scalar(stmt)


def create_categoria(db: Session, categoria_in: schemas.CategoriaCreate) -> models.Categoria:
    categoria = models.Categoria(**categoria_in.model_dump())
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


def update_categoria(
    db: Session,
    categoria: models.Categoria,
    categoria_in: schemas.CategoriaUpdate,
) -> models.Categoria:
    for field, value in categoria_in.model_dump(exclude_unset=True).items():
        setattr(categoria, field, value)
    db.commit()
    db.refresh(categoria)
    return categoria


def delete_categoria(db: Session, categoria: models.Categoria) -> None:
    db.delete(categoria)
    db.commit()


def get_tags(db: Session) -> list[models.Tag]:
    stmt = select(models.Tag).order_by(models.Tag.nome)
    return list(db.scalars(stmt).all())


def get_tag(db: Session, tag_id: int) -> models.Tag | None:
    stmt = select(models.Tag).where(models.Tag.id == tag_id)
    return db.scalar(stmt)


def get_tag_by_nome(db: Session, nome: str) -> models.Tag | None:
    stmt = select(models.Tag).where(models.Tag.nome == nome)
    return db.scalar(stmt)


def create_tag(db: Session, tag_in: schemas.TagCreate) -> models.Tag:
    tag = models.Tag(**tag_in.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(
    db: Session,
    tag: models.Tag,
    tag_in: schemas.TagUpdate,
) -> models.Tag:
    for field, value in tag_in.model_dump(exclude_unset=True).items():
        setattr(tag, field, value)
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag: models.Tag) -> None:
    db.delete(tag)
    db.commit()


def get_produtos(db: Session) -> list[models.Produto]:
    stmt = (
        select(models.Produto)
        .options(joinedload(models.Produto.categoria_obj), joinedload(models.Produto.tag_obj))
        .order_by(models.Produto.nome)
    )
    return list(db.scalars(stmt).all())


def get_produto(db: Session, produto_id: int) -> models.Produto | None:
    stmt = (
        select(models.Produto)
        .options(joinedload(models.Produto.categoria_obj), joinedload(models.Produto.tag_obj))
        .where(models.Produto.id == produto_id)
    )
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


def migrate_categorias_from_text(db: Session) -> dict:
    produtos = db.query(models.Produto).all()
    migrated_count = 0

    for p in produtos:
        if p.categoria and not p.categoria_id:
            categoria = get_categoria_by_nome(db, p.categoria)
            if not categoria:
                categoria = create_categoria(db, schemas.CategoriaCreate(nome=p.categoria))
            p.categoria_id = categoria.id
            db.flush()
            migrated_count += 1

    db.commit()
    return {"migrated": migrated_count}
