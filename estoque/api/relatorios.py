from datetime import datetime
from decimal import Decimal
import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from ..log_utils import log_acao
from ..models import LogAcao, Movimentacao
from ..services.estoque_metrics import agrupar_quantidade_por_unidade, serializar_totais_unidade
from ..services.units import formatar_quantidade, unidade_base_codigo
from ..views.helpers import PERFIS_NEGOCIO, exigir_admin_json, json_erro, json_ok


@login_required
def relatorio_mensal_api(request):
    """Relatório consolidado de movimentações por período."""
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

    por_produto = movs.values(
        'produto_id', 'produto__descricao', 'produto__tipo_produto', 'produto__unidade_medida', 'tipo'
    ).annotate(
        total=Sum('quantidade')
    ).order_by('produto__descricao')

    movs_por_produto = {}
    for item in por_produto:
        produto_id = item['produto_id']
        if produto_id not in movs_por_produto:
            fake_produto = type('ProdutoUnidade', (), {
                'tipo_produto': item['produto__tipo_produto'],
                'unidade_medida': item['produto__unidade_medida'],
            })()
            movs_por_produto[produto_id] = {
                'produto_id': produto_id,
                'nome': item['produto__descricao'],
                'entradas': Decimal('0'),
                'saidas': Decimal('0'),
                'unidade': unidade_base_codigo(fake_produto),
            }
        if item['tipo'] == 'ENTRADA':
            movs_por_produto[produto_id]['entradas'] += item['total']
        else:
            movs_por_produto[produto_id]['saidas'] += item['total']

    produtos_afetados = [
        {
            'produto_id': d['produto_id'],
            'nome': d['nome'],
            'entradas': float(d['entradas']),
            'entradas_formatadas': formatar_quantidade(d['entradas'], d['unidade']),
            'saidas': float(d['saidas']),
            'saidas_formatadas': formatar_quantidade(d['saidas'], d['unidade']),
            'saldo': float(d['entradas'] - d['saidas']),
            'saldo_formatado': formatar_quantidade(d['entradas'] - d['saidas'], d['unidade']),
        }
        for d in movs_por_produto.values()
    ]

    return json_ok(
        periodo={
            'data_inicio': data_inicio,
            'data_fim': data_fim,
        },
        totais_entradas=total_entradas_unidade,
        totais_saidas=total_saidas_unidade,
        total_movimentacoes=movs.count(),
        produtos_afetados=produtos_afetados,
    )


@login_required
def logs_api(request):
    """Lista paginada do log de auditoria com filtros."""
    busca = (request.GET.get('busca') or request.GET.get('q') or '').strip()
    acao = request.GET.get('acao', '').strip()

    try:
        page_size = min(int(request.GET.get('page_size', 25)), 100)
    except (TypeError, ValueError):
        page_size = 25

    logs_qs = LogAcao.objects.select_related('usuario').all().order_by('-data')
    if busca:
        logs_qs = logs_qs.filter(
            Q(descricao__icontains=busca)
            | Q(usuario__username__icontains=busca)
            | Q(modelo__icontains=busca)
        )
    if acao:
        logs_qs = logs_qs.filter(acao=acao)

    paginator = Paginator(logs_qs, page_size)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    itens = [
        {
            'id': log.id,
            'data': log.data.isoformat(),
            'data_formatada': log.data.strftime('%d/%m/%Y %H:%M'),
            'usuario': log.usuario.username if log.usuario else '-',
            'acao': log.acao,
            'descricao': log.descricao,
            'modelo': log.modelo,
            'objeto_id': log.objeto_id,
        }
        for log in page_obj
    ]

    return json_ok(
        itens=itens,
        paginacao={
            'pagina_atual': page_obj.number,
            'total_paginas': paginator.num_pages,
            'total_itens': paginator.count,
            'tem_proxima': page_obj.has_next(),
            'tem_anterior': page_obj.has_previous(),
            'itens_por_pagina': page_size,
        },
        acoes_disponiveis=[{'value': val, 'label': lbl} for val, lbl in LogAcao.ACAO_CHOICES],
        filtros_aplicados={'busca': busca, 'acao': acao},
    )


