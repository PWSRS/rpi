# 1. Bibliotecas padrão do Python (Standard Library)
import urllib.parse
import urllib.request
from datetime import datetime, time
from pathlib import Path
from collections import Counter


# 2. Bibliotecas de terceiros (Third-party)
from weasyprint import HTML, CSS

# 3. Framework Django - Core, Modelos e Banco de Dados
from django.conf import settings
from django.db import transaction
from django.db.models import F, Prefetch
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date

# 4. Django - Views, Mixins e Decoradores
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.staticfiles.finders import find
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
from .models import Ocorrencia, Envolvido, RelatorioDiario, Apreensao, OcorrenciaImagem, Instrumento
from .forms import (
    OcorrenciaForm,
    EnvolvidoForm,
    EnvolvidoFormSet,
    ApreensaoForm,
    ApreensaoFormSet,
    ImagemFormSet,
    InstrumentoForm,
)

# --- GERENCIAMENTO DO RELATÓRIO ---


# CÓDIGO CORRIGIDO (Finalização e Verificação Robustas)
@login_required
def finalizar_relatorio(request, pk):
    relatorio = get_object_or_404(
        RelatorioDiario, pk=pk, usuario_responsavel=request.user
    )

    if request.method == "POST":
        # Trava de segurança: impede finalizar sem dados
        if not relatorio.ocorrencias.exists():
            messages.error(
                request, "Não é possível finalizar um relatório sem ocorrências."
            )
            return redirect("ocorrencia_list")

        relatorio.finalizado = True
        # NÃO alteramos data_fim aqui, mantemos as 07:00 fixas
        relatorio.save()

        messages.success(
            request,
            f"Relatório {relatorio.nr_relatorio}/{relatorio.ano_criacao} finalizado com sucesso!",
        )
        return redirect("ocorrencia_list")

    return redirect("ocorrencia_list")


def download_pdf_relatorio(request, pk):
    """
    View que aciona a função de geração do PDF.
    Recebe 'request' e 'pk' da URL.
    """
    relatorio = get_object_or_404(
        RelatorioDiario, pk=pk, usuario_responsavel=request.user
    )

    # CORREÇÃO: Passa 'relatorio' e 'request' para a função de geração de PDF
    response = gerar_pdf_relatorio_weasyprint(relatorio, request)

    # O Content-Disposition 'inline' na função de PDF deve fazer o navegador abrir a nova guia.
    return response


# NOVO: Reverte o status de finalização do relatório para permitir a edição
@login_required
def reabrir_relatorio(request, pk):
    relatorio = get_object_or_404(
        RelatorioDiario, pk=pk, usuario_responsavel=request.user
    )

    if request.method == "POST":
        relatorio.finalizado = False
        # RETIFICAÇÃO CRÍTICA: Removido 'data_fim = None'
        # Mantemos a data_fim original (07:00 do dia seguinte) para não invalidar o banco
        relatorio.save()

        messages.warning(
            request,
            f"Relatório {relatorio.nr_relatorio} foi REABERTO para edição. Lembre-se de FINALIZAR novamente!",
        )
        return redirect("ocorrencia_list")

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
        # CORREÇÃO: Passa o 'request' para a função de geração de PDF
        pdf_response = gerar_pdf_relatorio_weasyprint(relatorio, request)
        messages.info(request, "PDF reexportado com sucesso!")
        return pdf_response

    except Exception as e:
        messages.error(
            request,
            f"Falha ao reexportar o PDF. Erro interno: {e}",
        )
        # O redirecionamento com cache buster é desnecessário aqui, basta redirecionar
        return redirect("ocorrencia_list")


