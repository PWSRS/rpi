# 1. Bibliotecas padrão do Python (Standard Library)
import urllib.parse
import urllib.request
from datetime import datetime

# 2. Bibliotecas de terceiros (Third-party)
from weasyprint import HTML, CSS

# 3. Framework Django - Core, Modelos e Banco de Dados
from django.conf import settings
from django.db import transaction
from django.db.models import F, Prefetch
from django.http import HttpResponse
from django.utils import timezone

# 4. Django - Views, Mixins e Decoradores
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    ListView,
    CreateView,
    DetailView,
    UpdateView,
    DeleteView,
)

# 5. Django - URLs e Templates
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.contrib.staticfiles.finders import find

# 6. Django - Formulários e Formsets
from django.forms import modelformset_factory, inlineformset_factory

# 7. Importações do seu App Local (Internal)
from .models import Ocorrencia, Envolvido, RelatorioDiario, Apreensao
from .forms import (
    OcorrenciaForm,
    EnvolvidoForm,
    EnvolvidoFormSet,
    ApreensaoForm,
    ApreensaoFormSet,
)

# --- GERENCIAMENTO DO RELATÓRIO ---


# CÓDIGO CORRIGIDO (Finalização e Verificação Robustas)
@login_required
def finalizar_relatorio(request, pk):
    relatorio = get_object_or_404(
        RelatorioDiario, pk=pk, usuario_responsavel=request.user
    )

    if request.method == "POST":
        if not relatorio.ocorrencias.exists():
            messages.error(request, "Não possui ocorrências.")
            return redirect("ocorrencia_list")

        # 1. FINALIZAÇÃO
        relatorio.finalizado = True
        relatorio.data_fim = timezone.now()
        relatorio.save()

        messages.success(
            request, f"Relatório {relatorio.nr_relatorio} finalizado com sucesso!"
        )

        # 2. REDIRECIONA COM PARÂMETRO PARA DISPARAR O DOWNLOAD
        url = reverse("ocorrencia_list")
        return redirect(f"{url}?download_id={relatorio.pk}")

    return redirect("ocorrencia_list")


def download_pdf_relatorio(request, pk):
    relatorio = get_object_or_404(RelatorioDiario, pk=pk)
    return gerar_pdf_relatorio_weasyprint(relatorio)


# NOVO: Reverte o status de finalização do relatório para permitir a edição
@login_required
def reabrir_relatorio(request, pk):
    """
    Permite que um usuário reabra um relatório finalizado (finalizado=False)
    para corrigir ou adicionar ocorrências.
    """
    # 🚨 Buscamos o objeto garantindo que o usuário seja o responsável
    relatorio = get_object_or_404(
        RelatorioDiario, pk=pk, usuario_responsavel=request.user
    )

    if request.method == "POST":
        # 1. Reverte o estado de finalização
        relatorio.finalizado = False
        relatorio.data_fim = None  # Limpa a data de finalização
        relatorio.save()

        # 2. Mensagem e redirecionamento com Cache Buster (para atualizar o status na lista)
        messages.warning(
            request,
            f"Relatório {relatorio.nr_relatorio} foi REABERTO para edição. Lembre-se de FINALIZAR novamente!",
        )
        url_destino = reverse("ocorrencia_list")
        url_destino_com_cache_buster = (
            f"{url_destino}?refresh={datetime.now().timestamp()}"
        )

        return redirect(url_destino_com_cache_buster)

    # Se for GET, apenas redireciona
    return redirect("ocorrencia_list")


# NOVO: Permite reexportar o PDF mesmo que o relatório esteja finalizado
@login_required
def reexportar_pdf(request, pk):
    """
    Gera o PDF do Relatório Diário, ignorando o status 'finalizado'.
    Retorna o HttpResponse do PDF para download.
    """
    relatorio = get_object_or_404(
        RelatorioDiario, pk=pk, usuario_responsavel=request.user
    )

    # 1. Tenta gerar e retornar o PDF (Download)
    try:
        # A função gerar_pdf_relatorio_weasyprint já retorna o HttpResponse de download
        pdf_response = gerar_pdf_relatorio_weasyprint(relatorio)
        messages.info(request, "PDF reexportado com sucesso!")
        return pdf_response

    except Exception as e:
        # Se houver falha na geração do PDF, captura o erro e redireciona
        messages.error(
            request,
            f"Falha ao reexportar o PDF. O relatório foi reaberto e não finalizado. Erro: {e}",
        )
        print(f"ERRO DE REEXPORTAÇÃO DE PDF: {e}")

        # Redireciona com cache-buster
        url_destino = reverse("ocorrencia_list")
        url_destino_com_cache_buster = (
            f"{url_destino}?refresh={datetime.now().timestamp()}"
        )
        return redirect(url_destino_com_cache_buster)


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

        # 🚨 CORREÇÃO CRÍTICA: Não use o método que filtra 'finalizado=False'.
        # Busque o ÚLTIMO relatório do usuário, independentemente do status.
        context["relatorio_atual"] = (
            RelatorioDiario.objects.filter(usuario_responsavel=self.request.user)
            .order_by("-data_inicio")
            .first()
        )  # <-- Apenas o mais recente, aberto ou fechado.

        # O resto do template (que usa `{% if not relatorio_atual.finalizado %}` ou `{% else %}`)
        # fará o trabalho de decidir qual alerta mostrar.

        return context


