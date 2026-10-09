import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Q

from ..log_utils import log_acao
from ..models import ConfiguracaoOmie, ImportacaoNFe
from ..services.omie_client import OmieAPIError, OmieClient, OmieConfigError
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
    except OmieConfigError:
        return json_erro(
            'Credenciais da API Omie não configuradas.',
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
    except Exception:
        logger.exception('Erro inesperado ao consultar recebimentos da Omie')
        return json_erro(
            'Não foi possível consultar os recebimentos no Omie.',
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
    """Retorna o status atual da configuração de credenciais da Omie."""
    cfg = ConfiguracaoOmie.objects.first()
    app_key = cfg.app_key if cfg and cfg.app_key else getattr(settings, 'OMIE_APP_KEY', '')
    app_secret = cfg.app_secret if cfg and cfg.app_secret else getattr(settings, 'OMIE_APP_SECRET', '')

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