@login_required
def iniciar_dia(request):
    # BUSCA EXPLÍCITA: Verifica se já existe um relatório ABERTO para o usuário
    relatorio_aberto = RelatorioDiario.objects.filter(
        usuario_responsavel=request.user, finalizado=False
    ).last()

    if request.method == "POST" and not relatorio_aberto:
        agora = timezone.now()

        # 1. FIXA O PERÍODO: 07:00 de hoje até 07:00 de amanhã
        inicio_plantao = timezone.make_aware(
            datetime.combine(agora.date(), time(7, 0, 0))
        )
        fim_plantao = inicio_plantao + timezone.timedelta(days=1)

        # 2. LÓGICA DE INCREMENTO ANUAL (Reset automático)
        ano_atual = agora.year
        ultimo = (
            RelatorioDiario.objects.filter(ano_criacao=ano_atual)
            .order_by("nr_relatorio")
            .last()
        )
        proximo_numero = (ultimo.nr_relatorio + 1) if ultimo else 1

        # 3. CRIAÇÃO DO RELATÓRIO
        relatorio_aberto = RelatorioDiario.objects.create(
            nr_relatorio=proximo_numero,
            ano_criacao=ano_atual,
            data_inicio=inicio_plantao,
            data_fim=fim_plantao,
            usuario_responsavel=request.user,
            finalizado=False,  # Garante que inicie aberto
        )

        messages.success(
            request, f"Relatório {proximo_numero}/{ano_atual} iniciado com sucesso!"
        )
        return redirect("ocorrencia_create")

    return render(request, "rpi/iniciar_dia.html", {"relatorio": relatorio_aberto})


# --- OCORRÊNCIAS ---


class OcorrenciaListView(LoginRequiredMixin, ListView):
    model = Ocorrencia
    template_name = "rpi/ocorrencia_list.html"
    context_object_name = "ocorrencias"

    def get_queryset(self):
        # 1. Busca APENAS o relatório que está ABERTO agora
        relatorio_aberto = RelatorioDiario.objects.filter(
            usuario_responsavel=self.request.user, finalizado=False
        ).last()

        # 2. Se houver um aberto, mostra apenas as ocorrências dele
        if relatorio_aberto:
            return relatorio_aberto.ocorrencias.all().order_by("-data_hora_fato")

        # 3. Se NÃO houver nenhum aberto (plantão finalizado e nenhum novo iniciado),
        # você pode optar por mostrar as do ÚLTIMO finalizado para não ver a tela vazia,
        # OU retornar vazio para forçar o início de um novo dia.
        ultimo_finalizado = (
            RelatorioDiario.objects.filter(
                usuario_responsavel=self.request.user, finalizado=True
            )
            .order_by("-data_inicio")
            .first()
        )

        if ultimo_finalizado:
            return ultimo_finalizado.ocorrencias.all().order_by("-data_hora_fato")

        return Ocorrencia.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Busca o mesmo relatório para o template decidir se mostra os botões de Editar/Excluir
        relatorio = (
            RelatorioDiario.objects.filter(
                usuario_responsavel=self.request.user, finalizado=False
            ).last()
            or RelatorioDiario.objects.filter(
                usuario_responsavel=self.request.user, finalizado=True
            )
            .order_by("-data_inicio")
            .first()
        )

        context["relatorio_atual"] = relatorio
        return context


