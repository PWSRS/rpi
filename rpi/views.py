from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    ListView,
    CreateView,
    DetailView,
    UpdateView,
    DeleteView,
)
from django.urls import reverse_lazy
from django.forms import modelformset_factory
from django.utils import timezone
from django.contrib import messages  # Importante para dar feedback ao usuário

from .models import Ocorrencia, Envolvido, RelatorioDiario
from .forms import OcorrenciaForm, EnvolvidoForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from django.http import HttpResponse
from django.db.models import F, Prefetch

# --- GERENCIAMENTO DO RELATÓRIO ---


# CÓDIGO CORRIGIDO (Finalização e Verificação Robustas)
@login_required
def finalizar_relatorio(request, pk):
    relatorio = get_object_or_404(
        RelatorioDiario, pk=pk, usuario_responsavel=request.user
    )

    if request.method == "POST":

        # 🚨 CORREÇÃO: Usamos a Queryset direta Ocorrencia.objects.filter() para maior robustez.
        ocorrencias_do_relatorio = Ocorrencia.objects.filter(relatorio_diario=relatorio)

        if not ocorrencias_do_relatorio.exists():
            messages.error(
                request,
                f"O Relatório {relatorio.nr_relatorio} não pode ser finalizado: Não possui ocorrências.",
            )
            return redirect("ocorrencia_list")

        # 1. FINALIZAÇÃO NO BANCO DE DADOS
        relatorio.finalizado = True
        relatorio.data_fim = timezone.now()
        relatorio.save()

        # 2. MENSAGEM DE SUCESSO DO BANCO DE DADOS
        messages.success(
            request,
            f"Relatório {relatorio.nr_relatorio} finalizado no banco de dados. Tentando gerar PDF...",
        )

        # 3. Tenta chamar a função WeasyPrint (Descomente este bloco APÓS testar a finalização)
        try:
            return gerar_pdf_relatorio_weasyprint(relatorio)

        except Exception as e:
            # Se houver falha na geração do PDF, captura o erro e redireciona
            messages.error(
                request,
                f"ERRO CRÍTICO NA GERAÇÃO DO PDF! O relatório foi finalizado, mas o PDF FALHOU. Erro: {e}",
            )
            return redirect("ocorrencia_list")

    # Requisição GET ou outra: apenas redireciona
    return redirect("ocorrencia_list")


@login_required
def iniciar_dia(request):
    relatorio_aberto = RelatorioDiario.obter_relatorio_atual(request.user)

    if request.method == "POST" and not relatorio_aberto:
        # Pega o último número do ano atual para incrementar
        ultimo_relatorio = (
            RelatorioDiario.objects.filter(ano_criacao=timezone.now().year)
            .order_by("nr_relatorio")
            .last()
        )

        proximo_numero = (ultimo_relatorio.nr_relatorio + 1) if ultimo_relatorio else 1

        relatorio_aberto = RelatorioDiario.objects.create(
            nr_relatorio=proximo_numero,
            ano_criacao=timezone.now().year,
            data_inicio=timezone.now(),
            data_fim=timezone.now() + timezone.timedelta(hours=24),
            usuario_responsavel=request.user,
        )
        messages.success(request, f"Relatório {proximo_numero} iniciado!")
        return redirect("ocorrencia_create")

    return render(request, "rpi/iniciar_dia.html", {"relatorio": relatorio_aberto})


# --- OCORRÊNCIAS ---


