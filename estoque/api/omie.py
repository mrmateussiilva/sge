import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db import transaction
from django.db.models import Q

from ..log_utils import log_acao
from ..models import (
    ConfiguracaoOmie,
    Fornecedor,
    HistoricoPreco,
    ImportacaoNFe,
    Movimentacao,
    Produto,
)
from ..services.omie_client import OmieAPIError, OmieClient, OmieConfigError, limpar_cnpj
from ..views.helpers import exigir_admin_json, json_erro, json_ok

logger = logging.getLogger(__name__)


def _formatar_data_omie(data_str: str) -> str:
    """Converte datas em formato ISO (YYYY-MM-DD) ou DD/MM/AAAA para DD/MM/AAAA exigido pela Omie."""
    if not data_str:
        return ''
    data_str = data_str.strip()
    if '-' in data_str:
        try:
            return datetime.strptime(data_str, '%Y-%m-%d').strftime('%d/%m/%Y')
        except ValueError:
            pass
    return data_str


@login_required
def listar_notas_omie_api(request):
    """
    Retorna as notas fiscais de fornecedores (NF-e Modelo 55) capturadas pela Omie
    para o período solicitado, com filtros, estatísticas e status de importação.
    """
    hoje = datetime.now(ZoneInfo('America/Sao_Paulo')).date()

    dias_param = request.GET.get('dias')
    try:
        dias = int(dias_param) if dias_param else 30
    except (ValueError, TypeError):
        dias = 30

    data_inicio_raw = request.GET.get('data_inicio', '').strip()
    data_fim_raw = request.GET.get('data_fim', '').strip()

    if data_inicio_raw:
        dt_inicio = _formatar_data_omie(data_inicio_raw)
    else:
        dt_inicio = (hoje - timedelta(days=dias)).strftime('%d/%m/%Y')

    if data_fim_raw:
        dt_fim = _formatar_data_omie(data_fim_raw)
    else:
        dt_fim = hoje.strftime('%d/%m/%Y')

    busca = (request.GET.get('q') or request.GET.get('busca') or '').strip()
    apenas_fornecedores = request.GET.get('apenas_fornecedores', 'true').lower() in ('true', '1', 's', 'sim')

    try:
        client = OmieClient()
        resumo = client.listar_recebimentos_fornecedores_periodo(
            dt_inicio=dt_inicio,
            dt_fim=dt_fim,
            apenas_fornecedores=apenas_fornecedores,
            incluir_detalhes=True,
        )
    except OmieConfigError as exc:
        return json_erro(
            str(exc) or 'Credenciais da API Omie não configuradas.',
            codigo='OMIE_NAO_CONFIGURADO',
            status=400,
        )
    except OmieAPIError as exc:
        logger.warning('Falha na API Omie [%s]: %s', exc.codigo, exc.descricao)
        return json_erro(
            f'Erro ao consultar Omie: {exc.descricao}',
            codigo='OMIE_API_ERROR',
            status=502,
        )
    except Exception as exc:
        logger.exception('Erro inesperado ao consultar recebimentos da Omie: %s', exc)
        return json_erro(
            f'Não foi possível consultar os recebimentos no Omie: {exc}',
            codigo='OMIE_ERRO_INTERNO',
            status=500,
        )

    todas_notas = resumo.get('notas', [])

    # Identificar quais notas já foram importadas no SGE
    ids_receb = [n['id_receb'] for n in todas_notas if n.get('id_receb')]
    importadas_ids = set(
        ImportacaoNFe.objects.filter(
            n_cod_nota_ent__in=ids_receb
        ).values_list('n_cod_nota_ent', flat=True)
    )

    for n in todas_notas:
        n['ja_importada'] = n.get('id_receb') in importadas_ids

    # Filtro textual em memória (fornecedor, razão social, CNPJ, número NF-e, chave ou produtos)
    if busca:
        q_lower = busca.lower()

        def _corresponde(n):
            if q_lower in n.get('numero_nfe', '').lower():
                return True
            if q_lower in n.get('chave_nfe', '').lower():
                return True
            if q_lower in n.get('fornecedor_nome', '').lower():
                return True
            if q_lower in n.get('fornecedor_razao', '').lower():
                return True
            if q_lower in n.get('fornecedor_cnpj', '').lower():
                return True
            for it in n.get('itens', []):
                if q_lower in it.get('descricao', '').lower():
                    return True
                if q_lower in it.get('codigo_produto', '').lower():
                    return True
            return False

        notas_filtradas = [n for n in todas_notas if _corresponde(n)]
    else:
        notas_filtradas = todas_notas

    # Cálculo dos KPIs consolidados
    total_notas = len(notas_filtradas)
    valor_total = sum(n.get('valor_total', 0) for n in notas_filtradas)
    fornecedores_unicos = len(
        {n.get('fornecedor_cnpj') or n.get('fornecedor_nome') for n in notas_filtradas if n.get('fornecedor_cnpj') or n.get('fornecedor_nome')}
    )
    ticket_medio = (valor_total / total_notas) if total_notas > 0 else 0.0

    # Top fornecedores por valor total
    mapa_forn = {}
    for n in notas_filtradas:
        nome = n.get('fornecedor_nome') or n.get('fornecedor_razao') or 'Outro'
        mapa_forn[nome] = mapa_forn.get(nome, 0.0) + n.get('valor_total', 0.0)

    top_fornecedores = sorted(
        [{'nome': k, 'total': round(v, 2)} for k, v in mapa_forn.items()],
        key=lambda x: x['total'],
        reverse=True,
    )[:5]

    # Timeline de evolução de compras por data
    mapa_datas = {}
    for n in notas_filtradas:
        d = n.get('data_emissao')
        if d:
            mapa_datas[d] = mapa_datas.get(d, 0.0) + n.get('valor_total', 0.0)

    def _chave_timeline(item):
        try:
            return datetime.strptime(item[0], '%d/%m/%Y').date()
        except Exception:
            return datetime.min.date()

    timeline = [
        {'data': k, 'total': round(v, 2)}
        for k, v in sorted(mapa_datas.items(), key=_chave_timeline)
    ]

    return json_ok(
        notas=notas_filtradas,
        kpis={
            'total_notas': total_notas,
            'valor_total': round(valor_total, 2),
            'fornecedores_ativos': fornecedores_unicos,
            'ticket_medio': round(ticket_medio, 2),
        },
        periodo={
            'inicio': dt_inicio,
            'fim': dt_fim,
            'dias': dias,
        },
        top_fornecedores=top_fornecedores,
        timeline=timeline,
        total_sem_filtro_busca=len(todas_notas),
    )


