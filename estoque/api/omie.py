import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..log_utils import log_acao
from ..models import (
    Categoria,
    ConfiguracaoOmie,
    DeParaOmie,
    Fornecedor,
    HistoricoPreco,
    ImportacaoNFe,
    Movimentacao,
    OrdemCompra,
    Produto,
)
from notifications.events import NFE_RECEIVED, notify_nfe_received
from notifications.models import NotificationLog

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
        auto_sync_ativo=cfg.auto_sync_ativo if cfg else True,
        ultimo_sync_em=cfg.ultimo_sync_em.strftime('%d/%m/%Y %H:%M') if cfg and cfg.ultimo_sync_em else None,
        ultimo_sync_status=cfg.ultimo_sync_status if cfg else '',
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
    auto_sync_ativo = data.get('auto_sync_ativo')

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
    if auto_sync_ativo is not None:
        config.auto_sync_ativo = bool(auto_sync_ativo)
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
def consultar_depara_omie_api(request):
    """
    Retorna a memória de De-Para entre itens de fornecedores na Omie e Produtos no SGE.
    Filtra opcionalmente por CNPJ do fornecedor.
    """
    cnpj = limpar_cnpj(request.GET.get('cnpj', ''))
    qs = DeParaOmie.objects.select_related('produto')
    if cnpj:
        qs = qs.filter(fornecedor_cnpj=cnpj)

    mapeamentos = []
    mapa_por_chave = {}
    for item in qs[:300]:
        prod = item.produto
        dado = {
            'id': item.id,
            'fornecedor_cnpj': item.fornecedor_cnpj,
            'fornecedor_nome': item.fornecedor_nome,
            'codigo_produto_fornecedor': item.codigo_produto_fornecedor,
            'descricao_produto_fornecedor': item.descricao_produto_fornecedor,
            'produto_id': prod.id,
            'produto_descricao': prod.descricao,
            'produto_tipo': prod.tipo_produto,
            'produto_unidade': prod.unidade_medida,
            'preco_custo': float(prod.preco_custo or 0),
            'fator_conversao': float(item.fator_conversao or 1.0),
            'atualizado_em': item.atualizado_em.strftime('%d/%m/%Y %H:%M'),
        }
        mapeamentos.append(dado)
        # Chaves de lookup rápido para o frontend
        if item.codigo_produto_fornecedor:
            mapa_por_chave[f'cod:{item.codigo_produto_fornecedor.strip().lower()}'] = dado
        if item.descricao_produto_fornecedor:
            mapa_por_chave[f'desc:{item.descricao_produto_fornecedor.strip().lower()}'] = dado

    return json_ok(
        mapeamentos=mapeamentos,
        mapa=mapa_por_chave,
        total=len(mapeamentos),
    )


@login_required
def listar_ordens_pendentes_fornecedor_api(request):
    """
    Retorna as Ordens de Compra em aberto (PENDENTE ou APROVADA) no SGE.
    Prioriza ordens do fornecedor indicado pelo CNPJ.
    """
    cnpj = limpar_cnpj(request.GET.get('cnpj', ''))
    busca = (request.GET.get('q') or '').strip().lower()

    qs = OrdemCompra.objects.filter(
        status__in=['PENDENTE', 'APROVADA']
    ).select_related('fornecedor').prefetch_related('itens__produto').order_by('-id')

    if cnpj:
        qs_filtrada = qs.filter(fornecedor__cnpj__icontains=cnpj)
        if qs_filtrada.exists():
            qs = qs_filtrada

    if busca:
        qs = qs.filter(
            Q(id__icontains=busca) |
            Q(fornecedor__nome__icontains=busca) |
            Q(observacao__icontains=busca)
        )

    ordens = []
    for o in qs[:50]:
        itens_ordem = []
        val_total = Decimal('0.00')
        for it in o.itens.all():
            subtotal = it.quantidade * it.preco_unitario
            val_total += subtotal
            itens_ordem.append({
                'item_id': it.id,
                'produto_id': it.produto_id,
                'produto_descricao': it.produto.descricao,
                'quantidade': float(it.quantidade),
                'preco_unitario': float(it.preco_unitario),
                'subtotal': float(subtotal),
            })

        ordens.append({
            'id': o.id,
            'status': o.status,
            'status_display': o.get_status_display(),
            'fornecedor_id': o.fornecedor_id,
            'fornecedor_nome': o.fornecedor.nome if o.fornecedor else 'Fornecedor não informado',
            'fornecedor_cnpj': o.fornecedor.cnpj if o.fornecedor else '',
            'data_criacao': o.data_criacao.strftime('%d/%m/%Y'),
            'total_itens': len(itens_ordem),
            'valor_total': float(val_total),
            'observacao': o.observacao,
            'itens': itens_ordem,
        })

    return json_ok(ordens=ordens, total=len(ordens))


