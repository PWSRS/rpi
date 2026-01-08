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
    RelatorioDetailView,
    InstrumentoListView,
    InstrumentoCreateView,
    InstrumentoUpdateView,
    InstrumentoDeleteView,
    salvar_instrumento_ajax,
    salvar_material_apreendido_ajax,
    MaterialApreendidoTipoCreateView,
    MaterialApreendidoTipoListView,
    MaterialApreendidoTipoUpdateView,
    MaterialApreendidoTipoDeleteView,
    registro_usuario,
)

urlpatterns = [
    # Registro no Sistema
    path("registro/", views.registro_usuario, name="registro"),
    path("gestao/", views.painel_gestao, name="painel_gestao"),
    path("gestao/ativar/<int:user_id>/", views.ativar_policial, name="ativar_policial"),
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
    path("relatorios/<int:pk>/",RelatorioDetailView.as_view(),name="relatorio_detail"),
    #Instrumentos
    path("instrumentos/", InstrumentoListView.as_view(), name="instrumentos"),
    path("instrumentos/novo/", InstrumentoCreateView.as_view(), name="novo_instrumento"),
    path("instrumentos/<int:pk>/editar/", InstrumentoUpdateView.as_view(), name="editar_instrumento"),
    path("instrumentos/<int:pk>/deletar/", InstrumentoDeleteView.as_view(), name="deletar_instrumento"),
    # Add novo instrumento via AJAX
    path("instrumentos/adicionar_ajax/", views.salvar_instrumento_ajax, name="adicionar_instrumento_ajax"),
    #Add Tipo de Material apreendio
    path("tipo_material_apreendido/novo/", MaterialApreendidoTipoCreateView.as_view(), name="create_material_apreendido_tipo"),
    path("tipo_material_apreendido/listar/", MaterialApreendidoTipoListView.as_view(), name="list_material_apreendido_tipo"),
    path("tipo_material_apreendido/<int:pk>/editar/", MaterialApreendidoTipoUpdateView.as_view(), name="update_material_apreendido_tipo"),
    path("material_apreendido/<int:pk>/deletar/", MaterialApreendidoTipoDeleteView.as_view(), name="delete_material_apreendido_tipo"),
    # Add novo material apreendido via AJAX
    path("material_apreendido/adicionar_ajax/",views.salvar_material_apreendido_ajax,name="adicionar_material_apreendido_ajax"),
]   
    