class OcorrenciaCreateView(LoginRequiredMixin, CreateView):
    model = Ocorrencia
    form_class = OcorrenciaForm
    template_name = "rpi/ocorrencia_form.html"
    success_url = reverse_lazy("ocorrencia_list")

    def dispatch(self, request, *args, **kwargs):
        # Usa o filtro de finalizado=False para ter certeza que o relatório permite novas inserções
        self.relatorio_atual = RelatorioDiario.objects.filter(
            usuario_responsavel=request.user, finalizado=False
        ).last()

        if not self.relatorio_atual:
            messages.warning(
                request, "Não há relatório aberto. Inicie um novo plantão."
            )
            return redirect("iniciar_dia")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["relatorio"] = self.relatorio_atual

        # Definição das fábricas de Formset (Mantidas na View, conforme seu código)
        EnvolvidoFormSet = inlineformset_factory(
            self.model,
            Envolvido,
            form=EnvolvidoForm,
            extra=1,
            can_delete=True,  # Alterei extra=0 para 1 para facilitar
        )
        ApreensaoFormSet = inlineformset_factory(
            self.model,
            Apreensao,
            form=ApreensaoForm,
            extra=1,
            can_delete=True,  # Alterei extra=0 para 1
        )

        # NOVO: Fábrica do Formset de Imagens (Definida na View, conforme seu código)
        OcorrenciaImagemFormSet = inlineformset_factory(
            self.model,
            OcorrenciaImagem,
            fields=("imagem", "legenda"),
            extra=1,
            can_delete=True,
        )

        if self.request.POST:
            data["envolvido_formset"] = EnvolvidoFormSet(
                self.request.POST, prefix="envolvidos"
            )
            data["apreensao_formset"] = ApreensaoFormSet(
                self.request.POST, prefix="apreensoes"
            )
            # CRÍTICO: Instancia o Formset de Imagens. Inclui request.FILES.
            data["imagem_formset"] = OcorrenciaImagemFormSet(
                self.request.POST, self.request.FILES, prefix="imagens"
            )
        else:
            # Em vez de criar um objeto fictício, passamos a instância como None (self.object é None)
            data["envolvido_formset"] = EnvolvidoFormSet(
                instance=self.object, prefix="envolvidos"
            )
            data["apreensao_formset"] = ApreensaoFormSet(
                instance=self.object, prefix="apreensoes"
            )
            # NOVO: Instancia o Formset de Imagens
            data["imagem_formset"] = OcorrenciaImagemFormSet(
                instance=self.object, prefix="imagens"
            )
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        envolvido_formset = context["envolvido_formset"]
        apreensao_formset = context["apreensao_formset"]
        imagem_formset = context["imagem_formset"]  # NOVO: Adiciona o formset de imagem

        # Log de depuração (opcional, pode remover depois)
        print(f"Envolvidos válidos: {envolvido_formset.is_valid()}")
        print(f"Apreensões válidas: {apreensao_formset.is_valid()}")
        print(f"Imagens válidas: {imagem_formset.is_valid()}")  # NOVO: Log

        if (
            envolvido_formset.is_valid()
            and apreensao_formset.is_valid()
            and imagem_formset.is_valid()  # CRÍTICO: Validação do formset de imagem
        ):
            with transaction.atomic():
                self.object = form.save(commit=False)
                self.object.relatorio_diario = self.relatorio_atual
                self.object.save()

                envolvido_formset.instance = self.object
                envolvido_formset.save()

                apreensao_formset.instance = self.object
                apreensao_formset.save()

                imagem_formset.instance = (
                    self.object
                )  # NOVO: Liga as imagens à ocorrência
                imagem_formset.save()  # NOVO: Salva as imagens

            messages.success(self.request, "Ocorrência salva com sucesso!")
            return redirect(self.get_success_url())
        else:
            # Se cair aqui, o erro aparecerá no topo da página
            messages.error(
                self.request,
                "Erro na validação dos dados dos participantes, materiais ou imagens.",
            )
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    envolvido_formset=envolvido_formset,
                    apreensao_formset=apreensao_formset,
                    imagem_formset=imagem_formset,  # CRÍTICO: Passar o formset de imagem
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
        context["apreensoes"] = ocorrencia.apreensoes.select_related(
            "material_tipo"
        ).all()

        # NOVO: Buscamos todas as imagens ligadas a esta ocorrência
        # O nome 'imagens' vem do related_name='imagens' no ForeignKey
        context["imagens"] = ocorrencia.imagens.all()

        return context


