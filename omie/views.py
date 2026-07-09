import decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import JsonResponse

from estoque.models import Produto, Movimentacao
from estoque.log_utils import log_acao
from .models import OmieConfig, OmieRecebimentoNFe, OmieRecebimentoItem, OmieProdutoMapping
from .services import sincronizar_recebimentos_omie, aprovar_recebimento_nfe, OmieApiError, normalizar_cnpj


@login_required
def lista_notas_omie(request):
    """
    Lista os recebimentos NF-e importados do Omie com filtros.
    """
    status_filtro = request.GET.get('status', '').strip()
    fornecedor_filtro = request.GET.get('fornecedor', '').strip()
    numero_filtro = request.GET.get('numero', '').strip()
    data_de = request.GET.get('data_de', '').strip()
    data_ate = request.GET.get('data_ate', '').strip()

    qs = OmieRecebimentoNFe.objects.select_related('fornecedor').prefetch_related('itens').all()

    if status_filtro:
        qs = qs.filter(status=status_filtro)
    
    if fornecedor_filtro:
        qs = qs.filter(fornecedor_nome__icontains=fornecedor_filtro) | qs.filter(fornecedor_cnpj__contains=fornecedor_filtro)
        
    if numero_filtro:
        qs = qs.filter(numero_nf__contains=numero_filtro)
        
    if data_de:
        try:
            qs = qs.filter(data_emissao__gte=data_de)
        except (ValueError, ValidationError):
            pass
            
    if data_ate:
        try:
            qs = qs.filter(data_emissao__lte=data_ate)
        except (ValueError, ValidationError):
            pass

    for nota in qs:
        nota.qtd_itens = nota.itens.count()
        nota.qtd_itens_vinculados = nota.itens.filter(produto__isnull=False).count()
        nota.pode_ser_aprovada = nota.pode_aprovar()

    config_ativa = OmieConfig.objects.filter(ativo=True).first()

    return render(request, 'omie/lista_notas.html', {
        'notas': qs,
        'status_filtro': status_filtro,
        'fornecedor_filtro': fornecedor_filtro,
        'numero_filtro': numero_filtro,
        'data_de': data_de,
        'data_ate': data_ate,
        'config_ativa': config_ativa,
    })


@login_required
def sincronizar_omie(request):
    """
    Dispara a sincronização manual com o Omie via interface web.
    """
    if request.method != 'POST':
        messages.error(request, "Método não permitido.")
        return redirect('lista_notas_omie')

    config = OmieConfig.objects.filter(ativo=True).first()
    if not config:
        messages.error(request, "Nenhuma configuração ativa do Omie cadastrada no sistema.")
        return redirect('lista_notas_omie')

    dias_str = request.POST.get('dias', '365')
    try:
        dias = int(dias_str)
    except ValueError:
        dias = 365

    try:
        resumo = sincronizar_recebimentos_omie(
            dias=dias,
            registros_por_pagina=50
        )
        
        if resumo.get('erros', 0) > 0:
            messages.warning(
                request,
                f"Sincronização executada com avisos!<br>"
                f"Recebimentos criados: {resumo.get('criadas', 0)}<br>"
                f"Recebimentos atualizados: {resumo.get('atualizadas', 0)}<br>"
                f"Recebimentos com erros: {resumo.get('erros', 0)}"
            )
        else:
            messages.success(
                request,
                f"Sincronização concluída com sucesso!<br>"
                f"Recebimentos criados: {resumo.get('criadas', 0)}<br>"
                f"Recebimentos atualizados: {resumo.get('atualizadas', 0)}"
            )

    except Exception as e:
        messages.error(request, f"Erro inesperado durante a sincronização: {e}")

    return redirect('lista_notas_omie')


@login_required
def detalhe_nota_omie(request, id):
    """
    Exibe os detalhes de um recebimento NF-e do Omie e seus itens.
    Permite fazer a vinculação manual dos itens a produtos do estoque.
    """
    nota = get_object_or_404(OmieRecebimentoNFe, id=id)
    itens = nota.itens.all().order_by('sequencia')
    produtos = Produto.objects.all().order_by('descricao')

    for item in itens:
        if item.quantidade_convertida is None:
            item.quantidade_convertida = item.quantidade_entrada
        
        if item.quantidade_entrada > 0:
            item.fator_atual = round(item.quantidade_convertida / item.quantidade_entrada, 6)
        else:
            item.fator_atual = 1.000000

    return render(request, 'omie/detalhe_nota.html', {
        'nota': nota,
        'itens': itens,
        'produtos': produtos,
    })


