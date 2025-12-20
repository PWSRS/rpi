from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    ListView,
    CreateView,
    DetailView,
    UpdateView,
    DeleteView,
)
from django.urls import reverse_lazy
from django.forms import modelformset_factory, inlineformset_factory
from django.utils import timezone
from django.contrib import messages  # Importante para dar feedback ao usuário

from .models import Ocorrencia, Envolvido, RelatorioDiario, RelatorioDiario, Apreensao
from .forms import OcorrenciaForm, EnvolvidoForm, ApreensaoForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from django.http import HttpResponse
from django.db.models import F, Prefetch
from django.urls import reverse
from datetime import datetime

# --- GERENCIAMENTO DO RELATÓRIO ---


# CÓDIGO CORRIGIDO (Finalização e Verificação Robustas)
@login_required
def finalizar_relatorio(request, pk):
    relatorio = get_object_or_404(
        RelatorioDiario, pk=pk, usuario_responsavel=request.user
    )

    if request.method == "POST":

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

        # 🚨 ALTERAÇÃO CRÍTICA AQUI 🚨
        try:
            # 2. Tenta gerar e retornar o PDF (Download)
            pdf_response = gerar_pdf_relatorio_weasyprint(relatorio)

            # Se a geração for bem-sucedida, o download é iniciado.
            # Nenhuma mensagem de sucesso é necessária aqui, pois o download é a confirmação.
            return pdf_response

        except Exception as e:
            # Se houver falha na geração do PDF, captura o erro e continua o fluxo de redirecionamento.
            messages.error(
                request,
                f"ERRO CRÍTICO NA GERAÇÃO DO PDF! O relatório foi finalizado, mas o PDF FALHOU. Erro: {e}",
            )
            # 🚨 Não precisa de "return redirect" aqui, pois o fluxo cairá no redirecionamento final.
            print(f"ERRO DE PDF NO CONSOLE: {e}")  # Debugging no console do servidor

        # 3. REDIRECIONAMENTO COM CACHE BUSTER
        # Este redirecionamento é alcançado se o PDF falhou (o 'except' foi executado).
        # Ele garante que o status do relatório (agora finalizado) seja atualizado.

        # 🚨 MENSAGEM DE SUCESSO (SÓ É EXIBIDA se NÃO HOUVE EXCEÇÃO, mas queremos que ela apareça)
        # Se você chegou aqui e não houve erro no PDF, a intenção era redirecionar.
        # Adicione uma mensagem de sucesso aqui caso não tenha havido erro de PDF
        if not messages.get_messages(
            request
        ):  # Verifica se já existe uma mensagem (de erro)
            messages.success(
                request,
                f"Relatório {relatorio.nr_relatorio} finalizado com sucesso. Por favor, verifique o download do PDF.",
            )

        # Configura o Cache Buster
        url_destino = reverse("ocorrencia_list")
        url_destino_com_cache_buster = (
            f"{url_destino}?refresh={datetime.now().timestamp()}"
        )

        return redirect(url_destino_com_cache_buster)

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
        data["relatorio"] = self.relatorio_atual

        # --- ENVOLVIDO FORMSET ---
        EnvolvidoFormSet = inlineformset_factory(
            self.model, Envolvido, form=EnvolvidoForm, extra=1, can_delete=True
        )

        # 🚨 NOVO: APREENSÃO FORMSET 🚨
        ApreensaoFormSet = inlineformset_factory(
            self.model, Apreensao, form=ApreensaoForm, extra=0, can_delete=True
        )

        if self.request.POST:
            # Popula com dados do POST
            # Não é necessário o 'queryset=...' aqui
            data["envolvido_formset"] = EnvolvidoFormSet(
                self.request.POST, prefix="envolvidos"
            )
            data["apreensao_formset"] = ApreensaoFormSet(
                self.request.POST, prefix="apreensoes"
            )
        else:
            # Popula com QuerySets vazias (ou vazia para inline)
            # Para CreateView, a instância é None, mas o inlineformset lida com isso.
            # É melhor criar um objeto vazio para satisfazer o inlineformset
            OcorrenciaEmpty = self.model()

            data["envolvido_formset"] = EnvolvidoFormSet(
                instance=OcorrenciaEmpty, prefix="envolvidos"
            )
            data["apreensao_formset"] = ApreensaoFormSet(
                instance=OcorrenciaEmpty, prefix="apreensoes"
            )
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        envolvido_formset = context["envolvido_formset"]
        apreensao_formset = context["apreensao_formset"]

        # 🚨 Verifica a validade de AMBOS os formsets
        if envolvido_formset.is_valid() and apreensao_formset.is_valid():

            # 1. Salva a Ocorrência principal (sem commit=False)
            self.object = form.save(commit=False)
            self.object.relatorio_diario = self.relatorio_atual
            self.object.save()

            # 2. Salva os Envolvidos e Apreensões (O inlineformset_factory FAZ O LOOP E VINCULA A FK)
            # Você precisa atribuir a instância principal ANTES do save()
            envolvido_formset.instance = self.object
            envolvido_formset.save()

            apreensao_formset.instance = self.object
            apreensao_formset.save()

            messages.success(
                self.request, "Ocorrência e materiais cadastrados com sucesso!"
            )
            return redirect(self.get_success_url())
        else:
            # Se algum formset for inválido, renderiza novamente
            # O get_context_data já popula os formsets com os dados do POST
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
    """Permite editar uma ocorrência existente, incluindo os involvedos e apreensões."""

    model = Ocorrencia
    form_class = OcorrenciaForm
    template_name = "rpi/ocorrencia_form.html"  # Reutiliza o template de criação
    success_url = reverse_lazy("ocorrencia_list")

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        # Configura o Formset de Envolvidos
        EnvolvidoFormSet = modelformset_factory(
            Envolvido, form=EnvolvidoForm, extra=0, can_delete=True
        )

        # 🚨 NOVO: APREENSÃO FORMSET 🚨
        ApreensaoFormSet = modelformset_factory(
            Apreensao, form=ApreensaoForm, extra=1, can_delete=True
        )

        if self.request.POST:
            # Popula formsets com dados de POST
            data["envolvido_formset"] = EnvolvidoFormSet(
                self.request.POST,
                prefix="envolvidos",
                queryset=self.object.envolvidos.all(),  # Dados existentes
            )
            data["apreensao_formset"] = ApreensaoFormSet(  # NOVO
                self.request.POST,
                prefix="apreensoes",
                queryset=self.object.apreensoes.all(),  # Dados existentes
            )
        else:
            # Popula formsets com dados existentes
            data["envolvido_formset"] = EnvolvidoFormSet(
                prefix="envolvidos", queryset=self.object.envolvidos.all()
            )
            data["apreensao_formset"] = ApreensaoFormSet(  # NOVO
                prefix="apreensoes", queryset=self.object.apreensoes.all()
            )
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        envolvido_formset = context["envolvido_formset"]
        apreensao_formset = context["apreensao_formset"]  # NOVO: Obtém o formset

        # 1. Salva a Ocorrência principal (sempre primeiro)
        self.object = form.save()

        # 🚨 Verifica a validade de AMBOS os formsets antes de salvar 🚨
        if envolvido_formset.is_valid() and apreensao_formset.is_valid():

            # 2. Salva os Envolvidos (e lida com exclusão)
            instances_env = envolvido_formset.save(commit=False)
            for instance in instances_env:
                instance.ocorrencia = self.object
                instance.save()
            for obj in envolvido_formset.deleted_objects:
                obj.delete()

            # 3. Salva as Apreensões (e lida com exclusão)
            instances_apr = apreensao_formset.save(commit=False)
            for instance in instances_apr:
                instance.ocorrencia = self.object
                instance.save()
            for obj in apreensao_formset.deleted_objects:
                obj.delete()

            messages.success(
                self.request, "Ocorrência e materiais atualizados com sucesso!"
            )
            return redirect(self.get_success_url())
        else:
            # Se algum formset falhar na edição, renderiza novamente o formulário com erros
            messages.error(
                self.request, "Erro na validação de envolvidos ou apreensões."
            )
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