@login_required
def usuarios_api(request):
    """Retorna lista de usuários e perfis (acesso restrito a superadministradores)."""
    perm_error = exigir_admin_json(request)
    if perm_error:
        return perm_error

    usuarios = User.objects.prefetch_related('groups').all().order_by('username')
    grupos = Group.objects.all().order_by('name')

    perfis = [
        {'id': g.id, 'nome': PERFIS_NEGOCIO.get(g.name, g.name), 'interno': g.name}
        for g in grupos
    ]

    usuarios_data = []
    for u in usuarios:
        grupo_principal = u.groups.first()
        perfil_nome = 'Administrador' if u.is_superuser else (
            PERFIS_NEGOCIO.get(grupo_principal.name, grupo_principal.name) if grupo_principal else 'Sem perfil'
        )
        usuarios_data.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'is_active': u.is_active,
            'is_superuser': u.is_superuser,
            'perfil': perfil_nome,
            'grupo_id': grupo_principal.id if grupo_principal else None,
        })

    return json_ok(
        usuarios=usuarios_data,
        perfis=perfis,
    )


@login_required
def criar_usuario_api(request):
    """Cria um novo usuário e associa ao perfil desejado (restrito a superadministradores)."""
    perm_error = exigir_admin_json(request)
    if perm_error:
        return perm_error
    if request.method != 'POST':
        return json_erro('Método não permitido.', status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return json_erro('JSON inválido.')

    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    email = (data.get('email') or '').strip()
    grupo_id = data.get('grupo_id')
    is_superuser = bool(data.get('is_superuser', False))

    if not username:
        return json_erro('O nome de usuário é obrigatório.')
    if not password:
        return json_erro('A senha é obrigatória.')
    if User.objects.filter(username__iexact=username).exists():
        return json_erro('Já existe um usuário com este login.')

    user = User.objects.create_user(username=username, password=password, email=email)
    if is_superuser:
        user.is_superuser = True
        user.is_staff = True
        user.save()

    if grupo_id:
        try:
            grupo = Group.objects.get(id=grupo_id)
            user.groups.add(grupo)
        except Group.DoesNotExist:
            pass

    log_acao(request.user, 'CRIAR', f'Criou novo usuário {user.username}', 'User', user.id)
    return json_ok(mensagem='Usuário criado com sucesso.', id=user.id)


@login_required
def alterar_perfil_usuario_api(request, id):
    """Altera grupo/perfil, superusuário ou status ativo de um usuário (restrito a superadministradores)."""
    perm_error = exigir_admin_json(request)
    if perm_error:
        return perm_error
    if request.method != 'POST':
        return json_erro('Método não permitido.', status=405)

    target_user = get_object_or_404(User, id=id)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return json_erro('JSON inválido.')

    grupo_id = data.get('grupo_id')
    is_active = data.get('is_active')
    is_superuser = data.get('is_superuser')

    if is_active is not None:
        if target_user == request.user and not is_active:
            return json_erro('Você não pode desativar seu próprio usuário.')
        target_user.is_active = bool(is_active)

    if is_superuser is not None:
        if target_user == request.user and not is_superuser:
            return json_erro('Você não pode revogar seus próprios privilégios de superusuário.')
        target_user.is_superuser = bool(is_superuser)
        target_user.is_staff = bool(is_superuser)

    target_user.save()

    if grupo_id is not None:
        target_user.groups.clear()
        if grupo_id:
            try:
                grupo = Group.objects.get(id=grupo_id)
                target_user.groups.add(grupo)
            except Group.DoesNotExist:
                pass

    log_acao(
        request.user,
        'EDITAR',
        f'Alterou permissões/perfil do usuário {target_user.username}',
        'User',
        target_user.id,
    )
    return json_ok(mensagem='Usuário atualizado com sucesso.')