class OcorrenciaUpdateView(LoginRequiredMixin, UpdateView):
    model = Ocorrencia
    form_class = OcorrenciaForm
    template_name = "rpi/ocorrencia_form.html"
    success_url = reverse_lazy("ocorrencia_list")

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        # Definição das fábricas de Formset (Mantidas na View, conforme seu código)
        EnvolvidoFormSet = inlineformset_factory(
            self.model, Envolvido, form=EnvolvidoForm, extra=1, can_delete=True
        )
        ApreensaoFormSet = inlineformset_factory(
            self.model, Apreensao, form=ApreensaoForm, extra=1, can_delete=True
        )
        # NOVO: Fábrica do Formset de Imagens (Definida na View, conforme seu código)
        OcorrenciaImagemFormSet = inlineformset_factory(
            self.model,
            OcorrenciaImagem,
            fields=("imagem", "legenda"),
            extra=1,
            can_delete=True,
        )

        if self.request.POST:
            # Instancia Formsets existentes com POST data
            data["envolvido_formset"] = EnvolvidoFormSet(
                self.request.POST, instance=self.object, prefix="envolvidos"
            )
            data["apreensao_formset"] = ApreensaoFormSet(
                self.request.POST, instance=self.object, prefix="apreensoes"
            )
            # CRÍTICO: Instancia Formset de Imagens com request.POST e request.FILES
            data["imagem_formset"] = OcorrenciaImagemFormSet(
                self.request.POST,
                self.request.FILES,
                instance=self.object,
                prefix="imagens",
            )
        else:
            # Instancia Formsets existentes com dados do objeto
            data["envolvido_formset"] = EnvolvidoFormSet(
                instance=self.object, prefix="envolvidos"
            )
            data["apreensao_formset"] = ApreensaoFormSet(
                instance=self.object, prefix="apreensoes"
            )
            # NOVO: Instancia Formset de Imagens
            data["imagem_formset"] = OcorrenciaImagemFormSet(
                instance=self.object, prefix="imagens"
            )
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        envolvido_formset = context["envolvido_formset"]
        apreensao_formset = context["apreensao_formset"]
        imagem_formset = context["imagem_formset"]  # NOVO: Pega o formset

        if (
            form.is_valid()
            and envolvido_formset.is_valid()
            and apreensao_formset.is_valid()
            and imagem_formset.is_valid()  # CRÍTICO: Validação do formset de imagem
        ):
            # Salva a ocorrência
            self.object = form.save()
            # Salva os formsets
            envolvido_formset.save()
            apreensao_formset.save()
            imagem_formset.save()  # NOVO: Salva as imagens (atualizações, exclusões e adições)

            messages.success(self.request, "Ocorrência atualizada com sucesso!")
            return redirect(self.get_success_url())
        else:
            # Caso algum formset seja inválido, volta para a página exibindo os erros
            return self.render_to_response(self.get_context_data(form=form))


class OcorrenciaDeleteView(LoginRequiredMixin, DeleteView):
    """Permite excluir uma ocorrência."""

    model = Ocorrencia
    success_url = reverse_lazy("ocorrencia_list")

    def form_valid(self, form):
        # A exclusão ocorre automaticamente ao receber o POST
        messages.success(
            self.request, f"Ocorrência {self.object.pk} excluída com sucesso."
        )
        return super().form_valid(form)


def listar_materiais_apreendidos(request):
    # Iniciamos com todos os materiais, usando select_related para performance
    materiais = Apreensao.objects.select_related("material_tipo", "ocorrencia").all()

    # Captura as datas vindas do formulário de filtro (GET)
    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    # Aplica os filtros apenas se as datas forem fornecidas
    if data_inicio:
        # Filtra ocorrências com data maior ou igual à data_inicio
        materiais = materiais.filter(ocorrencia__data_hora_fato__date__gte=data_inicio)

    if data_fim:
        # Filtra ocorrências com data menor ou igual à data_fim
        materiais = materiais.filter(ocorrencia__data_hora_fato__date__lte=data_fim)

    # Ordenar por data mais recente para facilitar a visualização
    materiais = materiais.order_by("-ocorrencia__data_hora_fato")

    context = {
        "materiais": materiais,
    }

    return render(request, "rpi/lista_materiais_apreendidos.html", context)


def deletar_materiais_apreendidos(request, apreensao_id):
    apreensao = get_object_or_404(Apreensao, id=apreensao_id)

    if request.method == "POST":
        apreensao.delete()
        messages.success(request, "Material apreendido excluído com sucesso.")

    return redirect("listar_materiais_apreendidos")