class OcorrenciaListView(LoginRequiredMixin, ListView):
    model = Ocorrencia
    template_name = "rpi/ocorrencia_list.html"
    context_object_name = "ocorrencias"
    ordering = ["-data_hora_fato"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ESTA LINHA É A CHAVE: Ela busca se existe um relatório aberto agora
        context["relatorio_atual"] = RelatorioDiario.obter_relatorio_atual(
            self.request.user
        )
        return context


class OcorrenciaCreateView(LoginRequiredMixin, CreateView):
    model = Ocorrencia
    form_class = OcorrenciaForm
    template_name = "rpi/ocorrencia_form.html"
    success_url = reverse_lazy("ocorrencia_list")

    # 1. SEGURANÇA: Verifica se existe relatório antes de entrar na página
    def dispatch(self, request, *args, **kwargs):
        self.relatorio_atual = RelatorioDiario.obter_relatorio_atual(request.user)
        if not self.relatorio_atual:
            messages.warning(
                request,
                "Você precisa iniciar um relatório antes de cadastrar ocorrências.",
            )
            return redirect("iniciar_dia")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        # Passamos o relatório atual para o template exibir no título (ex: "Relatório 05/2024")
        data["relatorio"] = self.relatorio_atual

        EnvolvidoFormSet = modelformset_factory(
            Envolvido, form=EnvolvidoForm, extra=0, can_delete=True
        )

        if self.request.POST:
            data["envolvido_formset"] = EnvolvidoFormSet(
                self.request.POST, prefix="envolvidos"
            )
        else:
            data["envolvido_formset"] = EnvolvidoFormSet(
                prefix="envolvidos", queryset=Envolvido.objects.none()
            )
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        envolvido_formset = context["envolvido_formset"]

        if envolvido_formset.is_valid():
            # 2. VINCULAÇÃO AUTOMÁTICA:
            # Define o relatório atual na ocorrência antes de salvar no banco
            self.object = form.save(commit=False)
            self.object.relatorio_diario = self.relatorio_atual
            self.object.save()

            # Salva os envolvidos
            instances = envolvido_formset.save(commit=False)
            for instance in instances:
                instance.ocorrencia = self.object
                instance.save()

            # Limpa envolvidos deletados se houver
            for obj in envolvido_formset.deleted_objects:
                obj.delete()

            return redirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))


class OcorrenciaDetailView(LoginRequiredMixin, DetailView):
    """Permite visualizar os detalhes de uma única ocorrência."""

    model = Ocorrencia
    template_name = "rpi/ocorrencia_detail.html"
    context_object_name = "ocorrencia"

    # Permite acessar os envolvidos diretamente no template
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # O 'object' é a Ocorrencia que está sendo visualizada
        context["envolvidos"] = self.object.envolvidos.all()
        return context


class OcorrenciaUpdateView(LoginRequiredMixin, UpdateView):
    """Permite editar uma ocorrência existente, incluindo os involvedos."""

    model = Ocorrencia
    form_class = OcorrenciaForm
    template_name = "rpi/ocorrencia_form.html"  # Reutiliza o template de criação
    success_url = reverse_lazy("ocorrencia_list")

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        # Configura o Formset de Envolvidos, mas agora com os dados existentes (instance=self.object)
        EnvolvidoFormSet = modelformset_factory(
            Envolvido, form=EnvolvidoForm, extra=0, can_delete=True
        )

        if self.request.POST:
            # Popula o formset com dados de POST
            data["envolvido_formset"] = EnvolvidoFormSet(
                self.request.POST,
                prefix="envolvidos",
                queryset=self.object.envolvidos.all(),  # Busca os envolvidos existentes
            )
        else:
            # Popula o formset com os envolvidos da ocorrência (self.object)
            data["envolvido_formset"] = EnvolvidoFormSet(
                prefix="envolvidos", queryset=self.object.envolvidos.all()
            )
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        envolvido_formset = context["envolvido_formset"]

        # 1. Salva a Ocorrência principal
        self.object = form.save()

        # 2. Salva os Envolvidos
        if envolvido_formset.is_valid():
            instances = envolvido_formset.save(commit=False)
            for instance in instances:
                instance.ocorrencia = self.object
                instance.save()

            # Lida com exclusão de envolvidos
            for obj in envolvido_formset.deleted_objects:
                obj.delete()

            messages.success(self.request, "Ocorrência atualizada com sucesso!")
            return redirect(self.get_success_url())
        else:
            # Se o formset falhar na edição, renderiza novamente o formulário com erros
            return self.render_to_response(self.get_context_data(form=form))


class OcorrenciaDeleteView(LoginRequiredMixin, DeleteView):
    """Permite excluir uma ocorrência."""

    model = Ocorrencia
    # Não precisa mais de template_name aqui, pois o POST virá direto do modal da lista.
    success_url = reverse_lazy("ocorrencia_list")

    def form_valid(self, form):
        # A exclusão ocorre automaticamente ao receber o POST
        messages.success(
            self.request, f"Ocorrência {self.object.pk} excluída com sucesso."
        )
        return super().form_valid(form)