@login_required
def salvar_vinculos_omie(request, id):
    """
    Salva os vínculos de produtos e fatores de conversão dos itens do recebimento.
    """
    if request.method != 'POST':
        messages.error(request, "Método não permitido.")
        return redirect('detalhe_nota_omie', id=id)

    nota = get_object_or_404(OmieRecebimentoNFe, id=id)
    
    if nota.status in ['IMPORTADA', 'APROVADA']:
        messages.error(request, "Este recebimento já foi importado no estoque e não pode ter seus vínculos alterados.")
        return redirect('detalhe_nota_omie', id=id)

    try:
        with transaction.atomic():
            for item in nota.itens.all():
                prod_id_str = request.POST.get(f'produto_{item.id}', '').strip()
                fator_str = request.POST.get(f'fator_{item.id}', '1.0').strip()
                status_str = request.POST.get(f'status_{item.id}', 'PENDENTE').strip()

                try:
                    fator = decimal.Decimal(fator_str.replace(',', '.'))
                except (ValueError, TypeError, decimal.InvalidOperation):
                    fator = decimal.Decimal('1.000000')

                if status_str == 'IGNORADO':
                    item.status = 'IGNORADO'
                    item.produto = None
                    item.quantidade_convertida = None
                    item.unidade_convertida = ""
                else:
                    if prod_id_str:
                        produto = Produto.objects.get(pk=prod_id_str)
                        item.produto = produto
                        item.quantidade_convertida = item.quantidade_entrada * fator
                        item.unidade_convertida = produto.unidade_medida
                        item.status = 'VINCULADO'
                    else:
                        item.produto = None
                        item.quantidade_convertida = item.quantidade_entrada
                        item.unidade_convertida = item.unidade_entrada
                        item.status = 'PENDENTE'
                
                item.save()

        messages.success(request, "Vínculos dos itens salvos com sucesso!")
    except Exception as e:
        messages.error(request, f"Erro ao salvar vínculos: {e}")

    return redirect('detalhe_nota_omie', id=id)


@login_required
def aprovar_nota_omie(request, id):
    """
    Aprova o recebimento gerando a movimentação de estoque.
    """
    if request.method != 'POST':
        messages.error(request, "Método não permitido.")
        return redirect('detalhe_nota_omie', id=id)

    nota = get_object_or_404(OmieRecebimentoNFe, id=id)

    if not nota.pode_aprovar():
        messages.error(request, "O recebimento não pode ser aprovado. Certifique-se de vincular todos os itens não ignorados a produtos.")
        return redirect('detalhe_nota_omie', id=id)

    try:
        res = aprovar_recebimento_nfe(nota, request.user)
        if res.get('sucesso'):
            messages.success(request, f"Recebimento importado com sucesso! {res.get('movimentacoes_geradas', 0)} item(ns) adicionados ao estoque.")
        else:
            messages.error(request, "Falha na aprovação do recebimento.")
    except ValidationError as e:
        messages.error(request, f"Erro de validação: {e.message if hasattr(e, 'message') else str(e)}")
    except Exception as e:
        messages.error(request, f"Erro ao aprovar recebimento: {e}")

    return redirect('detalhe_nota_omie', id=id)


@login_required
def ignorar_nota_omie(request, id):
    """
    Muda o status do recebimento para IGNORADA.
    """
    if request.method != 'POST':
        messages.error(request, "Método não permitido.")
        return redirect('lista_notas_omie')

    nota = get_object_or_404(OmieRecebimentoNFe, id=id)
    if nota.status in ['IMPORTADA', 'APROVADA']:
        messages.error(request, "Recebimentos importados não podem ser ignorados.")
        return redirect('lista_notas_omie')

    nota.status = 'IGNORADA'
    nota.save(update_fields=['status'])
    
    log_acao(
        request.user, 'CANCELAR',
        f"Recebimento Omie #{nota.numero_nf} marcado como ignorado.",
        'OmieRecebimentoNFe', nota.id
    )
    
    messages.success(request, f"Recebimento #{nota.numero_nf} foi ignorado.")
    return redirect('lista_notas_omie')


@login_required
def reativar_nota_omie(request, id):
    """
    Reativa um recebimento marcado como IGNORADA ou ERRO para PENDENTE.
    """
    if request.method != 'POST':
        messages.error(request, "Método não permitido.")
        return redirect('lista_notas_omie')

    nota = get_object_or_404(OmieRecebimentoNFe, id=id)
    if nota.status not in ['IGNORADA', 'ERRO']:
        messages.error(request, "Somente recebimentos ignorados ou com erro podem ser reativados.")
        return redirect('lista_notas_omie')

    nota.status = 'PENDENTE'
    nota.save(update_fields=['status'])
    
    log_acao(
        request.user, 'EDITAR',
        f"Recebimento Omie #{nota.numero_nf} reativado para pendente.",
        'OmieRecebimentoNFe', nota.id
    )
    
    messages.success(request, f"Recebimento #{nota.numero_nf} foi reativado.")
    return redirect('detalhe_nota_omie', id=id)