@login_required
def consultar_configuracao_omie_api(request):
    try:
        cfg = ConfiguracaoOmie.objects.first()
        app_key = cfg.app_key if cfg and cfg.app_key else getattr(settings, 'OMIE_APP_KEY', '')
        app_secret = cfg.app_secret if cfg and cfg.app_secret else getattr(settings, 'OMIE_APP_SECRET', '')
    except Exception as exc:
        logger.warning('Erro ao consultar ConfiguracaoOmie: %s', exc)
        cfg = None
        app_key = getattr(settings, 'OMIE_APP_KEY', '')
        app_secret = getattr(settings, 'OMIE_APP_SECRET', '')

    configurado = bool(app_key and app_secret)
    app_key_mascarada = ''
    if app_key:
        if len(app_key) > 6:
            app_key_mascarada = f'{app_key[:4]}...{app_key[-2:]}'
        else:
            app_key_mascarada = '******'

    return json_ok(
        configurado=configurado,
        app_key_mascarada=app_key_mascarada,
        atualizado_em=cfg.atualizado_em.strftime('%d/%m/%Y %H:%M') if cfg and cfg.atualizado_em else None,
        cnpj_proprio=getattr(settings, 'OMIE_CNPJ_PROPRIO', '06098674000157'),
        is_admin=request.user.is_superuser,
    )


