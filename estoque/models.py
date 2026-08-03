import calendar
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True, default='')
    cor = models.CharField(max_length=7, default='#6c757d', help_text='Cor em hex, ex: #ff5733')

    class Meta:
        ordering = ['nome']
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'

    def __str__(self):
        return self.nome


class Fornecedor(models.Model):
    nome = models.CharField(max_length=200)
    cnpj = models.CharField(max_length=18, blank=True, default='', verbose_name='CNPJ')
    email = models.EmailField(blank=True, default='')
    telefone = models.CharField(max_length=20, null=True, blank=True)
    observacao = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['nome']

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

    UNIDADE_MEDIDA_CHOICES = [
        ('UN', 'Unidade (un)'),
        ('M', 'Metros (m)'),
        ('KG', 'Quilogramas (kg)'),
        ('L', 'Litros (L)'),
        ('RL', 'Rolo (rl)'),
        ('CX', 'Caixa (cx)'),
        ('PC', 'Peça (pc)'),
        ('G', 'Gramas (g)'),
        ('ML', 'Mililitros (ml)'),
        ('OUTRO', 'Outro'),
    ]

    tipo_produto = models.CharField(max_length=20, choices=TIPO_PRODUTO_CHOICES, default='OUTRO')
    unidade_medida = models.CharField(max_length=10, choices=UNIDADE_MEDIDA_CHOICES, default='UN', verbose_name="Unidade de Medida")
    descricao = models.CharField(max_length=255, verbose_name="Descrição do Material")
    categoria = models.ForeignKey(
        'Categoria', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='produtos'
    )
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

    preco_custo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    estoque_minimo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)

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
    def unidade_base_codigo(self):
        from .services.units import unidade_base_codigo
        return unidade_base_codigo(self)

    @property
    def unidade_simbolo(self):
        from .services.units import unidade_simbolo
        return unidade_simbolo(self)

    @property
    def quantidade_formatada(self):
        from .services.units import formatar_quantidade_produto
        return formatar_quantidade_produto(self)

    @property
    def status_estoque(self):
        from .services.estoque_status import classificar_estoque
        return classificar_estoque(self).codigo




class Movimentacao(models.Model):
    TIPO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    ]

    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='movimentacoes')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=7, choices=TIPO_CHOICES)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateTimeField(auto_now_add=True)
    observacao = models.CharField(max_length=255, blank=True, default='')

    def _normalizar_quantidade(self):
        try:
            quantidade = Decimal(str(self.quantidade))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError('Quantidade inválida.')

        if not quantidade.is_finite() or quantidade <= 0:
            raise ValidationError('Quantidade deve ser maior que zero.')

        return quantidade

    def save(self, *args, **kwargs):
        self.quantidade = self._normalizar_quantidade()
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


class FechamentoMensal(models.Model):
    data_fechamento = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    referencia_mes_ano = models.CharField(
        max_length=7,
        unique=True,
        null=True,
        blank=True,
        help_text='Referência legada MM/AAAA, preenchida para períodos mensais completos.',
    )
    observacao = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-data_fechamento']
        constraints = [
            models.UniqueConstraint(
                fields=['data_inicio', 'data_fim'],
                name='fechamento_periodo_unico',
            ),
            models.CheckConstraint(
                condition=models.Q(data_fim__gte=models.F('data_inicio')),
                name='fechamento_periodo_datas_validas',
            ),
        ]

    def clean(self):
        super().clean()
        if self.data_inicio and self.data_fim and self.data_inicio > self.data_fim:
            raise ValidationError({'data_fim': 'A data final deve ser igual ou posterior à data inicial.'})

    def save(self, *args, **kwargs):
        if self.data_inicio and self.data_fim and self.data_inicio > self.data_fim:
            raise ValidationError('A data final deve ser igual ou posterior à data inicial.')
        if self.data_inicio and self.data_fim:
            ultimo_dia = calendar.monthrange(self.data_inicio.year, self.data_inicio.month)[1]
            periodo_mensal_completo = (
                self.data_inicio.day == 1
                and self.data_fim.year == self.data_inicio.year
                and self.data_fim.month == self.data_inicio.month
                and self.data_fim.day == ultimo_dia
            )
            if periodo_mensal_completo:
                self.referencia_mes_ano = self.data_inicio.strftime('%m/%Y')
            else:
                self.referencia_mes_ano = None
        super().save(*args, **kwargs)

    @property
    def periodo_formatado(self):
        return f'{self.data_inicio:%d/%m/%Y} a {self.data_fim:%d/%m/%Y}'

    def __str__(self):
        return f'Fechamento {self.periodo_formatado}'


class ItemFechamento(models.Model):
    fechamento = models.ForeignKey(FechamentoMensal, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.SET_NULL, null=True, blank=True)
    descricao = models.CharField(max_length=255)
    tipo_produto = models.CharField(max_length=20, choices=Produto.TIPO_PRODUTO_CHOICES, blank=True, default='')
    unidade_medida = models.CharField(max_length=10, choices=Produto.UNIDADE_MEDIDA_CHOICES, blank=True, default='')
    categoria_nome = models.CharField(max_length=100, blank=True, default='')
    fornecedor_nome = models.CharField(max_length=200, blank=True, default='')
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    preco_custo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f'{self.descricao} ({self.quantidade})'


class ImportacaoNFe(models.Model):
    """
    Controle de idempotência para importação de Notas de Entrada do Omie.

    Garante que uma nota não seja importada mais de uma vez.
    O campo `n_cod_nota_ent` corresponde ao ID interno do Omie (nCodNotaEnt).
    """

    n_cod_nota_ent = models.BigIntegerField(
        unique=True,
        verbose_name='ID da Nota no Omie',
        help_text='Corresponde ao campo nCodNotaEnt retornado pela API do Omie.',
    )
    cod_int_nota_ent = models.CharField(
        max_length=60, blank=True, default='',
        verbose_name='Código de Integração',
    )
    numero_nfe = models.CharField(max_length=20, blank=True, default='', verbose_name='Número NF-e')
    fornecedor_nome = models.CharField(max_length=200, blank=True, default='', verbose_name='Fornecedor')
    data_importacao = models.DateTimeField(auto_now_add=True, verbose_name='Data da Importação')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Importado por',
    )
    observacao = models.CharField(max_length=500, blank=True, default='')

    class Meta:
        ordering = ['-data_importacao']
        verbose_name = 'Importação de NF-e'
        verbose_name_plural = 'Importações de NF-e'

    def __str__(self):
        return f'NF-e Omie #{self.n_cod_nota_ent} — {self.fornecedor_nome} ({self.data_importacao:%d/%m/%Y})'


class ConfiguracaoOmie(models.Model):
    """
    Guarda as credenciais da API Omie (App Key e App Secret) configuradas via interface.
    """

    app_key = models.CharField(max_length=100, blank=True, default='', verbose_name='App Key Omie')
    app_secret = models.CharField(max_length=100, blank=True, default='', verbose_name='App Secret Omie')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Atualizado por',
    )

    class Meta:
        verbose_name = 'Configuração Omie'
        verbose_name_plural = 'Configurações Omie'

    def __str__(self):
        return f'Configuração Omie (App Key: {self.app_key[:6]}...)'
