from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from estoque.log_utils import log_acao
from estoque.models import FechamentoMensal, ItemFechamento, Produto

from .units import unidade_base_codigo


def validar_periodo(data_inicio: date, data_fim: date):
    if not data_inicio or not data_fim:
        raise ValidationError('Data inicial e data final são obrigatórias.')
    if data_inicio > data_fim:
        raise ValidationError('A data final deve ser igual ou posterior à data inicial.')


def criar_fechamento_periodo(*, data_inicio, data_fim, usuario, observacao=''):
    """Congela o estoque atual para a competência informada, sem calcular movimentações."""
    validar_periodo(data_inicio, data_fim)

    try:
        with transaction.atomic():
            if FechamentoMensal.objects.filter(
                data_inicio=data_inicio,
                data_fim=data_fim,
            ).exists():
                raise ValidationError('Já existe um fechamento para este período.')

            produtos = list(
                Produto.objects.select_for_update()
                .select_related('categoria', 'fornecedor')
                .order_by('id')
            )
            fechamento = FechamentoMensal.objects.create(
                usuario=usuario,
                data_inicio=data_inicio,
                data_fim=data_fim,
                observacao=observacao,
            )
            ItemFechamento.objects.bulk_create([
                ItemFechamento(
                    fechamento=fechamento,
                    produto=produto,
                    descricao=produto.descricao,
                    tipo_produto=produto.tipo_produto,
                    unidade_medida=unidade_base_codigo(produto),
                    categoria_nome=produto.categoria.nome if produto.categoria else '',
                    fornecedor_nome=produto.fornecedor.nome if produto.fornecedor else '',
                    quantidade=produto.quantidade_base,
                    preco_custo=produto.preco_custo,
                    preco_venda=produto.preco_venda,
                )
                for produto in produtos
            ])
            log_acao(
                usuario,
                'CRIAR',
                f'Realizou fechamento de estoque do período {fechamento.periodo_formatado}',
                'FechamentoMensal',
                fechamento.id,
            )
            return fechamento
    except IntegrityError as exc:
        raise ValidationError('Já existe um fechamento para este período.') from exc