class OcorrenciaCreateView(LoginRequiredMixin, CreateView):
    model = Ocorrencia
    form_class = OcorrenciaForm
    template_name = "rpi/ocorrencia_form.html"
    success_url = reverse_lazy("ocorrencia_list")

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

        # Definição das fábricas de Formset
        EnvolvidoFormSet = inlineformset_factory(
            self.model, Envolvido, form=EnvolvidoForm, extra=0, can_delete=True
        )
        ApreensaoFormSet = inlineformset_factory(
            self.model, Apreensao, form=ApreensaoForm, extra=0, can_delete=True
        )

        if self.request.POST:
            data["envolvido_formset"] = EnvolvidoFormSet(
                self.request.POST, prefix="envolvidos"
            )
            data["apreensao_formset"] = ApreensaoFormSet(
                self.request.POST, prefix="apreensoes"
            )
        else:
            # Em vez de criar um objeto fictício, passamos a instância como None (padrão do CreateView)
            data["envolvido_formset"] = EnvolvidoFormSet(
                instance=self.object, prefix="envolvidos"
            )
            data["apreensao_formset"] = ApreensaoFormSet(
                instance=self.object, prefix="apreensoes"
            )
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        envolvido_formset = context["envolvido_formset"]
        apreensao_formset = context["apreensao_formset"]

        # Log de depuração (aparecerá no seu terminal/console)
        print(f"Envolvidos válidos: {envolvido_formset.is_valid()}")
        print(f"Apreensões válidas: {apreensao_formset.is_valid()}")

        if envolvido_formset.is_valid() and apreensao_formset.is_valid():
            with transaction.atomic():
                self.object = form.save(commit=False)
                self.object.relatorio_diario = self.relatorio_atual
                self.object.save()

                envolvido_formset.instance = self.object
                envolvido_formset.save()

                apreensao_formset.instance = self.object
                apreensao_formset.save()

            messages.success(self.request, "Ocorrência salva com sucesso!")
            return redirect(self.get_success_url())
        else:
            # Se cair aqui, o erro aparecerá no topo da página
            messages.error(
                self.request,
                "Erro na validação dos dados dos participantes ou materiais.",
            )
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    envolvido_formset=envolvido_formset,
                    apreensao_formset=apreensao_formset,
                )
            )


class OcorrenciaDetailView(LoginRequiredMixin, DetailView):
    model = Ocorrencia
    template_name = "rpi/ocorrencia_detail.html"
    context_object_name = "ocorrencia"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 'self.object' é a instância da Ocorrencia atual
        ocorrencia = self.object

        # Buscamos todos os envolvidos ligados a esta ocorrência específica
        context["envolvidos"] = ocorrencia.envolvidos.all()

        # Buscamos todas as apreensões ligadas a esta ocorrência específica
        # select_related ajuda a trazer o nome do material de forma eficiente
        context["apreensoes"] = ocorrencia.apreensoes.select_related(
            "material_tipo"
        ).all()

        return context


