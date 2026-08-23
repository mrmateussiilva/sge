from django.contrib import admin

from .models import Fornecedor, HistoricoPreco, ItemOrdemCompra, LogAcao, Movimentacao, OrdemCompra, Produto


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'telefone')


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'tipo_produto', 'fornecedor', 'quantidade_base', 'preco_custo', 'preco_venda', 'estoque_minimo')
    list_filter = ('tipo_produto', 'fornecedor')
    readonly_fields = ('quantidade_base',)
    fieldsets = (
        ('Geral', {'fields': ('descricao', 'tipo_produto', 'fornecedor')}),
        ('Preços', {'fields': ('preco_custo', 'preco_venda')}),
        ('Quantidade', {'fields': ('quantidade_base', 'estoque_minimo')}),
        ('Configurações de Tipo', {
            'fields': ('metros_por_rolo', 'tipo_tinta', 'cor_tinta', 'litros_por_vidro'),
            'classes': ('collapse',),
        }),
    )

    def has_delete_permission(self, request, obj=None):
        # A exclusão pelo Admin poderia apagar a trilha de movimentações em
        # cascata e deixar o saldo histórico sem explicação.
        return False


@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ('produto', 'tipo', 'quantidade', 'data', 'observacao')
    list_filter = ('tipo', 'data')
    readonly_fields = ('produto', 'usuario', 'tipo', 'quantidade', 'data', 'observacao')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.status != 'PENDENTE':
            return False
        return super().has_change_permission(request, obj)


@admin.register(LogAcao)
class LogAcaoAdmin(admin.ModelAdmin):
    list_display = ('data', 'usuario', 'acao', 'descricao', 'modelo')
    list_filter = ('acao', 'data')
    readonly_fields = ('usuario', 'acao', 'descricao', 'modelo', 'objeto_id', 'data')