@login_required
def salvar_configuracao_omie_api(request):
    """Atualiza as credenciais da Omie (apenas administradores)."""
    if request.method != 'POST':
        return json_erro('Método não permitido.', status=405)

    perm_error = exigir_admin_json(request)
    if perm_error:
        return perm_error

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return json_erro('JSON inválido.')

    app_key = str(data.get('app_key', '')).strip().strip('"\':')
    app_secret = str(data.get('app_secret', '')).strip().strip('"\':')

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
        return json_erro('App Key e App Secret são obrigatórios.')

    config.app_key = app_key
    config.app_secret = app_secret
    config.usuario = request.user
    config.save()

    log_acao(
        request.user,
        'EDITAR',
        'Atualizou credenciais de API do Omie via painel web',
        'ConfiguracaoOmie',
        config.id,
    )

    return json_ok(mensagem='Credenciais da Omie salvas com sucesso!')


@login_required
def importar_nota_omie_api(request, id_receb: int):
    """
    Importa itens selecionados de uma NF-e da Omie (Recebimento) para o SGE:
    - Mescla itens com produtos existentes (com atualização opcional de preço de custo)
    - Cadastra novos produtos se solicitado
    - Cria movimentações oficiais de ENTRADA (motivo: COMPRA)
    - Salva controle de idempotência (ImportacaoNFe) e registra auditoria (log_acao)
    """
    if request.method != 'POST':
        return json_erro('Método não permitido.', status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return json_erro('JSON inválido.')

    if ImportacaoNFe.objects.filter(n_cod_nota_ent=id_receb).exists():
        return json_erro(
            f'A NF-e com ID #{id_receb} já foi importada anteriormente no SGE.',
            codigo='JA_IMPORTADO',
            status=400,
        )

    itens = data.get('itens', [])
    if not itens:
        return json_erro('Nenhum item selecionado para importação.')

    numero_nfe = str(data.get('numero_nfe', '')).strip()
    fornecedor_nome = str(data.get('fornecedor_nome', '')).strip()
    fornecedor_cnpj = str(data.get('fornecedor_cnpj', '')).strip()
    chave_nfe = str(data.get('chave_nfe', '')).strip()

    # Tentar localizar ou criar Fornecedor correspondente no SGE
    fornecedor_obj = None
    if fornecedor_cnpj:
        cnpj_limpo = limpar_cnpj(fornecedor_cnpj)
        fornecedor_obj = Fornecedor.objects.filter(cnpj__icontains=cnpj_limpo).first()
    if not fornecedor_obj and fornecedor_nome:
        fornecedor_obj = Fornecedor.objects.filter(nome__iexact=fornecedor_nome).first()
    if not fornecedor_obj and fornecedor_nome:
        try:
            fornecedor_obj = Fornecedor.objects.create(
                nome=fornecedor_nome[:200],
                cnpj=fornecedor_cnpj[:18],
            )
        except Exception:
            fornecedor_obj = None

    movimentacoes_criadas = 0
    descricoes_importadas = []

    try:
        with transaction.atomic():
            if ImportacaoNFe.objects.filter(n_cod_nota_ent=id_receb).exists():
                return json_erro(
                    f'A NF-e #{id_receb} já foi importada anteriormente.',
                    codigo='JA_IMPORTADO',
                    status=400,
                )

            for it in itens:
                acao = it.get('acao', 'vincular')
                qtd_raw = it.get('quantidade')
                try:
                    qtd_dec = Decimal(str(qtd_raw))
                except (InvalidOperation, TypeError, ValueError):
                    return json_erro(f'Quantidade inválida para o item "{it.get("descricao_omie", "")}".')

                if qtd_dec <= 0:
                    return json_erro(f'Quantidade deve ser maior que zero para o item "{it.get("descricao_omie", "")}".')

                val_unit_raw = it.get('valor_unitario')
                try:
                    val_unit_dec = Decimal(str(val_unit_raw)) if val_unit_raw is not None else Decimal('0.00')
                except (InvalidOperation, TypeError, ValueError):
                    val_unit_dec = Decimal('0.00')

                if acao == 'criar':
                    np_data = it.get('novo_produto') or {}
                    desc = (np_data.get('descricao') or it.get('descricao_omie') or 'Novo Insumo').strip()
                    tipo_prod = np_data.get('tipo_produto', 'OUTRO')
                    unid = np_data.get('unidade_medida', 'UN')
                    est_min_raw = np_data.get('estoque_minimo')
                    try:
                        est_min = Decimal(str(est_min_raw)) if est_min_raw not in (None, '') else None
                    except (InvalidOperation, TypeError, ValueError):
                        est_min = None

                    produto = Produto(
                        descricao=desc,
                        tipo_produto=tipo_prod,
                        unidade_medida=unid,
                        quantidade_base=Decimal('0.00'),
                        preco_custo=val_unit_dec if val_unit_dec > 0 else None,
                        estoque_minimo=est_min,
                        fornecedor=fornecedor_obj,
                    )
                    produto.full_clean()
                    produto.save()

                    log_acao(
                        request.user,
                        'CRIAR',
                        f'Produto "{produto.descricao}" cadastrado via importação NF-e #{numero_nfe or id_receb}',
                        'Produto',
                        produto.id,
                    )
                else:
                    prod_id = it.get('produto_id')
                    if not prod_id:
                        return json_erro(f'Selecione um produto do SGE para o item "{it.get("descricao_omie", "")}".')
                    try:
                        produto = Produto.objects.select_for_update().get(pk=prod_id)
                    except Produto.DoesNotExist:
                        return json_erro(f'Produto #{prod_id} não encontrado no SGE.', status=404)

                    # Atualizar preço de custo se marcado
                    if it.get('atualizar_custo') and val_unit_dec > 0 and produto.preco_custo != val_unit_dec:
                        custo_antigo = produto.preco_custo
                        produto.preco_custo = val_unit_dec
                        produto.save(update_fields=['preco_custo'])
                        HistoricoPreco.objects.create(
                            produto=produto,
                            preco_custo_antigo=custo_antigo,
                            preco_custo_novo=val_unit_dec,
                            usuario=request.user,
                        )

                # Registrar Movimentacao de Entrada
                obs = f'Importado da NF-e nº {numero_nfe or id_receb} ({fornecedor_nome}) | {it.get("descricao_omie", "")}'
                Movimentacao.objects.create(
                    produto=produto,
                    usuario=request.user,
                    tipo='ENTRADA',
                    motivo='COMPRA',
                    quantidade=qtd_dec,
                    observacao=obs[:255],
                )

                movimentacoes_criadas += 1
                descricoes_importadas.append(f'{produto.descricao} (+{qtd_dec})')

            # Registrar controle de NF-e importada
            ImportacaoNFe.objects.create(
                n_cod_nota_ent=id_receb,
                numero_nfe=numero_nfe,
                fornecedor_nome=fornecedor_nome,
                usuario=request.user,
                observacao=f'{movimentacoes_criadas} item(ns) importado(s) via conciliação web',
            )

            log_acao(
                request.user,
                'ENTRADA',
                (
                    f'Importação NF-e {numero_nfe or id_receb} ({fornecedor_nome}) — '
                    f'{movimentacoes_criadas} entrada(s): {", ".join(descricoes_importadas[:5])}'
                    + ('...' if len(descricoes_importadas) > 5 else '')
                ),
                'ImportacaoNFe',
                id_receb,
            )

        return json_ok(
            mensagem=f'{movimentacoes_criadas} entrada(s) de estoque registrada(s) com sucesso!',
            movimentacoes_criadas=movimentacoes_criadas,
        )
    except Exception as exc:
        logger.exception('Erro ao importar itens da NF-e Omie: %s', exc)
        return json_erro(f'Falha ao importar itens da NF-e: {exc}')

