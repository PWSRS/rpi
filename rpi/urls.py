from django.urls import path
from . import views
from .views import (
    OcorrenciaListView,
    OcorrenciaCreateView,
    OcorrenciaDetailView,
    OcorrenciaUpdateView,
    OcorrenciaDeleteView,
    iniciar_dia,
    finalizar_relatorio,
    listar_materiais_apreendidos,
    deletar_materiais_apreendidos,
    RelatorioListView,
)

urlpatterns = [
    # Listagem (EXISTENTE)
    path("", OcorrenciaListView.as_view(), name="ocorrencia_list"),
    # Criação (EXISTENTE)
    path("nova/", OcorrenciaCreateView.as_view(), name="ocorrencia_create"),
    # Detalhe (NOVA)
    path("<int:pk>/", OcorrenciaDetailView.as_view(), name="ocorrencia_detail"),
    # Edição (NOVA)
    path("<int:pk>/editar/", OcorrenciaUpdateView.as_view(), name="ocorrencia_update"),
    # Exclusão (NOVA)
    path("<int:pk>/excluir/", OcorrenciaDeleteView.as_view(), name="ocorrencia_delete"),
    # Finalização (EXISTENTE)
    path(
        "finalizar/<int:pk>/",
        views.finalizar_relatorio,
        name="finalizar_relatorio",
    ),
    # Iniciar Dia (EXISTENTE)
    path("iniciar/", views.iniciar_dia, name="iniciar_dia"),
    path('relatorio/<int:pk>/reabrir/', views.reabrir_relatorio, name='reabrir_relatorio'),
    path('relatorio/<int:pk>/reexportar/', views.reexportar_pdf, name='reexportar_pdf'),
    # ...
    path('relatorio/<int:pk>/download/', views.download_pdf_relatorio, name='download_pdf_relatorio'),
    path('listar_materiais_apreendidos/', views.listar_materiais_apreendidos, name='listar_materiais_apreendidos'),
    path('materiais/deletar/<int:apreensao_id>/', views.deletar_materiais_apreendidos, name='apreensao_delete'),
    #filtragem do RPI
    path("relatorios/",RelatorioListView.as_view(),name="relatorio_list"),

]
