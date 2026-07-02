from django.contrib import admin

from .models import Fornecedor, HistoricoPreco, ItemOrdemCompra, LogAcao, Movimentacao, OrdemCompra, Produto


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'telefone')


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'tipo_produto', 'fornecedor', 'quantidade_base', 'preco_custo', 'preco_venda', 'estoque_minimo')
    list_filter = ('tipo_produto', 'fornecedor')
    fieldsets = (
        ('Geral', {'fields': ('descricao', 'tipo_produto', 'fornecedor')}),
        ('Preços', {'fields': ('preco_custo', 'preco_venda')}),
        ('Quantidade', {'fields': ('quantidade_base', 'estoque_minimo')}),
        ('Configurações de Tipo', {
            'fields': ('metros_por_rolo', 'tipo_tinta', 'cor_tinta', 'litros_por_vidro'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ('produto', 'tipo', 'quantidade', 'data', 'observacao')
    list_filter = ('tipo', 'data')


@admin.register(HistoricoPreco)
class HistoricoPrecoAdmin(admin.ModelAdmin):
    list_display = ('produto', 'data', 'preco_custo_antigo', 'preco_custo_novo', 'preco_venda_antigo', 'preco_venda_novo', 'usuario')
    list_filter = ('data',)
    readonly_fields = ('produto', 'preco_custo_antigo', 'preco_custo_novo', 'preco_venda_antigo', 'preco_venda_novo', 'data', 'usuario')


class ItemOrdemCompraInline(admin.TabularInline):
    model = ItemOrdemCompra
    extra = 1


@admin.register(OrdemCompra)
class OrdemCompraAdmin(admin.ModelAdmin):
    list_display = ('id', 'fornecedor', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao')
    inlines = [ItemOrdemCompraInline]


@admin.register(LogAcao)
class LogAcaoAdmin(admin.ModelAdmin):
    list_display = ('data', 'usuario', 'acao', 'descricao', 'modelo')
    list_filter = ('acao', 'data')
    readonly_fields = ('usuario', 'acao', 'descricao', 'modelo', 'objeto_id', 'data')
