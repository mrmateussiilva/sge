from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_notas_omie, name='lista_notas_omie'),
    path('sincronizar/', views.sincronizar_omie, name='sincronizar_omie'),
    path('nota/<int:id>/', views.detalhe_nota_omie, name='detalhe_nota_omie'),
    path('nota/<int:id>/salvar-vinculos/', views.salvar_vinculos_omie, name='salvar_vinculos_omie'),
    path('nota/<int:id>/aprovar/', views.aprovar_nota_omie, name='aprovar_nota_omie'),
    path('nota/<int:id>/ignorar/', views.ignorar_nota_omie, name='ignorar_nota_omie'),
    path('nota/<int:id>/reativar/', views.reativar_nota_omie, name='reativar_nota_omie'),
]