def gerar_pdf_relatorio_weasyprint(relatorio_diario, request):
    """
    Gera o PDF do relatório diário utilizando WeasyPrint
    """

    # ============================================================
    # FUNÇÕES AUXILIARES
    # ============================================================

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
        return f"{data.strftime('%d%H%M')}{meses[data.month]}{data.strftime('%y')}"

    # Crimes considerados CVLI (por enquanto, lista simples)
    CRIMES_CVLI = [
        "HOMICÍDIO DECORRENTE DE OPOSIÇÃO A INTERVENÇÃO POLICIAL",
        "HOMICÍDIO DOLOSO",
        "HOMICÍDIO DOLOSO NA DIREÇÃO DE VEÍCULO AUTOMOTOR",
        "INDUZIMENTO, INSTIGAÇÃO OU AUXÍLIO AO SUICÍDIO OU A AUTOMUTILAÇÃO",
        "FEMINICÍDIO",
        "ABORTO",
        "LESÃO CORPORAL SEGUIDA DE MORTE",
        "ROUBO A PEDESTRE COM MORTE",
        "ROUBO A RESIDÊNCIA COM MORTE",
        "ROUBO A COMÉRCIO COM MORTE",
        "ROUBO A MOTORISTA COM MORTE",
        "ROUBO DE ARMA COM MORTE",
        "ROUBO DE VEÍCULO COM MORTE",
        "ROUBO A ESTABELECIMENTO BANCÁRIO COM MORTE",
        "ROUBO COM MORTE",
    ]

    # ============================================================
    # CONSULTA DAS OCORRÊNCIAS
    # ============================================================

    ocorrencias_qs = (
        relatorio_diario.ocorrencias.select_related("natureza", "opm", "opm__municipio")
        .prefetch_related("envolvidos", "apreensoes", "imagens")
        .order_by("data_hora_fato")
    )

    ocorrencias_normais = []
    ocorrencias_cvli = []

    for ocorrencia in ocorrencias_qs:
        natureza_nome = ocorrencia.natureza.nome.upper()

        imagens = []
        for img in ocorrencia.imagens.all():
            if img.imagem and img.imagem.path:
                imagens.append(
                    {
                        "uri": Path(img.imagem.path).as_uri(),
                        "legenda": img.legenda,
                    }
                )

        item = {
            "ocorrencia": ocorrencia,
            "sigla_opm_limpa": (
                ocorrencia.opm.sigla.split(" - ")[0] if ocorrencia.opm else ""
            ),
            "imagens": imagens,
        }

        if natureza_nome in CRIMES_CVLI:
            ocorrencias_cvli.append(item)
        else:
            ocorrencias_normais.append(item)

    # ============================================================
    # NUMERAÇÃO DO RELATÓRIO
    # ============================================================

    numero_cvli = len(ocorrencias_normais) + 1

    # Letras a), b), c)...
    letras = "abcdefghijklmnopqrstuvwxyz"
    for idx, item in enumerate(ocorrencias_cvli):
        item["letra"] = letras[idx]

    # ============================================================
    # TABELA RESUMO CVLI
    # ============================================================

    tabela_cvli = []
    contador_opm = Counter()

    for item in ocorrencias_cvli:
        ocorrencia = item["ocorrencia"]
        opm = item["sigla_opm_limpa"]

        envolvidos_da_ocorrencia = ocorrencia.envolvidos.all()
        n_vitimas = len(
            [e for e in envolvidos_da_ocorrencia if e.tipo_participante == "V"]
        )

        # Caso não haja vítimas cadastradas, definimos 1 como padrão para não zerar a tabela
        if n_vitimas == 0:
            n_vitimas = 1

        municipio = ocorrencia.opm.municipio.nome if ocorrencia.opm else ""
        opm = item["sigla_opm_limpa"]

        contador_opm[opm] += n_vitimas

        tabela_cvli.append(
            {
                "municipio": municipio,
                "opm": opm,
                "vitimas": n_vitimas,  # por ora fixo
                "instrumento": (
                    ocorrencia.instrumento.nome
                    if ocorrencia.instrumento
                    else "NÃO INFORMADO"
                ),  # placeholder
            }
        )

    total_cvli = sum(contador_opm.values())
    # total_cvli = sum(linha["vitimas"] for linha in tabela_cvli)

    cvli_resumo_opm = ", ".join(f"{qtd} - {opm}" for opm, qtd in contador_opm.items())

    # ============================================================
    # LOGO E CSS
    # ============================================================

    logo_path = find("rpi/img/logo.png")
    logo_uri = (
        urllib.parse.urljoin("file:", urllib.request.pathname2url(logo_path))
        if logo_path
        else ""
    )

    css_path = find("rpi/css/rpi.css")
    css_uri = (
        urllib.parse.urljoin("file:", urllib.request.pathname2url(css_path))
        if css_path
        else ""
    )

    # ============================================================
    # CONTEXTO DO TEMPLATE
    # ============================================================

    context = {
        "relatorio": relatorio_diario,
        "ocorrencias": ocorrencias_normais,
        "ocorrencias_cvli": ocorrencias_cvli,
        "numero_cvli": numero_cvli,
        "tabela_cvli": tabela_cvli,
        "total_cvli": total_cvli,
        "cvli_resumo_opm": cvli_resumo_opm,
        "data_inicio_militar": formatar_data_militar(relatorio_diario.data_inicio),
        "data_fim_militar": formatar_data_militar(relatorio_diario.data_fim),
        "logo_uri": logo_uri,
        "css_uri": css_uri,
        "nr_relatorio": f"{numero_cvli:03d}/{relatorio_diario.ano_criacao}",
    }

    # ============================================================
    # RENDERIZAÇÃO DO PDF
    # ============================================================

    html_string = render_to_string("rpi/relatorio_pdf.html", context)

    pdf = HTML(string=html_string, base_url="file:///").write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=relatorio.pdf"

    return response


