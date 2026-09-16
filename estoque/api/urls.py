from django.urls import path

from .. import views
from . import (
    auth,
    categorias,
    dashboard,
    fechamentos,
    fornecedores,
    movimentacoes,
    ordens,
    produtos,
    relatorios,
)

app_name = 'api_v1'

urlpatterns = [
    # Auth & Sessão
    path('me/', auth.me, name='me'),
    path('auth/logout/', auth.api_logout, name='logout'),

    # Dashboard
    path('dashboard/', dashboard.dashboard_metricas, name='dashboard'),
    path('dashboard/chart/', dashboard.dashboard_chart, name='dashboard_chart'),

    # Produtos
    path('produtos/', produtos.listar_produtos_api, name='produtos_lista'),
    path('produtos/opcoes/', produtos.opcoes_produto_api, name='produtos_opcoes'),
    path('produtos/<int:id>/', produtos.detalhe_produto_api, name='produtos_detalhe'),
    path('produtos/cadastrar/', views.cadastrar_produto, name='produtos_cadastrar'),
    path('produtos/<int:id>/editar/', views.editar_produto, name='produtos_editar'),
    path('produtos/<int:id>/excluir/', views.excluir_produto, name='produtos_excluir'),
    path('produtos/atualiza-estoque/', views.atualiza_estoque, name='produtos_atualiza_estoque'),
    path('produtos/importar-csv/', views.importar_csv_produtos, name='produtos_importar_csv'),

    # Movimentações
    path('movimentacoes/', movimentacoes.listar_movimentacoes_api, name='movimentacoes_lista'),
    path('movimentacoes/registrar/', views.registrar_movimentacao, name='movimentacoes_registrar'),
    path('movimentacoes/<int:id>/excluir/', views.excluir_movimentacao, name='movimentacoes_excluir'),

    # Ordens de Compra
    path('ordens/', ordens.listar_ordens_api, name='ordens_lista'),
    path('ordens/<int:id>/', ordens.detalhe_ordem_api, name='ordens_detalhe'),
    path('ordens/criar/', views.criar_ordem, name='ordens_criar'),
    path('ordens/<int:id>/aprovar/', views.aprovar_ordem, name='ordens_aprovar'),
    path('ordens/<int:id>/cancelar/', views.cancelar_ordem, name='ordens_cancelar'),
    path('ordens/<int:id>/receber/', views.receber_ordem, name='ordens_receber'),

    # Categorias
    path('categorias/', categorias.listar_categorias_api, name='categorias_lista'),
    path('categorias/salvar/', views.salvar_categoria, name='categorias_salvar'),
    path('categorias/<int:id>/editar/', views.salvar_categoria, name='categorias_editar'),
    path('categorias/<int:id>/excluir/', views.excluir_categoria, name='categorias_excluir'),

    # Fornecedores
    path('fornecedores/', fornecedores.listar_fornecedores_api, name='fornecedores_lista'),
    path('fornecedores/salvar/', views.salvar_fornecedor, name='fornecedores_salvar'),
    path('fornecedores/<int:id>/editar/', views.salvar_fornecedor, name='fornecedores_editar'),
    path('fornecedores/<int:id>/excluir/', views.excluir_fornecedor, name='fornecedores_excluir'),

    # Fechamentos
    path('fechamentos/', fechamentos.listar_fechamentos_api, name='fechamentos_lista'),
    path('fechamentos/revisar/', fechamentos.revisar_fechamento_api, name='fechamentos_revisar'),
    path('fechamentos/<int:id>/', fechamentos.detalhe_fechamento_api, name='fechamentos_detalhe'),
    path('fechamentos/<int:id>/exportar/', views.exportar_fechamento_xlsx, name='fechamentos_exportar'),
    path('fechamentos/realizar/', views.realizar_fechamento, name='fechamentos_realizar'),
    path('fechamentos/<int:id>/excluir/', views.excluir_fechamento, name='fechamentos_excluir'),

    # Relatórios, Logs e Usuários
    path('relatorio/', relatorios.relatorio_mensal_api, name='relatorio_mensal'),
    path('logs/', relatorios.logs_api, name='logs'),
    path('usuarios/', relatorios.usuarios_api, name='usuarios'),
    path('usuarios/criar/', relatorios.criar_usuario_api, name='usuarios_criar'),
    path('usuarios/<int:id>/perfil/', relatorios.alterar_perfil_usuario_api, name='usuarios_perfil'),

    # Omie e Busca Rápida
    path('busca-rapida/', views.busca_rapida, name='busca_rapida'),
    path('omie/notas/', views.buscar_notas_omie, name='omie_notas'),
    path('omie/notas/<int:n_cod>/importar/', views.importar_nota_omie, name='omie_importar'),
    path('omie/configuracao/', views.salvar_configuracao_omie, name='omie_configuracao'),
]
