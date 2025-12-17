# SeuApp/urls.py
from django.urls import path
from .views import OcorrenciaListView, OcorrenciaCreateView

urlpatterns = [
    # /ocorrencias/
    path("", OcorrenciaListView.as_view(), name="ocorrencia_list"),
    # /ocorrencias/nova/
    path("nova/", OcorrenciaCreateView.as_view(), name="ocorrencia_create"),
]