class RelatorioListView(LoginRequiredMixin, ListView):
    model = RelatorioDiario
    template_name = "rpi/relatorio_list.html"
    context_object_name = "relatorios"
    ordering = ["-data_inicio"]

    def get_queryset(self):
        """
        Sobrescreve o queryset padrão para aplicar filtros por data
        usando parâmetros GET.
        """
        queryset = RelatorioDiario.objects.filter(
            usuario_responsavel=self.request.user,
            finalizado=True,  # MOSTRA SOMENTE RELATÓRIOS FINALIZADOS
        )

        # Captura os parâmetros da URL (?data_inicio=...&data_fim=...)
        data_inicio = self.request.GET.get("data_inicio")
        data_fim = self.request.GET.get("data_fim")

        # Se o usuário informou data inicial
        if data_inicio:
            queryset = queryset.filter(data_inicio__date__gte=parse_date(data_inicio))

        # Se o usuário informou data final
        if data_fim:
            queryset = queryset.filter(data_inicio__date__lte=parse_date(data_fim))

        return queryset


class RelatorioDetailView(LoginRequiredMixin, DetailView):
    """
    View responsável por exibir o DETALHE de um relatório:
    - dados do relatório
    - ocorrências vinculadas a ele
    """

    model = RelatorioDiario
    template_name = "rpi/relatorio_detail.html"
    context_object_name = "relatorio"

    paginate_by = 1

    def get_queryset(self):
        """
        Garante que o usuário só veja relatórios dele.
        """
        return RelatorioDiario.objects.filter(usuario_responsavel=self.request.user)

    def get_context_data(self, **kwargs):
        """
        Adiciona as ocorrências do relatório ao contexto.
        """
        context = super().get_context_data(**kwargs)

        # Busca apenas ocorrências deste relatório
        context["ocorrencias"] = self.object.ocorrencias.all().order_by(
            "-data_hora_fato"
        )

        return context
    
    
class InstrumentoCreateView(LoginRequiredMixin, CreateView):
    model = Instrumento
    form_class = InstrumentoForm
    template_name = "rpi/instrumento_form.html"
    success_url = reverse_lazy("ocorrencia_create")

    def form_valid(self, form):
        messages.success(self.request, "Instrumento cadastrado com sucesso!")
        return super().form_valid(form)

class InstrumentoListView(LoginRequiredMixin, ListView):
    model = Instrumento
    template_name = "rpi/instrumento_list.html"
    context_object_name = "instrumentos"
    ordering = ["nome"]
    
class InstrumentoDeleteView(LoginRequiredMixin, DeleteView):
    model = Instrumento
    success_url = reverse_lazy("instrumento_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Instrumento excluído com sucesso.")
        return super().delete(request, *args, **kwargs)
    
class InstrumentoUpdateView(LoginRequiredMixin, UpdateView):
    model = Instrumento
    form_class = InstrumentoForm
    template_name = "rpi/instrumento_form.html"
    success_url = reverse_lazy("instrumento_list")

    def form_valid(self, form):
        messages.success(self.request, "Instrumento atualizado com sucesso!")
        return super().form_valid(form)
    
class InstrumentoDetailView(LoginRequiredMixin, DetailView):
    model = Instrumento
    template_name = "rpi/instrumento_detail.html"
    context_object_name = "instrumento"


def salvar_instrumento_ajax(request):
    if request.method == "POST":
        nome = request.POST.get('nome')
        if nome:
            novo_inst = Instrumento.objects.create(nome=nome)
            return JsonResponse({'id': novo_inst.id, 'nome': novo_inst.nome}, status=200)
    return JsonResponse({'erro': 'Dados inválidos'}, status=400)