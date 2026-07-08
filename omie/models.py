from django.conf import settings
from django.db import models, transaction
from omie.crypto import encrypt_secret, decrypt_secret


class OmieConfig(models.Model):
    AMBIENTE_CHOICES = [
        ('PRODUCAO', 'Produção'),
        ('HOMOLOGACAO', 'Homologação'),
    ]

    nome = models.CharField(max_length=100, default="Configuração principal")
    ativo = models.BooleanField(default=True)
    app_key = models.CharField(max_length=100)
    app_secret_encrypted = models.TextField(blank=True, default="")
    ambiente = models.CharField(max_length=20, choices=AMBIENTE_CHOICES, default='PRODUCAO')
    ultima_sincronizacao = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração Omie'
        verbose_name_plural = 'Configurações Omie'

    def set_app_secret(self, secret: str):
        self.app_secret_encrypted = encrypt_secret(secret)

    def get_app_secret(self) -> str:
        return decrypt_secret(self.app_secret_encrypted)

    def save(self, *args, **kwargs):
        if self.ativo:
            # Desativa outras configurações ativas para garantir apenas uma ativa
            with transaction.atomic():
                OmieConfig.objects.exclude(pk=self.pk).update(ativo=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} - {'Ativa' if self.ativo else 'Inativa'} ({self.ambiente})"


class OmieNotaEntrada(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('APROVADA', 'Aprovada'),
        ('IMPORTADA', 'Importada'),
        ('IGNORADA', 'Ignorada'),
        ('ERRO', 'Erro'),
    ]

    omie_codigo_nota = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    omie_codigo_integracao = models.CharField(max_length=100, null=True, blank=True)
    chave_nfe = models.CharField(max_length=60, null=True, blank=True, unique=True, verbose_name="Chave NF-e")
    numero_nf = models.CharField(max_length=30, null=True, blank=True, verbose_name="Número NF")
    serie = models.CharField(max_length=20, null=True, blank=True, verbose_name="Série")

    fornecedor_nome = models.CharField(max_length=255, blank=True, verbose_name="Nome Fornecedor (Nota)")
    fornecedor_cnpj = models.CharField(max_length=30, blank=True, verbose_name="CNPJ Fornecedor (Nota)")
    fornecedor = models.ForeignKey(
        'estoque.Fornecedor', null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Fornecedor Vinculado"
    )

    data_emissao = models.DateField(null=True, blank=True, verbose_name="Data de Emissão")
    data_entrada = models.DateField(null=True, blank=True, verbose_name="Data de Entrada")
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Valor Total")
    valor_mercadorias = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Valor Mercadorias")

    codigo_omie_fornecedor = models.CharField(max_length=100, null=True, blank=True, verbose_name="Código Fornecedor Omie")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE', db_index=True)
    raw_json = models.JSONField(default=dict, blank=True, verbose_name="JSON Bruto")
    erro = models.TextField(blank=True, default="", verbose_name="Log de Erro")

    aprovado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Aprovado por"
    )
    aprovado_em = models.DateTimeField(null=True, blank=True, verbose_name="Aprovado em")

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_emissao', '-id']
        verbose_name = 'Nota de Entrada Omie'
        verbose_name_plural = 'Notas de Entrada Omie'

    def pode_aprovar(self) -> bool:
        if self.status in ['IMPORTADA', 'APROVADA']:
            return False
        # Para aprovar, todo item não ignorado deve estar associado a um Produto do estoque
        itens = self.itens.all()
        if not itens.exists():
            return False
        for item in itens:
            if item.status != 'IGNORADO' and not item.produto:
                return False
        return True

    def __str__(self):
        numero = self.numero_nf or "S/N"
        fornecedor = self.fornecedor_nome or "Fornecedor Desconhecido"
        return f"Nota NF {numero} - {fornecedor} ({self.get_status_display()})"


