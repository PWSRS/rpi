from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.forms import modelformset_factory

from .models import Ocorrencia, Envolvido
from .forms import OcorrenciaForm, EnvolvidoForm


# View para listar todas as ocorrências
class OcorrenciaListView(ListView):
    model = Ocorrencia
    template_name = "rpi/ocorrencia_list.html"
    context_object_name = "ocorrencias"
    ordering = ["-data_hora_fato"]  # Ordena pela data mais recente


# View para criar uma nova ocorrência
class OcorrenciaCreateView(CreateView):
    model = Ocorrencia
    form_class = OcorrenciaForm
    template_name = "rpi/ocorrencia_form.html"
    success_url = reverse_lazy(
        "ocorrencia_list"
    )  # Redireciona para a lista após sucesso

    # Este método é chamado para dar contexto ao template
    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        # Cria um Formset para lidar com múltiplos envolvidos no mesmo formulário
        EnvolvidoFormSet = modelformset_factory(
            Envolvido, form=EnvolvidoForm, extra=3, can_delete=True
        )

        # Se for um POST (enviando dados), tenta validar o formset
        if self.request.POST:
            data["envolvido_formset"] = EnvolvidoFormSet(
                self.request.POST, prefix="envolvidos"
            )
        else:
            # Se for GET (primeira vez), inicializa o formset vazio
            data["envolvido_formset"] = EnvolvidoFormSet(
                prefix="envolvidos", queryset=Envolvido.objects.none()
            )
        return data

    # Este método é chamado após a validação do formulário principal
    def form_valid(self, form):
        context = self.get_context_data()
        envolvido_formset = context["envolvido_formset"]

        # Se o formulário principal e o formset de envolvidos forem válidos
        if envolvido_formset.is_valid():
            # 1. Salva a Ocorrencia principal
            self.object = form.save()

            # 2. Salva o Formset, ligando cada Envolvido à Ocorrencia recém-criada
            instances = envolvido_formset.save(commit=False)
            for instance in instances:
                instance.ocorrencia = self.object  # Define a Foreign Key
                instance.save()

            return redirect(self.get_success_url())

        # Se o formset de envolvidos falhar, retorna o formulário com erros
        else:
            return self.render_to_response(self.get_context_data(form=form))
