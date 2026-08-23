import os
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from estoque.models import Fornecedor, ItemOrdemCompra, OrdemCompra, Produto
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Cria dados isolados e determinísticos para os testes E2E do Playwright.'

    def handle(self, *args, **options):
        User = get_user_model()
        password = os.getenv('E2E_PASSWORD', 'sge-e2e-local-2026')

        operador, _ = User.objects.get_or_create(username='e2e_operador')
        operador.is_staff = False
        operador.is_superuser = False
        operador.set_password(password)
        operador.save()
        operador.groups.set([Group.objects.get(name='Operador')])

        leitura, _ = User.objects.get_or_create(username='e2e_leitura')
        leitura.is_staff = False
        leitura.is_superuser = False
        leitura.set_password(password)
        leitura.save()
        leitura.groups.set([Group.objects.get(name='Visualizador')])

        admin, _ = User.objects.get_or_create(username='e2e_admin')
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password(password)
        admin.save()

        fornecedor, _ = Fornecedor.objects.update_or_create(
            nome='E2E Fornecedor',
            defaults={'cnpj': '', 'email': 'e2e@example.test'},
        )
        produto_mov, _ = Produto.objects.update_or_create(
            descricao='E2E Produto Movimento',
            defaults={
                'tipo_produto': 'OUTRO',
                'unidade_medida': 'UN',
                'quantidade_base': Decimal('10.00'),
                'preco_custo': Decimal('5.00'),
                'preco_venda': Decimal('8.00'),
                'estoque_minimo': Decimal('2.00'),
                'fornecedor': fornecedor,
            },
        )
        produto_ordem, _ = Produto.objects.update_or_create(
            descricao='E2E Produto Ordem',
            defaults={
                'tipo_produto': 'OUTRO',
                'unidade_medida': 'UN',
                'quantidade_base': Decimal('10.00'),
                'preco_custo': Decimal('5.00'),
                'preco_venda': Decimal('8.00'),
                'estoque_minimo': Decimal('2.00'),
                'fornecedor': fornecedor,
            },
        )

        ordem, _ = OrdemCompra.objects.update_or_create(
            observacao='E2E Ordem Aprovada',
            defaults={'fornecedor': fornecedor, 'status': 'APROVADA'},
        )
        ordem.itens.all().delete()
        ItemOrdemCompra.objects.create(
            ordem=ordem,
            produto=produto_ordem,
            quantidade=Decimal('3.00'),
            preco_unitario=Decimal('5.00'),
        )

        self.stdout.write(self.style.SUCCESS('Dados E2E preparados.'))
