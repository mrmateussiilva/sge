import datetime
import decimal
from django import forms
from django.contrib import admin
from django.contrib import messages
from django.db import transaction

from omie.models import OmieConfig, OmieNotaEntrada, OmieNotaEntradaItem, OmieProdutoMapping
from omie.services import testar_conexao, sincronizar_notas_entrada, aprovar_nota_entrada


class OmieConfigForm(forms.ModelForm):
    app_secret = forms.CharField(
        widget=forms.PasswordInput(render_value=False),
        required=False,
        label="App Secret (Senha da API)",
        help_text="Insira a chave secreta (App Secret) da Omie. Deixe em branco para manter o valor atual já salvo."
    )

    class Meta:
        model = OmieConfig
        fields = ['nome', 'ativo', 'app_key', 'app_secret', 'ambiente', 'ultima_sincronizacao']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['app_secret'].required = False
        else:
            self.fields['app_secret'].required = True

    def save(self, commit=True):
        instance = super().save(commit=False)
        app_secret_val = self.cleaned_data.get('app_secret')
        if app_secret_val:
            instance.set_app_secret(app_secret_val)
        if commit:
            instance.save()
        return instance


@admin.register(OmieConfig)
class OmieConfigAdmin(admin.ModelAdmin):
    form = OmieConfigForm
    list_display = ('nome', 'ativo', 'app_key', 'ambiente', 'ultima_sincronizacao', 'atualizado_em')
    readonly_fields = ('ultima_sincronizacao', 'criado_em', 'atualizado_em')
    actions = ['testar_conexao_action']

    @admin.action(description="Testar conexão com a API Omie")
    def testar_conexao_action(self, request, queryset):
        erros = 0
        sucessos = 0
        for config in queryset:
            try:
                testar_conexao(config)
                self.message_user(request, f"Conexão com '{config.nome}' realizada com sucesso!", level=messages.SUCCESS)
                sucessos += 1
            except Exception as e:
                self.message_user(request, f"Falha de conexão com '{config.nome}': {e}", level=messages.ERROR)
                erros += 1


class OmieNotaEntradaItemInline(admin.TabularInline):
    model = OmieNotaEntradaItem
    extra = 0
    can_delete = False

    # Campos editáveis pelo usuário no admin para fazer o vínculo
    fields = ('sequencia', 'descricao', 'unidade_nota', 'quantidade_nota', 'produto', 'quantidade_convertida', 'unidade_convertida', 'status', 'movimentacao')
    
    # Campos que devem ser apenas leitura para não serem alterados pelo usuário
    readonly_fields = ('sequencia', 'descricao', 'unidade_nota', 'quantidade_nota', 'movimentacao')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(OmieNotaEntrada)