class OmieNotaEntradaItem(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('VINCULADO', 'Vinculado'),
        ('IGNORADO', 'Ignorado'),
        ('IMPORTADO', 'Importado'),
        ('ERRO', 'Erro'),
    ]

    nota = models.ForeignKey(OmieNotaEntrada, on_delete=models.CASCADE, related_name='itens')
    sequencia = models.PositiveIntegerField(default=1)

    codigo_produto_omie = models.CharField(max_length=100, blank=True, verbose_name="Cód. Produto Omie")
    codigo_produto_fornecedor = models.CharField(max_length=100, blank=True, verbose_name="Cód. Prod. Fornecedor")
    
    codigo_omie_item = models.CharField(max_length=100, blank=True, verbose_name="Código Item Omie")
    codigo_omie_produto = models.CharField(max_length=100, blank=True, verbose_name="Código Produto Omie")
    codigo_local_estoque_omie = models.CharField(max_length=100, blank=True, verbose_name="Cód. Local Estoque Omie")

    descricao = models.TextField(verbose_name="Descrição do Item")
    ncm = models.CharField(max_length=20, blank=True, verbose_name="NCM")
    cfop = models.CharField(max_length=20, blank=True, verbose_name="CFOP")

    # Quantidades da Nota
    unidade_nota = models.CharField(max_length=20, blank=True, verbose_name="Unidade Nota")
    quantidade_nota = models.DecimalField(max_digits=14, decimal_places=4, default=0.0000, verbose_name="Qtd. Nota")
    valor_unitario = models.DecimalField(max_digits=14, decimal_places=4, default=0.0000, verbose_name="Val. Unitário")
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Val. Total")

    # Vínculo e Conversão para o Estoque
    produto = models.ForeignKey(
        'estoque.Produto', null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Produto Interno"
    )
    quantidade_convertida = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True,
        verbose_name="Qtd. Convertida"
    )
    unidade_convertida = models.CharField(max_length=20, blank=True, verbose_name="Unidade Convertida")

    # Movimentação do Estoque associada
    movimentacao = models.ForeignKey(
        'estoque.Movimentacao', null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Movimentação Estoque"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE', db_index=True)
    raw_json = models.JSONField(default=dict, blank=True, verbose_name="JSON Item Bruto")
    erro = models.TextField(blank=True, default="", verbose_name="Log de Erro Item")

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sequencia']
        verbose_name = 'Item da Nota de Entrada'
        verbose_name_plural = 'Itens da Nota de Entrada'

    def quantidade_para_entrada(self):
        if self.quantidade_convertida is not None:
            return self.quantidade_convertida
        return self.quantidade_nota

    def esta_pronto_para_importar(self) -> bool:
        if self.status == 'IGNORADO':
            return True
        return self.produto is not None

    def __str__(self):
        return f"Item {self.sequencia} - {self.descricao[:40]} ({self.quantidade_nota} {self.unidade_nota})"


class OmieProdutoMapping(models.Model):
    fornecedor = models.ForeignKey('estoque.Fornecedor', null=True, blank=True, on_delete=models.SET_NULL)
    fornecedor_cnpj = models.CharField(max_length=30, blank=True, db_index=True, verbose_name="CNPJ Fornecedor")

    codigo_produto_omie = models.CharField(max_length=100, blank=True, verbose_name="Cód. Produto Omie")
    codigo_produto_fornecedor = models.CharField(max_length=100, blank=True, verbose_name="Cód. Prod. Fornecedor")
    descricao_fornecedor = models.TextField(blank=True, verbose_name="Descrição do Fornecedor")

    produto = models.ForeignKey('estoque.Produto', on_delete=models.CASCADE, verbose_name="Produto Interno")
    unidade_nota = models.CharField(max_length=20, blank=True, verbose_name="Unidade Nota")
    fator_conversao_para_base = models.DecimalField(
        max_digits=14, decimal_places=6, default=1.000000,
        verbose_name="Fator de Conversão",
        help_text="Multiplicador para converter a unidade da nota para a unidade base do produto. Ex: se a nota vem em caixas de 50 metros, e a base é Metros, o fator é 50."
    )

    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('fornecedor_cnpj', 'codigo_produto_omie', 'codigo_produto_fornecedor')
        verbose_name = 'Mapeamento de Produto Omie'
        verbose_name_plural = 'Mapeamentos de Produtos Omie'

    def __str__(self):
        fornecedor = self.fornecedor.nome if self.fornecedor else self.fornecedor_cnpj
        return f"Map: {fornecedor} -> {self.produto.descricao}"