@login_required
def sincronizar_omie_api(request):
    """
    Executa a sincronização ativa com a API Omie para o período especificado (padrão 30 dias),
    atualizando o carimbo de último sync na ConfiguracaoOmie.
    """
    dias = 30
    if request.method == 'POST' and request.body:
        try:
            body = json.loads(request.body)
            dias = int(body.get('dias', 30))
        except Exception:
            pass
    elif request.GET.get('dias'):
        try:
            dias = int(request.GET.get('dias'))
        except Exception:
            pass

    hoje = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    dt_inicio = (hoje - timedelta(days=dias)).strftime('%d/%m/%Y')
    dt_fim = hoje.strftime('%d/%m/%Y')

    try:
        client = OmieClient()
        resumo = client.listar_recebimentos_fornecedores_periodo(
            dt_inicio=dt_inicio,
            dt_fim=dt_fim,
            apenas_fornecedores=True,
            incluir_detalhes=True,
        )
    except OmieConfigError as exc:
        return json_erro(str(exc), codigo='OMIE_NAO_CONFIGURADO', status=400)
    except OmieAPIError as exc:
        return json_erro(f'Erro na API Omie: {exc.descricao}', codigo='OMIE_API_ERROR', status=502)
    except Exception as exc:
        logger.exception('Erro ao sincronizar com Omie: %s', exc)
        return json_erro(f'Falha ao sincronizar: {exc}', status=500)

    todas_notas = resumo.get('notas', [])
    ids_receb = [n['id_receb'] for n in todas_notas if n.get('id_receb')]
    importadas_ids = set(
        ImportacaoNFe.objects.filter(n_cod_nota_ent__in=ids_receb).values_list('n_cod_nota_ent', flat=True)
    )

    novas_notas = [n for n in todas_notas if n.get('id_receb') not in importadas_ids]

    # Disparar notificações para novas notas recebidas que ainda não foram alertadas
    for n in novas_notas:
        num = n.get('numero_nfe') or ''
        forn = n.get('fornecedor_nome') or ''
        v_tot = n.get('valor_total') or 0
        chv = n.get('chave_nfe') or ''
        ja_notificada = NotificationLog.objects.filter(
            event=NFE_RECEIVED,
            payload__data__numero_nfe=str(num),
            payload__data__fornecedor=str(forn),
        ).exists()
        if not ja_notificada:
            try:
                notify_nfe_received(
                    numero_nfe=str(num),
                    fornecedor_nome=str(forn),
                    valor_total=v_tot,
                    chave_nfe=str(chv),
                )
            except Exception as notif_err:
                logger.warning('Falha ao enviar notificação de nova NF-e %s: %s', num, notif_err)

    cfg, _ = ConfiguracaoOmie.objects.get_or_create(id=1)
    agora_tz = timezone.now()
    status_msg = f'{len(todas_notas)} NF-e consultadas ({len(novas_notas)} nova(s) pendente(s))'
    cfg.ultimo_sync_em = agora_tz
    cfg.ultimo_sync_status = status_msg
    cfg.save(update_fields=['ultimo_sync_em', 'ultimo_sync_status'])

    return json_ok(
        mensagem=f'Sincronização concluída com sucesso! {len(todas_notas)} nota(s) consultada(s).',
        total_notas=len(todas_notas),
        novas_notas=len(novas_notas),
        ultimo_sync_em=agora_tz.strftime('%d/%m/%Y %H:%M'),
        ultimo_sync_status=status_msg,
    )