class OcorrenciaUpdateView(LoginRequiredMixin, UpdateView):
    model = Ocorrencia
    form_class = OcorrenciaForm
    template_name = "rpi/ocorrencia_form.html"
    success_url = reverse_lazy("ocorrencia_list")

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        # Como EnvolvidoFormSet e ApreensaoFormSet já são inline_formsets
        # definidos no forms.py, basta instanciá-los passando a instância (self.object)
        if self.request.POST:
            data["envolvido_formset"] = EnvolvidoFormSet(
                self.request.POST, instance=self.object, prefix="envolvidos"
            )
            data["apreensao_formset"] = ApreensaoFormSet(
                self.request.POST, instance=self.object, prefix="apreensoes"
            )
        else:
            data["envolvido_formset"] = EnvolvidoFormSet(
                instance=self.object, prefix="envolvidos"
            )
            data["apreensao_formset"] = ApreensaoFormSet(
                instance=self.object, prefix="apreensoes"
            )
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        envolvido_formset = context["envolvido_formset"]
        apreensao_formset = context["apreensao_formset"]

        if (
            form.is_valid()
            and envolvido_formset.is_valid()
            and apreensao_formset.is_valid()
        ):
            # Salva a ocorrência
            self.object = form.save()
            # Salva os formsets (o inline já cuida dos IDs e FKs automaticamente)
            envolvido_formset.save()
            apreensao_formset.save()

            messages.success(self.request, "Ocorrência atualizada com sucesso!")
            return redirect(self.get_success_url())
        else:
            # Caso algum formset seja inválido, volta para a página exibindo os erros
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
    # --- FUNÇÃO AUXILIAR PARA FORMATO MILITAR (Ex: 23DEZ25) ---
    def formatar_data_militar(data):
        if not data:
            return ""
        meses = {
            1: "JAN",
            2: "FEV",
            3: "MAR",
            4: "ABR",
            5: "MAI",
            6: "JUN",
            7: "JUL",
            8: "AGO",
            9: "SET",
            10: "OUT",
            11: "NOV",
            12: "DEZ",
        }
        dia = data.strftime("%d")
        hora_minuto = data.strftime("%H%M")  # Adiciona Hora e Minuto
        mes = meses[data.month]
        ano = data.strftime("%y")

        return f"{dia}{hora_minuto}{mes}{ano}"

    # 1. CONSULTA GERAL OTIMIZADA E ORDENADA
    ocorrencias_qs = (
        relatorio_diario.ocorrencias.select_related("natureza", "opm", "opm__municipio")
        .prefetch_related("envolvidos")
        .order_by("data_hora_fato")
    )

    # 2. CONSULTA CVLI CONSUMADO
    cvli_qs = (
        Ocorrencia.objects.filter(
            relatorio_diario=relatorio_diario,
            tipo_acao="C",
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
            Prefetch(
                "envolvidos",
                queryset=Envolvido.objects.filter(tipo_participante="V"),
                to_attr="vitimas_cvli",
            )
        )
        .order_by("data_hora_fato")
    )

    # 3. PRÉ-PROCESSAMENTO DE DADOS
    ocorrencias_com_dados = []
    for ocorrencia in ocorrencias_qs:
        sigla_opm_limpa = "OPM Não Definida"
        if ocorrencia.opm:
            try:
                sigla_opm_limpa = ocorrencia.opm.sigla.split(" - ")[0]
            except:
                sigla_opm_limpa = ocorrencia.opm.sigla

        primeiro_envolvido_str = ""
        primeiro_envolvido = ocorrencia.envolvidos.first()

        if primeiro_envolvido:
            nome = getattr(primeiro_envolvido, "nome", "NÃO INFORMADO")
            idade = getattr(primeiro_envolvido, "idade", "??")
            antecedentes_display = (
                "sem antecedentes criminais"
                if primeiro_envolvido.antecedentes == "N"
                else "com antecedentes criminais"
            )
            tipo_participante = (
                primeiro_envolvido.get_tipo_participante_display().lower()
                if primeiro_envolvido.tipo_participante
                else "participante"
            )
            primeiro_envolvido_str = (
                f"uma guarnição durante patrulhamento motorizado, em contato com "
                f"a {tipo_participante} "
                f"{nome}, {idade} anos, {antecedentes_display}, "
                f"informou"
            )

        ocorrencias_com_dados.append(
            {
                "ocorrencia": ocorrencia,
                "sigla_opm_limpa": sigla_opm_limpa,
                "primeiro_envolvido_str": primeiro_envolvido_str,
            }
        )

    # 4. MONTAGEM DO CONTEXTO PARA O TEMPLATE
    logo_file_path = find("rpi/img/logo.png")
    logo_uri = ""
    if logo_file_path:
        logo_uri = urllib.parse.urljoin(
            "file:", urllib.request.pathname2url(logo_file_path)
        )

    css_file_path = find("rpi/css/rpi.css")
    css_uri = ""
    if css_file_path:
        css_uri = urllib.parse.urljoin(
            "file:", urllib.request.pathname2url(css_file_path)
        )

    # --- DATAS FORMATADAS PARA O CONTEXTO ---
    data_inicio_militar = formatar_data_militar(relatorio_diario.data_inicio)
    data_fim_militar = formatar_data_militar(relatorio_diario.data_fim)

    context = {
        "relatorio": relatorio_diario,
        "data_inicio_militar": data_inicio_militar,  # <-- Enviando para o HTML
        "data_fim_militar": data_fim_militar,  # <-- Enviando para o HTML
        "ocorrencias": ocorrencias_com_dados,
        "cvli_ocorrencias": cvli_qs,
        "logo_uri": logo_uri,
        "css_uri": css_uri,
    }

    # 5. RENDERIZAÇÃO E GERAÇÃO DO PDF
    html_string = render_to_string("rpi/relatorio_pdf.html", context)

    static_root = settings.STATIC_ROOT
    if not static_root:
        try:
            static_root = find("rpi/css/rpi.css").replace("rpi/css/rpi.css", "")
        except:
            static_root = None

    pdf_file = HTML(string=html_string, base_url=static_root).write_pdf()

    # 6. CONFIGURAÇÃO DA RESPOSTA HTTP
    data_formatada = relatorio_diario.data_inicio.strftime("%d.%m.%Y")
    filename = f"RELATÓRIO PERIÓDICO DE INTELIGÊNCIA Nº {relatorio_diario.nr_relatorio} - ARI SUL - {data_formatada}.pdf"

    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response
