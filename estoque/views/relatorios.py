import json
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from ..log_utils import log_acao
from ..models import LogAcao, Movimentacao
from ..services.estoque_metrics import agrupar_quantidade_por_unidade, serializar_totais_unidade
from ..services.units import formatar_quantidade, unidade_base_codigo
from ..services.usernames import validate_username_available
from .helpers import PERFIS_NEGOCIO, exigir_admin_json, json_erro, json_ok, requisicao_htmx


@login_required
def relatorio_mensal(request):
    hoje = timezone.now()
    data_inicio = request.GET.get('data_inicio', hoje.replace(day=1).strftime('%Y-%m-%d'))
    data_fim = request.GET.get('data_fim', hoje.strftime('%Y-%m-%d'))
    try:
        dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
        dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.get_current_timezone())
    except ValueError:
        dt_inicio = hoje.replace(day=1)
        dt_fim = hoje

    movs = Movimentacao.objects.filter(data__gte=dt_inicio, data__lte=dt_fim).select_related('produto')
    total_entradas_unidade = serializar_totais_unidade(agrupar_quantidade_por_unidade(movs.filter(tipo='ENTRADA')))
    total_saidas_unidade = serializar_totais_unidade(agrupar_quantidade_por_unidade(movs.filter(tipo='SAIDA')))

    por_produto = movs.values('produto__descricao', 'produto__tipo_produto', 'produto__unidade_medida', 'tipo').annotate(
        total=Sum('quantidade')
    ).order_by('produto__descricao')

    movs_por_produto = {}
    for item in por_produto:
        nome = item['produto__descricao']
        if nome not in movs_por_produto:
            fake_produto = type('ProdutoUnidade', (), {
                'tipo_produto': item['produto__tipo_produto'],
                'unidade_medida': item['produto__unidade_medida'],
            })()
            movs_por_produto[nome] = {'entradas': Decimal('0'), 'saidas': Decimal('0'), 'unidade': unidade_base_codigo(fake_produto)}
        if item['tipo'] == 'ENTRADA':
            movs_por_produto[nome]['entradas'] += item['total']
        else:
            movs_por_produto[nome]['saidas'] += item['total']

    produtos_afetados = [
        {
            'nome': nome,
            'entradas': formatar_quantidade(d['entradas'], d['unidade']),
            'saidas': formatar_quantidade(d['saidas'], d['unidade']),
            'saldo': formatar_quantidade(d['entradas'] - d['saidas'], d['unidade']),
        }
        for nome, d in movs_por_produto.items()
    ]

    return render(request, 'estoque/relatorio.html', {
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'total_entradas_unidade': total_entradas_unidade,
        'total_saidas_unidade': total_saidas_unidade,
        'total_movimentacoes': movs.count(),
        'produtos_afetados': produtos_afetados,
    })


@login_required
def log_acoes(request):
    busca = (request.GET.get('busca') or request.GET.get('q') or '').strip()
    acao = request.GET.get('acao', '').strip()
    logs_qs = LogAcao.objects.select_related('usuario').all().order_by('-data')
    if busca:
        logs_qs = logs_qs.filter(
            Q(descricao__icontains=busca)
            | Q(usuario__username__icontains=busca)
            | Q(modelo__icontains=busca)
        )
    if acao:
        logs_qs = logs_qs.filter(acao=acao)

    paginator = Paginator(logs_qs, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    extra_params = f"&busca={busca}&acao={acao}"
    tem_filtros_ativos = bool(busca or acao)

    context = {
        'page_obj': page_obj,
        'logs': page_obj,
        'busca': busca,
        'acao_selecionada': acao,
        'acoes': LogAcao.ACAO_CHOICES,
        'extra_params': extra_params,
        'tem_filtros_ativos': tem_filtros_ativos,
    }

    if requisicao_htmx(request):
        return render(request, 'estoque/logs/_lista_resultados.html', context)
    return render(request, 'estoque/log_acoes.html', context)


@login_required
def lista_usuarios(request):
    if not request.user.is_superuser:
        if request.method == 'POST':
            return json_erro('Permissão negada.', status=403, codigo='PERMISSAO_NEGADA')
        return render(request, 'estoque/lista_usuarios.html', {'erro': 'Apenas administradores podem gerenciar usuarios.'})
    usuarios = User.objects.prefetch_related('groups').all()
    grupos = Group.objects.all()
    perfis = [
        {'id': g.id, 'nome': PERFIS_NEGOCIO.get(g.name, g.name), 'interno': g.name}
        for g in grupos
    ]
    if request.method == 'POST':
        data = json.loads(request.body)
        acao = data.get('acao')
        if acao == 'criar':
            try:
                username = validate_username_available(data.get('username'))
                user = User.objects.create_user(
                    username=username,
                    password=data['password'],
                    is_staff=True,
                )
            except ValidationError as e:
                return JsonResponse({'ok': False, 'erro': '; '.join(e.messages)}, status=400)
            log_acao(request.user, 'CRIAR', f'Criou usuario {user.username}', 'User', user.id)
        elif acao == 'grupo':
            perm_error = exigir_admin_json(request)
            if perm_error:
                return perm_error
            user = User.objects.get(id=data['user_id'])
            grupo_id = data.get('grupo_id')
            grupo = Group.objects.get(id=grupo_id) if grupo_id else None
            novo_superuser = bool(grupo and grupo.name == 'Admin')
            admins_ativos = User.objects.filter(is_superuser=True, is_active=True).count()
            removendo_admin = user.is_superuser and not novo_superuser
            if removendo_admin and user.id == request.user.id:
                return json_erro('Você não pode remover sua própria permissão administrativa.', status=400, codigo='PERMISSAO_NEGADA')
            if removendo_admin and admins_ativos <= 1:
                return json_erro('O sistema precisa manter pelo menos um administrador.', status=400, codigo='PERMISSAO_NEGADA')
            user.groups.clear()
            if grupo:
                user.groups.add(grupo)
            user.is_staff = grupo is not None
            user.is_superuser = novo_superuser
            user.save()
            perfil_nome = PERFIS_NEGOCIO.get(grupo.name, grupo.name) if grupo else 'Sem perfil'
            log_acao(request.user, 'EDITAR', f'Alterou perfil do usuário {user.username} para {perfil_nome}', 'User', user.id)
            return json_ok(mensagem='Perfil atualizado com sucesso.')
        return json_ok()
    return render(request, 'estoque/lista_usuarios.html', {
        'usuarios': usuarios,
        'grupos': grupos,
        'perfis': perfis,
    })