def gerar_pdf_relatorio_weasyprint(relatorio_diario):
    """
    Gera um PDF completo do Relatório Diário usando WeasyPrint.
    A função consulta todas as ocorrências (gerais) e as ocorrências CVLI consumadas separadamente,
    pré-processando os dados para simplificar o template HTML.
    """

    # 1. CONSULTA GERAL OTIMIZADA E ORDENADA
    # Esta consulta busca TODAS as ocorrências do relatório, ordenadas por data para a numeração.
    ocorrencias_qs = (
        relatorio_diario.ocorrencias.select_related("natureza", "opm", "opm__municipio")
        .prefetch_related("envolvidos")
        .order_by("data_hora_fato")
    )

    # 2. CONSULTA CVLI CONSUMADO
    # Esta consulta busca apenas os CVLIs consumados, prefetchando SOMENTE as vítimas (tipo_participante='V').
    cvli_qs = (
        Ocorrencia.objects.filter(
            relatorio_diario=relatorio_diario,
            tipo_acao="C",  # Assumindo que 'C' = Consumado
            # Ajuste a lista de naturezas se tiver nomes diferentes no seu banco de dados
            natureza__nome__in=[
                "Homicídio Doloso",
                "Latrocínio",
                "Roubo com Morte",
                "Feminicídio",
                "CVLI Genérico",
            ],
        )
        .select_related("natureza", "opm", "opm__municipio")
        .prefetch_related(
            # Prefetch especial que busca apenas as vítimas para a contagem da tabela
            Prefetch(
                "envolvidos",
                queryset=Envolvido.objects.filter(tipo_participante="V"),
                to_attr="vitimas_cvli",
            )
        )
        .order_by("data_hora_fato")
    )

    # 3. PRÉ-PROCESSAMENTO DE DADOS (AGORA MAIS ROBUSTO CONTRA VALORES NULOS)
    ocorrencias_com_dados = []
    for ocorrencia in ocorrencias_qs:

        # 3.1. TRATAMENTO DA SIGLA OPM (Proteção contra ocorrencia.opm ser None)
        sigla_opm_limpa = "OPM Não Definida"  # Valor Padrão
        if ocorrencia.opm:
            try:
                # Tenta split, se falhar (se ' - ' não existir), usa a sigla inteira.
                sigla_opm_limpa = ocorrencia.opm.sigla.split(" - ")[0]
            except:
                sigla_opm_limpa = ocorrencia.opm.sigla

        # 3.2. TRATAMENTO DO PRIMEIRO ENVOLVIDO (Proteção contra Envolvido ser None)
        primeiro_envolvido_str = ""
        primeiro_envolvido = ocorrencia.envolvidos.first()

        if primeiro_envolvido:
            # Proteção contra campos individuais serem None/Vazios
            nome = getattr(primeiro_envolvido, "nome", "NÃO INFORMADO")
            idade = getattr(primeiro_envolvido, "idade", "??")

            # Pega a descrição de antecedentes de forma segura
            antecedentes_display = (
                "sem antecedentes criminais"
                if primeiro_envolvido.antecedentes == "N"
                else "com antecedentes criminais"
            )

            # Pega a descrição do tipo de participante (usa 'participante' se falhar)
            tipo_participante = (
                primeiro_envolvido.get_tipo_participante_display().lower()
                if primeiro_envolvido.tipo_participante
                else "participante"
            )

            # Monta a frase de forma segura
            primeiro_envolvido_str = (
                f"uma guarnição durante patrulhamento motorizado, em contato com "
                f"a {tipo_participante} "
                f"{nome}, {idade} anos, {antecedentes_display}, "
                f"informou"
            )

        # Cria um objeto simples com todos os dados necessários
        ocorrencias_com_dados.append(
            {
                "ocorrencia": ocorrencia,
                "sigla_opm_limpa": sigla_opm_limpa,
                "primeiro_envolvido_str": primeiro_envolvido_str,
            }
        )

    # 4. MONTAGEM DO CONTEXTO PARA O TEMPLATE
    context = {
        "relatorio": relatorio_diario,
        "ocorrencias": ocorrencias_com_dados,  # Ocorrências para o Sumário e Detalhes
        "cvli_ocorrencias": cvli_qs,  # Ocorrências para a Tabela CVLI
        # 'user': request.user # Pode ser útil para cabeçalhos (se o user não for acessível via relatorio_diario.usuario_responsavel)
    }

    # 5. RENDERIZAÇÃO E GERAÇÃO DO PDF

    # Renderiza o template HTML ('rpi/relatorio_pdf.html')
    html_string = render_to_string("rpi/relatorio_pdf.html", context)

    # Gera o PDF
    pdf_file = HTML(string=html_string).write_pdf()

    # 6. CONFIGURAÇÃO DA RESPOSTA HTTP (Força o download)
    filename = (
        f"Relatorio_{relatorio_diario.nr_relatorio}_{relatorio_diario.ano_criacao}.pdf"
    )
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response