@login_required
def consultar_danfe_omie_api(request):
    """
    Retorna a URL do DANFE (PDF) da NF-e consultando a Omie ou gerando link oficial de acesso seguro.
    """
    id_receb_raw = request.GET.get('id_receb')
    chave_nfe = str(request.GET.get('chave', '')).strip().replace(' ', '')

    danfe_url = None
    if id_receb_raw or chave_nfe:
        try:
            client = OmieClient()
            danfe_url = client.consultar_danfe(
                n_id_receb=int(id_receb_raw) if id_receb_raw else None,
                chave_nfe=chave_nfe or None,
            )
        except Exception as exc:
            logger.warning('Erro ao consultar DANFE na Omie: %s', exc)

    if not danfe_url and chave_nfe and len(chave_nfe) == 44:
        danfe_url = f'https://meudanfe.com.br/ver/{chave_nfe}'

    if not danfe_url:
        return json_erro('DANFE não disponível ou chave da NF-e não informada.', status=404)

    return json_ok(danfe_url=danfe_url)




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
    ordem_compra_id = data.get('ordem_compra_id')

    # Tentar localizar ou criar Fornecedor correspondente no SGE
    fornecedor_obj = None
    cnpj_limpo = limpar_cnpj(fornecedor_cnpj) if fornecedor_cnpj else ''
    if cnpj_limpo:
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
    ordem_compra_obj = None

    try:
        with transaction.atomic():
            if ImportacaoNFe.objects.filter(n_cod_nota_ent=id_receb).exists():
                return json_erro(
                    f'A NF-e #{id_receb} já foi importada anteriormente.',
                    codigo='JA_IMPORTADO',
                    status=400,
                )

            # Se vinculada a uma Ordem de Compra existente
            if ordem_compra_id:
                try:
                    ordem_compra_obj = OrdemCompra.objects.select_for_update().get(pk=ordem_compra_id)
                    if ordem_compra_obj.status != 'RECEBIDA':
                        ordem_compra_obj.status = 'RECEBIDA'
                        ordem_compra_obj.save(update_fields=['status'])
                        log_acao(
                            request.user,
                            'RECEBER',
                            f'Ordem de Compra #{ordem_compra_obj.id} finalizada como RECEBIDA via importação da NF-e nº {numero_nfe or id_receb} ({fornecedor_nome})',
                            'OrdemCompra',
                            ordem_compra_obj.id,
                        )
                except OrdemCompra.DoesNotExist:
                    return json_erro(f'Ordem de Compra #{ordem_compra_id} não encontrada.', status=404)

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

                fator_raw = it.get('fator_conversao')
                try:
                    fator_dec = Decimal(str(fator_raw)) if fator_raw not in (None, '') else Decimal('1.0')
                    if fator_dec <= 0:
                        fator_dec = Decimal('1.0')
                except (InvalidOperation, TypeError, ValueError):
                    fator_dec = Decimal('1.0')

                qtd_efetiva = qtd_dec * fator_dec
                custo_unit_efetivo = (val_unit_dec / fator_dec) if (val_unit_dec > 0 and fator_dec > 0) else val_unit_dec

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

                    cat_id_raw = np_data.get('categoria_id')
                    cat_obj = None
                    if cat_id_raw:
                        try:
                            cat_obj = Categoria.objects.filter(id=int(cat_id_raw)).first()
                        except (ValueError, TypeError):
                            cat_obj = None

                    produto = Produto(
                        descricao=desc,
                        tipo_produto=tipo_prod,
                        unidade_medida=unid,
                        categoria=cat_obj,
                        quantidade_base=Decimal('0.00'),
                        preco_custo=custo_unit_efetivo if custo_unit_efetivo > 0 else None,
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
                    if it.get('atualizar_custo') and custo_unit_efetivo > 0 and produto.preco_custo != custo_unit_efetivo:
                        custo_antigo = produto.preco_custo
                        produto.preco_custo = custo_unit_efetivo
                        produto.save(update_fields=['preco_custo'])
                        HistoricoPreco.objects.create(
                            produto=produto,
                            preco_custo_antigo=custo_antigo,
                            preco_custo_novo=custo_unit_efetivo,
                            usuario=request.user,
                        )

                # Registrar Movimentacao de Entrada com quantidade e custo efetivos
                obs = f'Importado da NF-e nº {numero_nfe or id_receb} ({fornecedor_nome}) | {it.get("descricao_omie", "")}'
                if fator_dec != Decimal('1.0'):
                    obs += f' [Fator {fator_dec}: {qtd_dec} => {qtd_efetiva} {produto.unidade_medida}]'

                Movimentacao.objects.create(
                    produto=produto,
                    usuario=request.user,
                    tipo='ENTRADA',
                    motivo='COMPRA',
                    quantidade=qtd_efetiva,
                    observacao=obs[:255],
                )

                # Salvar ou atualizar memória de De-Para do fornecedor com fator de conversão
                if cnpj_limpo:
                    cod_item = str(it.get('codigo_omie', '')).strip()
                    desc_item = str(it.get('descricao_omie', '')).strip()
                    if desc_item:
                        try:
                            DeParaOmie.objects.update_or_create(
                                fornecedor_cnpj=cnpj_limpo,
                                codigo_produto_fornecedor=cod_item,
                                descricao_produto_fornecedor=desc_item,
                                defaults={
                                    'fornecedor_nome': fornecedor_nome[:200],
                                    'produto': produto,
                                    'fator_conversao': fator_dec,
                                }
                            )
                        except Exception as depara_exc:
                            logger.warning('Falha ao gravar DeParaOmie para item "%s": %s', desc_item, depara_exc)

                movimentacoes_criadas += 1
                descricoes_importadas.append(f'{produto.descricao} (+{qtd_efetiva})')

            # Registrar controle de NF-e importada
            ImportacaoNFe.objects.create(
                n_cod_nota_ent=id_receb,
                numero_nfe=numero_nfe,
                fornecedor_nome=fornecedor_nome,
                ordem_compra=ordem_compra_obj,
                usuario=request.user,
                observacao=(
                    f'{movimentacoes_criadas} item(ns) importado(s) via conciliação web'
                    + (f' | Vinculada à Ordem de Compra #{ordem_compra_obj.id}' if ordem_compra_obj else '')
                ),
            )

            log_acao(
                request.user,
                'ENTRADA',
                (
                    f'Importação NF-e {numero_nfe or id_receb} ({fornecedor_nome}) — '
                    f'{movimentacoes_criadas} entrada(s): {", ".join(descricoes_importadas[:5])}'
                    + ('...' if len(descricoes_importadas) > 5 else '')
                    + (f' [Ordem #{ordem_compra_obj.id} RECEBIDA]' if ordem_compra_obj else '')
                ),
                'ImportacaoNFe',
                id_receb,
            )

        msg_retorno = f'{movimentacoes_criadas} entrada(s) de estoque registrada(s) com sucesso!'
        if ordem_compra_obj:
            msg_retorno += f' Ordem de Compra #{ordem_compra_obj.id} marcada como RECEBIDA.'

        return json_ok(
            mensagem=msg_retorno,
            movimentacoes_criadas=movimentacoes_criadas,
            ordem_compra_id=ordem_compra_obj.id if ordem_compra_obj else None,
        )
    except Exception as exc:
        logger.exception('Erro ao importar itens da NF-e Omie: %s', exc)
        return json_erro(f'Falha ao importar itens da NF-e: {exc}')

