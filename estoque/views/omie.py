import json
import logging
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render

from ..log_utils import log_acao
from ..models import ConfiguracaoOmie, ImportacaoNFe, Movimentacao, Produto
from ..services.omie_client import OmieAPIError, OmieClient, OmieConfigError
from .helpers import exigir_admin_json, json_erro, json_ok


@login_required
def buscar_notas_omie(request):
    """
    Exibe a lista de Notas de Entrada do Omie e permite ao usuário
    importá-las como movimentações de ENTRADA no estoque.

    GET: Lista notas do Omie (com paginação e busca por fornecedor/data), marcando quais já foram importadas.
    """
    pagina = int(request.GET.get('pagina', 1))
    busca = request.GET.get('q', '').strip()
    cnpj_fornecedor = request.GET.get('cnpj', '').strip()
    data_inicio = request.GET.get('data_inicio', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()

    erro = None
    notas = []
    total_paginas = 1
    total_registros = 0
    ja_importados = set()
    config_omie = ConfiguracaoOmie.objects.first()

    try:
        client = OmieClient()
        notas, total_paginas, total_registros = client.listar_notas_parseadas(
            pagina=pagina,
            registros_por_pagina=20,
            cnpj_fornecedor=cnpj_fornecedor,
            data_inicio=data_inicio,
            data_fim=data_fim,
            ordenar_decrescente=True,
        )

        if busca:
            q_lower = busca.lower()
            notas = [
                n for n in notas
                if q_lower in n.fornecedor_nome.lower()
                or q_lower in n.fornecedor_cnpj.lower()
                or q_lower in n.numero_nfe.lower()
                or any(q_lower in item.descricao.lower() for item in n.itens)
            ]

        ids_notas = {n.n_cod_nota_ent for n in notas}
        ja_importados = set(
            ImportacaoNFe.objects.filter(
                n_cod_nota_ent__in=ids_notas
            ).values_list('n_cod_nota_ent', flat=True)
        )
    except OmieConfigError as exc:
        erro = f'Credenciais Omie não configuradas: {exc}'
    except OmieAPIError as exc:
        erro = f'Erro na API Omie [{exc.codigo}]: {exc.descricao}'
    except Exception as exc:
        erro = f'Erro inesperado ao conectar ao Omie: {exc}'

    produtos_sge = list(
        Produto.objects.order_by('descricao').values('id', 'descricao', 'unidade_medida')
    )

    return render(request, 'estoque/omie_notas.html', {
        'notas': notas,
        'ja_importados': ja_importados,
        'erro': erro,
        'pagina': pagina,
        'busca': busca,
        'cnpj_fornecedor': cnpj_fornecedor,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'total_paginas': total_paginas,
        'total_registros': total_registros,
        'produtos_sge_json': json.dumps(produtos_sge),
        'config_omie': config_omie,
    })


@login_required
def salvar_configuracao_omie(request):
    """
    POST: Salva ou atualiza a App Key e o App Secret do Omie no banco de dados (ConfiguracaoOmie).
    Apenas administradores podem alterar.
    """
    if request.method != 'POST':
        return json_erro('Método não permitido.', status=405)

    perm_error = exigir_admin_json(request)
    if perm_error:
        return perm_error

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return json_erro('JSON inválido.')

    app_key = data.get('app_key', '').strip().strip('"\':')
    app_secret = data.get('app_secret', '').strip().strip('"\':')

    if not app_key or not app_secret:
        return json_erro('App Key e App Secret são obrigatórios.')

    if len(app_secret) == 32 and app_secret[0] in ('O', 'o'):
        import re
        if re.match(r'^[0-9a-fA-F]{31}$', app_secret[1:]):
            app_secret = '0' + app_secret[1:]

    config, _ = ConfiguracaoOmie.objects.get_or_create(id=1)
    config.app_key = app_key
    config.app_secret = app_secret
    config.usuario = request.user
    config.save()

    log_acao(
        request.user,
        'EDITAR',
        'Atualizou credenciais de API do Omie (App Key e App Secret)',
        'ConfiguracaoOmie',
        config.id,
    )

    return json_ok(mensagem='Credenciais do Omie salvas com sucesso!')


@login_required
def importar_nota_omie(request, n_cod: int):
    """
    POST: Importa uma nota de entrada do Omie gerando Movimentacoes de ENTRADA.
    """
    if request.method != 'POST':
        return json_erro('Método não permitido.', status=405)

    if ImportacaoNFe.objects.filter(n_cod_nota_ent=n_cod).exists():
        return json_erro(
            f'A nota Omie #{n_cod} já foi importada anteriormente.',
            codigo='JA_IMPORTADO',
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return json_erro('JSON inválido.')

    itens = data.get('itens', [])
    if not itens:
        return json_erro('Nenhum item para importar.')

    for item in itens:
        pid = str(item.get('produto_id', ''))
        if not pid or (pid != 'novo' and not item.get('criar_novo') and not pid.isdigit()):
            descricao = item.get('descricao', '?')
            return json_erro(
                f'O item "{descricao}" não tem produto do SGE selecionado.',
                codigo='PRODUTO_NAO_SELECIONADO',
            )

    movimentacoes_criadas = 0
    descricoes_importadas = []

    try:
        with transaction.atomic():
            for item in itens:
                pid = str(item.get('produto_id', ''))
                valor_unitario = item.get('valor_unitario', '0')

                if pid == 'novo' or item.get('criar_novo'):
                    nova_desc = (item.get('novo_descricao') or item.get('descricao') or 'Novo Produto').strip()
                    tipo_prod = item.get('novo_tipo_produto', 'OUTRO')
                    unid = item.get('novo_unidade_medida', 'UN')
                    val_unit_dec = Decimal(str(valor_unitario)) if valor_unitario and Decimal(str(valor_unitario)) > 0 else Decimal('0.00')
                    est_min_raw = item.get('novo_estoque_minimo', '0')
                    est_min_dec = Decimal(str(est_min_raw)) if est_min_raw else Decimal('0.00')

                    produto = Produto.objects.create(
                        descricao=nova_desc,
                        tipo_produto=tipo_prod,
                        unidade_medida=unid,
                        quantidade_base=Decimal('0.00'),
                        preco_custo=val_unit_dec,
                        preco_venda=Decimal('0.00'),
                        estoque_minimo=est_min_dec,
                    )
                    log_acao(
                        request.user,
                        'CRIAR',
                        f'Produto "{produto.descricao}" cadastrado via importação NF-e Omie #{n_cod}',
                        'Produto',
                        produto.id,
                    )
                else:
                    produto = Produto.objects.select_for_update().get(pk=item['produto_id'])

                quantidade = Decimal(str(item.get('quantidade', '0')))
                if quantidade <= 0:
                    raise ValidationError(f'Quantidade inválida para "{produto.descricao}".')

                obs = (
                    f'Importado da NF-e Omie #{n_cod} | '
                    f'{item.get("descricao", "")} | '
                    f'Qtde: {quantidade} | '
                    f'Valor unit.: R$ {valor_unitario}'
                )

                Movimentacao.objects.create(
                    produto=produto,
                    usuario=request.user,
                    tipo='ENTRADA',
                    quantidade=quantidade,
                    observacao=obs[:255],
                )
                if str(item.get('produto_id', '')) != 'novo' and not item.get('criar_novo'):
                    if valor_unitario and Decimal(str(valor_unitario)) > 0:
                        produto.preco_custo = Decimal(str(valor_unitario))
                        produto.save(update_fields=['preco_custo'])

                movimentacoes_criadas += 1
                descricoes_importadas.append(produto.descricao)

            ImportacaoNFe.objects.create(
                n_cod_nota_ent=n_cod,
                cod_int_nota_ent=data.get('cod_int_nota_ent', ''),
                numero_nfe=data.get('numero_nfe', ''),
                fornecedor_nome=data.get('fornecedor_nome', ''),
                usuario=request.user,
                observacao=f'{movimentacoes_criadas} itens importados',
            )

        log_acao(
            request.user,
            'ENTRADA',
            (
                f'Importação NF-e Omie #{n_cod} — '
                f'{movimentacoes_criadas} movimentação(ões) criada(s): '
                f'{", ".join(descricoes_importadas[:5])}'
                + ('...' if len(descricoes_importadas) > 5 else '')
            ),
            'ImportacaoNFe',
        )

        return json_ok(
            mensagem=f'{movimentacoes_criadas} entrada(s) registrada(s) com sucesso!',
            movimentacoes_criadas=movimentacoes_criadas,
        )

    except Produto.DoesNotExist:
        return json_erro('Produto SGE não encontrado.', status=404)
    except ValidationError as exc:
        return json_erro('; '.join(exc.messages), codigo='VALIDACAO')
    except (InvalidOperation, TypeError, ValueError) as exc:
        return json_erro(f'Valor inválido: {exc}', codigo='VALIDACAO')
    except OmieConfigError as exc:
        return json_erro(str(exc), codigo='CONFIG_ERROR', status=500)
    except Exception as exc:
        logger_omie = logging.getLogger(__name__)
        logger_omie.exception('Erro ao importar nota Omie #%s', n_cod)
        return json_erro(f'Erro interno: {exc}', status=500)