class OmieNotaEntradaAdmin(admin.ModelAdmin):
    list_display = (
        'numero_nf', 'serie', 'fornecedor_nome', 'fornecedor_cnpj',
        'data_emissao', 'valor_total', 'status', 'criado_em',
        'aprovado_por', 'aprovado_em'
    )
    list_filter = ('status', 'data_emissao', 'criado_em')
    search_fields = ('numero_nf', 'chave_nfe', 'fornecedor_nome', 'fornecedor_cnpj')
    readonly_fields = ('raw_json', 'aprovado_por', 'aprovado_em', 'criado_em', 'atualizado_em')
    inlines = [OmieNotaEntradaItemInline]
    actions = [
        'sincronizar_notas_action',
        'aprovar_notas_action',
        'ignorar_notas_action',
        'criar_mapeamento_action'
    ]

    @admin.action(description="Sincronizar notas da Omie (últimos 7 dias)")
    def sincronizar_notas_action(self, request, queryset):
        config = OmieConfig.objects.filter(ativo=True).first()
        if not config:
            self.message_user(request, "Nenhuma configuração ativa do Omie encontrada no sistema.", level=messages.ERROR)
            return

        hoje = datetime.date.today()
        uma_semana_atras = hoje - datetime.timedelta(days=7)

        try:
            resumo = sincronizar_notas_entrada(config, data_inicial=uma_semana_atras, data_final=hoje, usuario=request.user)
            self.message_user(
                request,
                f"Sincronização concluída com sucesso: {resumo['criadas']} notas criadas, {resumo['atualizadas']} atualizadas, {resumo['erros']} erros.",
                level=messages.SUCCESS
            )
        except Exception as e:
            self.message_user(request, f"Erro durante a sincronização: {e}", level=messages.ERROR)

    @admin.action(description="Aprovar e Importar notas para o estoque")
    def aprovar_notas_action(self, request, queryset):
        sucesso_count = 0
        erros_count = 0
        for nota in queryset:
            try:
                res = aprovar_nota_entrada(nota, request.user)
                if res.get("sucesso"):
                    sucesso_count += 1
            except Exception as e:
                # Grava o erro no log do modelo para inspeção do usuário
                nota.status = 'ERRO'
                nota.erro = str(e)
                nota.save(update_fields=['status', 'erro'])
                erros_count += 1
                self.message_user(request, f"Erro ao aprovar a Nota Fiscal #{nota.numero_nf or nota.id}: {e}", level=messages.ERROR)

        if sucesso_count:
            self.message_user(request, f"{sucesso_count} nota(s) aprovada(s) e movimentada(s) no estoque com sucesso.", level=messages.SUCCESS)
        if erros_count:
            self.message_user(request, f"{erros_count} nota(s) falharam na aprovação. Consulte a coluna Log de Erro na nota.", level=messages.WARNING)

    @admin.action(description="Marcar notas como Ignoradas")
    def ignorar_notas_action(self, request, queryset):
        with transaction.atomic():
            updated = 0
            for nota in queryset:
                if nota.status not in ['IMPORTADA', 'APROVADA']:
                    nota.status = 'IGNORADA'
                    nota.save(update_fields=['status'])
                    nota.itens.filter(status__in=['PENDENTE', 'VINCULADO']).update(status='IGNORADO')
                    updated += 1
            self.message_user(request, f"{updated} nota(s) marcada(s) como ignorada(s).", level=messages.SUCCESS)

    @admin.action(description="Criar mapeamento de produtos a partir dos vínculos atuais")
    def criar_mapeamento_action(self, request, queryset):
        criados = 0
        for nota in queryset:
            for item in nota.itens.all():
                if item.produto and nota.fornecedor_cnpj:
                    fator = decimal.Decimal("1.000000")
                    if item.quantidade_convertida is not None and item.quantidade_nota > 0:
                        fator = item.quantidade_convertida / item.quantidade_nota

                    obj, created = OmieProdutoMapping.objects.get_or_create(
                        fornecedor_cnpj=nota.fornecedor_cnpj,
                        codigo_produto_omie=item.codigo_produto_omie,
                        codigo_produto_fornecedor=item.codigo_produto_fornecedor,
                        defaults={
                            'fornecedor': nota.fornecedor,
                            'descricao_fornecedor': item.descricao,
                            'produto': item.produto,
                            'unidade_nota': item.unidade_nota,
                            'fator_conversao_para_base': fator,
                            'ativo': True
                        }
                    )
                    if created:
                        criados += 1
        self.message_user(request, f"{criados} novos mapeamentos de produtos criados com sucesso.", level=messages.SUCCESS)


@admin.register(OmieProdutoMapping)
class OmieProdutoMappingAdmin(admin.ModelAdmin):
    list_display = (
        'fornecedor_cnpj', 'fornecedor', 'codigo_produto_omie',
        'codigo_produto_fornecedor', 'produto', 'unidade_nota',
        'fator_conversao_para_base', 'ativo'
    )
    list_filter = ('ativo', 'unidade_nota')
    search_fields = ('fornecedor_cnpj', 'codigo_produto_omie', 'codigo_produto_fornecedor', 'descricao_fornecedor', 'produto__descricao')
