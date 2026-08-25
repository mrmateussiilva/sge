import json
import logging
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import render

from ..log_utils import log_acao
from ..models import ConfiguracaoOmie, ImportacaoNFe, Movimentacao, Produto
from ..services.omie_client import OmieAPIError, OmieClient, OmieConfigError
from .helpers import exigir_admin_json, json_erro, json_ok


logger = logging.getLogger(__name__)


@login_required
def buscar_notas_omie(request):
    """
    Exibe a lista de Notas de Entrada do Omie e permite ao usuário
    importá-las como movimentações de ENTRADA no estoque.

    GET: Lista notas do Omie (com paginação e busca por fornecedor/data), marcando quais já foram importadas.
    """
    try:
        pagina = max(int(request.GET.get('pagina', 1)), 1)
    except (TypeError, ValueError):
        pagina = 1
    busca = request.GET.get('q', '').strip()
    cnpj_fornecedor = request.GET.get('cnpj', '').strip()
    data_inicio = request.GET.get('data_inicio', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()

    erro = None
    notas = []
    total_paginas = 1
    total_registros = 0
    ja_importados = set()
    config_omie = ConfiguracaoOmie.objects.first() if request.user.is_superuser else None

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
    except OmieConfigError:
        erro = 'Credenciais Omie não configuradas.'
    except OmieAPIError as exc:
        logger.warning('Falha na API Omie [%s]: %s', exc.codigo, exc.descricao)
        erro = 'Não foi possível consultar as notas no Omie.'
    except Exception:
        logger.exception('Erro inesperado ao consultar notas Omie')
        erro = 'Não foi possível consultar as notas no Omie.'

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

    if len(app_secret) == 32 and app_secret[0] in ('O', 'o'):
        import re
        if re.match(r'^[0-9a-fA-F]{31}$', app_secret[1:]):
            app_secret = '0' + app_secret[1:]

    config, _ = ConfiguracaoOmie.objects.get_or_create(id=1)
    if not app_key:
        app_key = config.app_key
    if not app_secret:
        app_secret = config.app_secret
    if not app_key or not app_secret:
        return json_erro('App Key e App Secret são obrigatórios na primeira configuração.')
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

    perm_error = exigir_admin_json(request)
    if perm_error:
        return perm_error

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return json_erro('JSON inválido.')

    movimentacoes_criadas = 0
    descricoes_importadas = []

    try:
        nota = OmieClient().consultar_nota_parseada(n_cod)
        itens = data.get('itens', [])
        if not itens:
            return json_erro('Nenhum item para importar.')

        itens_fonte = {str(item.cod_item_int): item for item in nota.itens if item.cod_item_int}
        codigos_payload = [str(item.get('cod_item_int', '')) for item in itens]
        if not itens_fonte or len(codigos_payload) != len(set(codigos_payload)):
            return json_erro('A nota retornada pelo Omie possui itens sem identificador único.')
        if set(codigos_payload) != set(itens_fonte):
            return json_erro('Os itens enviados não correspondem à nota confirmada no Omie.')

        for item in itens:
            pid = str(item.get('produto_id', ''))
            if not pid or (pid != 'novo' and not item.get('criar_novo') and not pid.isdigit()):
                descricao = item.get('descricao', '?')
                return json_erro(
                    f'O item "{descricao}" não tem produto do SGE selecionado.',
                    codigo='PRODUTO_NAO_SELECIONADO',
                )

        with transaction.atomic():
            if ImportacaoNFe.objects.filter(n_cod_nota_ent=n_cod).exists():
                return json_erro(
                    f'A nota Omie #{n_cod} já foi importada anteriormente.',
                    codigo='JA_IMPORTADO',
                )

            for item in itens:
                pid = str(item.get('produto_id', ''))
                item_fonte = itens_fonte[str(item['cod_item_int'])]
                quantidade = Decimal(str(item_fonte.quantidade))
                valor_unitario = Decimal(str(item_fonte.valor_unitario))

                if pid == 'novo' or item.get('criar_novo'):
                    nova_desc = (item.get('novo_descricao') or item.get('descricao') or 'Novo Produto').strip()
                    tipo_prod = item.get('novo_tipo_produto', 'OUTRO')
                    unid = item.get('novo_unidade_medida', 'UN')
                    val_unit_dec = valor_unitario if valor_unitario > 0 else Decimal('0.00')
                    est_min_raw = item.get('novo_estoque_minimo', '0')
                    est_min_dec = Decimal(str(est_min_raw)) if est_min_raw else Decimal('0.00')

                    produto = Produto(
                        descricao=nova_desc,
                        tipo_produto=tipo_prod,
                        unidade_medida=unid,
                        quantidade_base=Decimal('0.00'),
                        preco_custo=val_unit_dec,
                        preco_venda=Decimal('0.00'),
                        estoque_minimo=est_min_dec,
                    )
                    produto.full_clean()
                    produto.save()
                    log_acao(
                        request.user,
                        'CRIAR',
                        f'Produto "{produto.descricao}" cadastrado via importação NF-e Omie #{n_cod}',
                        'Produto',
                        produto.id,
                    )
                else:
                    produto = Produto.objects.select_for_update().get(pk=item['produto_id'])

                if quantidade <= 0:
                    raise ValidationError(f'Quantidade inválida para "{produto.descricao}".')

                obs = (
                    f'Importado da NF-e Omie #{n_cod} | '
                    f'{item_fonte.descricao} | '
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
                    if valor_unitario > 0:
                        produto.preco_custo = valor_unitario
                        produto._historico_usuario = request.user
                        produto.save(update_fields=['preco_custo'])

                movimentacoes_criadas += 1
                descricoes_importadas.append(produto.descricao)

            ImportacaoNFe.objects.create(
                n_cod_nota_ent=n_cod,
                cod_int_nota_ent=nota.cod_int_nota_ent,
                numero_nfe=nota.numero_nfe,
                fornecedor_nome=nota.fornecedor_nome,
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
    except OmieConfigError:
        return json_erro('A integração Omie não está configurada.', codigo='CONFIG_ERROR', status=500)
    except (OmieAPIError, OSError):
        return json_erro('Não foi possível confirmar a nota no Omie.', codigo='OMIE_ERROR', status=502)
    except IntegrityError:
        return json_erro(
            f'A nota Omie #{n_cod} já foi importada anteriormente.',
            status=409,
            codigo='JA_IMPORTADO',
        )
    except Exception:
        logger_omie = logging.getLogger(__name__)
        logger_omie.exception('Erro ao importar nota Omie #%s', n_cod)
        return json_erro('Não foi possível concluir a importação.', status=500)
