from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


class Fornecedor(models.Model):
    nome = models.CharField(max_length=200)
    telefone = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.nome


class Produto(models.Model):
    TIPO_PRODUTO_CHOICES = [
        ('TECIDO', 'Tecido'),
        ('PAPEL', 'Papel'),
        ('TINTA', 'Tinta'),
        ('AVIAMENTO', 'Aviamento'),
        ('OUTRO', 'Outro'),
    ]

    TIPO_TINTA_CHOICES = [
        ('SUBLIMACAO', 'Sublimação'),
        ('SOLVENTE', 'Solvente'),
        ('N/A', 'Não se aplica'),
    ]

    COR_CHOICES = [
        ('CYAN', 'Cyan'),
        ('MAGENTA', 'Magenta'),
        ('YELLOW', 'Yellow'),
        ('BLACK', 'Black (Preto)'),
        ('LIGHT_CYAN', 'Light Cyan'),
        ('LIGHT_MAGENTA', 'Light Magenta'),
        ('BRANCO', 'Branco'),
        ('INCOLOR', 'Incolor/N/A'),
    ]

    tipo_produto = models.CharField(max_length=20, choices=TIPO_PRODUTO_CHOICES, default='OUTRO')
    descricao = models.CharField(max_length=255, verbose_name="Descrição do Material")
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True)

    quantidade_base = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        verbose_name="Quantidade Base (Metros ou Litros)"
    )

    metros_por_rolo = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Se vendido em rolo, quantos metros tem um rolo padrão?"
    )

    tipo_tinta = models.CharField(max_length=20, choices=TIPO_TINTA_CHOICES, default='N/A')
    cor_tinta = models.CharField(max_length=20, choices=COR_CHOICES, default='INCOLOR')
    litros_por_vidro = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Quantos litros vem em um vidro/garrafa padrão?"
    )

    preco_custo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estoque_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        if self.tipo_produto == 'TINTA':
            return f"Tinta {self.get_tipo_tinta_display()} - {self.get_cor_tinta_display()} ({self.descricao})"
        return f"{self.get_tipo_produto_display()} - {self.descricao}"

    @property
    def quantidade_rolos_estimada(self):
        if self.tipo_produto in ['TECIDO', 'PAPEL'] and self.metros_por_rolo and self.metros_por_rolo > 0:
            return round(self.quantidade_base / self.metros_por_rolo, 2)
        return 0

    @property
    def quantidade_vidros_estimada(self):
        if self.tipo_produto == 'TINTA' and self.litros_por_vidro and self.litros_por_vidro > 0:
            return round(self.quantidade_base / self.litros_por_vidro, 2)
        return 0

    @property
    def unidade_medida(self):
        return "Litros" if self.tipo_produto == 'TINTA' else "Metros"


class Movimentacao(models.Model):
    TIPO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    ]

    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='movimentacoes')
    tipo = models.CharField(max_length=7, choices=TIPO_CHOICES)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateTimeField(auto_now_add=True)
    observacao = models.CharField(max_length=255, blank=True, default='')

    def save(self, *args, **kwargs):
        if not self.pk:
            with transaction.atomic():
                produto = Produto.objects.select_for_update().get(pk=self.produto.pk)
                if self.tipo == 'ENTRADA':
                    produto.quantidade_base += self.quantidade
                elif self.tipo == 'SAIDA':
                    if produto.quantidade_base < self.quantidade:
                        raise ValidationError(
                            f'Quantidade indisponível em estoque. '
                            f'Disponível: {produto.quantidade_base}, solicitado: {self.quantidade}'
                        )
                    produto.quantidade_base -= self.quantidade
                produto.save()
                self.produto = produto
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.produto.descricao} ({self.quantidade})'


class HistoricoPreco(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='historico_precos')
    preco_custo_antigo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    preco_custo_novo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    preco_venda_antigo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    preco_venda_novo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    data = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-data']

    def __str__(self):
        return f'[{self.data:%d/%m/%Y %H:%M}] {self.produto.descricao}'


class OrdemCompra(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('APROVADA', 'Aprovada'),
        ('RECEBIDA', 'Recebida'),
        ('CANCELADA', 'Cancelada'),
    ]

    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    observacao = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-data_criacao']

    def __str__(self):
        return f'Ordem #{self.id} - {self.get_status_display()}'


class ItemOrdemCompra(models.Model):
    ordem = models.ForeignKey(OrdemCompra, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.produto.descricao} x {self.quantidade}'


class LogAcao(models.Model):
    ACAO_CHOICES = [
        ('CRIAR', 'Criação'),
        ('EDITAR', 'Edição'),
        ('EXCLUIR', 'Exclusão'),
        ('ENTRADA', 'Entrada Estoque'),
        ('SAIDA', 'Saída Estoque'),
        ('APROVAR', 'Aprovação'),
        ('CANCELAR', 'Cancelamento'),
        ('RECEBER', 'Recebimento'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    acao = models.CharField(max_length=20, choices=ACAO_CHOICES)
    descricao = models.CharField(max_length=500)
    modelo = models.CharField(max_length=50, blank=True, default='')
    objeto_id = models.PositiveIntegerField(null=True, blank=True)
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data']

    def __str__(self):
        return f'[{self.data:%d/%m/%Y %H:%M}] {self.usuario} - {self.acao}: {self.descricao[:50]}'
