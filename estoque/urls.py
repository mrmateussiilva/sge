from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('exportar-csv/', views.exportar_csv, name='exportar_csv'),
    path('produtos/', views.lista_produtos, name='lista_produtos'),
    path('produtos/template-csv/', views.template_csv_produtos, name='template_csv_produtos'),
    path('produtos/importar-csv/', views.importar_csv_produtos, name='importar_csv_produtos'),
    path('produto/<int:id>/', views.detalhe_produto, name='detalhe_produto'),
    path('movimentacao/', views.registrar_movimentacao, name='registrar_movimentacao'),
    path('atualiza-estoque/', views.atualiza_estoque, name='atualiza_estoque'),
    path('cadastrar-produto/', views.cadastrar_produto, name='cadastrar_produto'),
    path('produto/<int:id>/editar/', views.editar_produto, name='editar_produto'),
    path('produto/<int:id>/excluir/', views.excluir_produto, name='excluir_produto'),
    path('movimentacao/<int:id>/excluir/', views.excluir_movimentacao, name='excluir_movimentacao'),
    path('ordens/', views.lista_ordens, name='lista_ordens'),
    path('ordem/nova/', views.criar_ordem, name='criar_ordem'),
    path('ordem/<int:id>/', views.detalhe_ordem, name='detalhe_ordem'),
    path('ordem/<int:id>/aprovar/', views.aprovar_ordem, name='aprovar_ordem'),
    path('ordem/<int:id>/cancelar/', views.cancelar_ordem, name='cancelar_ordem'),
    path('ordem/<int:id>/receber/', views.receber_ordem, name='receber_ordem'),
    path('produto/<int:id>/etiqueta/', views.etiqueta_produto, name='etiqueta_produto'),
    path('relatorio/', views.relatorio_mensal, name='relatorio_mensal'),
    path('log/', views.log_acoes, name='log_acoes'),
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
]
