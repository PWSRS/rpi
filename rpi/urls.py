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
]
