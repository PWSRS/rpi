# 1. Bibliotecas padrão do Python (Standard Library)
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

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
from .models import Ocorrencia, Envolvido, RelatorioDiario, Apreensao, OcorrenciaImagem
from .forms import (
    OcorrenciaForm,
    EnvolvidoForm,
    EnvolvidoFormSet,
    ApreensaoForm,
    ApreensaoFormSet,
    ImagemFormSet,
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

        # 2. REDIRECIONA PARA O DOWNLOAD (Chama a URL de download)
        # Assumindo que sua URL de download seja: path('relatorio/<int:pk>/download/', ...)
        return redirect("download_pdf_relatorio", pk=relatorio.pk) 

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
    """
    Permite que um usuário reabra um relatório finalizado (finalizado=False)
    para corrigir ou adicionar ocorrências.
    """
    relatorio = get_object_or_404(
        RelatorioDiario, pk=pk, usuario_responsavel=request.user
    )

    if request.method == "POST":
        relatorio.finalizado = False
        relatorio.data_fim = None 
        relatorio.save()

        messages.warning(
            request,
            f"Relatório {relatorio.nr_relatorio} foi REABERTO para edição. Lembre-se de FINALIZAR novamente!",
        )
        return redirect("ocorrencia_list") # Redirecionamento simples após a ação POST

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

        # Busque o ÚLTIMO relatório do usuário, independentemente do status.
        context["relatorio_atual"] = (
            RelatorioDiario.objects.filter(usuario_responsavel=self.request.user)
            .order_by("-data_inicio")
            .first()
        )

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

        # Definição das fábricas de Formset (Mantidas na View, conforme seu código)
        EnvolvidoFormSet = inlineformset_factory(
            self.model, Envolvido, form=EnvolvidoForm, extra=1, can_delete=True # Alterei extra=0 para 1 para facilitar
        )
        ApreensaoFormSet = inlineformset_factory(
            self.model, Apreensao, form=ApreensaoForm, extra=1, can_delete=True # Alterei extra=0 para 1
        )
        
        # NOVO: Fábrica do Formset de Imagens (Definida na View, conforme seu código)
        OcorrenciaImagemFormSet = inlineformset_factory(
            self.model, 
            OcorrenciaImagem, 
            fields=('imagem', 'legenda'),
            extra=1,
            can_delete=True
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
        imagem_formset = context["imagem_formset"] # NOVO: Adiciona o formset de imagem

        # Log de depuração (opcional, pode remover depois)
        print(f"Envolvidos válidos: {envolvido_formset.is_valid()}")
        print(f"Apreensões válidas: {apreensao_formset.is_valid()}")
        print(f"Imagens válidas: {imagem_formset.is_valid()}") # NOVO: Log

        if (
            envolvido_formset.is_valid() 
            and apreensao_formset.is_valid()
            and imagem_formset.is_valid() # CRÍTICO: Validação do formset de imagem
        ):
            with transaction.atomic():
                self.object = form.save(commit=False)
                self.object.relatorio_diario = self.relatorio_atual
                self.object.save()

                envolvido_formset.instance = self.object
                envolvido_formset.save()

                apreensao_formset.instance = self.object
                apreensao_formset.save()
                
                imagem_formset.instance = self.object # NOVO: Liga as imagens à ocorrência
                imagem_formset.save() # NOVO: Salva as imagens

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
                    imagem_formset=imagem_formset, # CRÍTICO: Passar o formset de imagem
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
            self.model, OcorrenciaImagem, fields=('imagem', 'legenda'), extra=1, can_delete=True
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
                self.request.POST, self.request.FILES, instance=self.object, prefix="imagens"
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
        imagem_formset = context["imagem_formset"] # NOVO: Pega o formset

        if (
            form.is_valid()
            and envolvido_formset.is_valid()
            and apreensao_formset.is_valid()
            and imagem_formset.is_valid() # CRÍTICO: Validação do formset de imagem
        ):
            # Salva a ocorrência
            self.object = form.save()
            # Salva os formsets
            envolvido_formset.save()
            apreensao_formset.save()
            imagem_formset.save() # NOVO: Salva as imagens (atualizações, exclusões e adições)

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
    # Buscamos todos os registros da tabela Apreensao
    # select_related evita múltiplas idas ao banco para buscar o nome do material e a ocorrência
    materiais = Apreensao.objects.select_related('material_tipo', 'ocorrencia').all()
    return render(request, 'rpi/lista_materiais_apreendidos.html', {'materiais': materiais})

def deletar_materiais_apreendidos(request, apreensao_id):
    apreensao = get_object_or_404(Apreensao, id=apreensao_id)
    
    if request.method == 'POST':
        apreensao.delete()
        messages.success(request, "Material apreendido excluído com sucesso.")
    
    return redirect('listar_materiais_apreendidos')

def gerar_pdf_relatorio_weasyprint(relatorio_diario, request): 
    """
    Gera o PDF do relatório diário (WeasyPrint), utilizando o request para 
    resolver a base URL HTTP para o carregamento das imagens de Mídia.
    """

    # --- FUNÇÃO AUXILIAR PARA FORMATO MILITAR ---
    def formatar_data_militar(data):
        if not data: return ""
        meses = {1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN", 7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"}
        dia = data.strftime("%d")
        hora_minuto = data.strftime("%H%M") 
        mes = meses[data.month]
        ano = data.strftime("%y")
        return f"{dia}{hora_minuto}{mes}{ano}"


    # --- FUNÇÕES AUXILIARES PARA GERAR LISTAS HTML (Mantidas) ---

    def _gerar_lista_envolvidos_html(ocorrencia):
        # ... (código mantido) ...
        envolvidos_qs = ocorrencia.envolvidos.all() 
        if not envolvidos_qs.exists():
            return ""

        html_parts = []
        html_parts.append('<div class="detalhes-tecnicos" style="margin-top: 10px; margin-left: 20px; font-size: 0.9em;">')
        html_parts.append('<strong>Envolvido(s):</strong>')
        html_parts.append('<ul style="list-style: none; padding: 0;">')
        
        for env in envolvidos_qs:
            tipo = env.get_tipo_participante_display()
            nome = getattr(env, "nome", "NÃO INFORMADO")
            idade = getattr(env, "idade", "??")
            antecedentes = "SIM" if env.antecedentes == "S" else "NÃO"
            
            html_parts.append(
                f'<li>- <b>{nome}</b>, {idade} anos ({tipo}). Antecedentes: {antecedentes}.</li>'
            )
            
        html_parts.append('</ul>')
        html_parts.append('</div>')

        return "\n".join(html_parts)

    def _gerar_lista_apreensoes_html(ocorrencia):
        # ... (código mantido) ...
        apreensoes_qs = ocorrencia.apreensoes.all()
        if not apreensoes_qs.exists():
            return ""

        html_parts = []
        html_parts.append('<div class="detalhes-tecnicos" style="margin-top: 5px; margin-left: 20px; font-size: 0.9em;">')
        html_parts.append('<strong>Material Apreendido:</strong>')
        html_parts.append('<ul style="list-style: none; padding: 0;">')

        for apreensao in apreensoes_qs:
            material = getattr(apreensao.material_tipo, "nome", "Material Não Identificado")
            quantidade = str(apreensao.quantidade).replace('.', ',') 
            unidade = apreensao.unidade_medida 
            
            html_parts.append(
                f'<li>- {quantidade} {unidade} de {material}.</li>'
            )
            
        html_parts.append('</ul>')
        html_parts.append('</div>')

        return "\n".join(html_parts)


    # 1. CONSULTA GERAL OTIMIZADA E ORDENADA
    ocorrencias_qs = (
        relatorio_diario.ocorrencias.select_related("natureza", "opm", "opm__municipio")
        .prefetch_related("envolvidos", "apreensoes__material_tipo", "imagens") 
        .order_by("data_hora_fato")
    )

    cvli_qs = [] 

    # 3. PRÉ-PROCESSAMENTO DE DADOS
    ocorrencias_com_dados = []
    for ocorrencia in ocorrencias_qs:
        sigla_opm_limpa = "OPM Não Definida"
        if ocorrencia.opm:
            try:
                sigla_opm_limpa = ocorrencia.opm.sigla.split(" - ")[0]
            except:
                sigla_opm_limpa = ocorrencia.opm.sigla

        envolvidos_html = _gerar_lista_envolvidos_html(ocorrencia)
        apreensoes_html = _gerar_lista_apreensoes_html(ocorrencia)

        ocorrencias_com_dados.append(
            {
                "ocorrencia": ocorrencia,
                "sigla_opm_limpa": sigla_opm_limpa,
                "envolvidos_html": envolvidos_html,
                "apreensoes_html": apreensoes_html,
            }
        )

    # 4. MONTAGEM DO CONTEXTO PARA O TEMPLATE
    
    # Acessando logo e CSS via File URI (Static)
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
        
    data_inicio_militar = formatar_data_militar(relatorio_diario.data_inicio)
    data_fim_militar = formatar_data_militar(relatorio_diario.data_fim)

    context = {
        "relatorio": relatorio_diario,
        "ocorrencias": ocorrencias_com_dados,
        "cvli_qs": cvli_qs,
        "data_inicio_militar": data_inicio_militar,
        "data_fim_militar": data_fim_militar,
        "logo_uri": logo_uri,
        "css_uri": css_uri,
    }

    # 5. RENDERIZAÇÃO E GERAÇÃO DO PDF
    html_string = render_to_string("rpi/relatorio_pdf.html", context)
    
    # CRÍTICO: Definir o base_url como a URL HTTP/HTTPS absoluta do seu site.
    base_url_http = request.build_absolute_uri('/') 

    pdf_file = HTML(string=html_string, base_url=base_url_http).write_pdf()

    # 6. CONFIGURAÇÃO DA RESPOSTA HTTP
    response = HttpResponse(pdf_file, content_type="application/pdf")
    filename = f"Relatorio_Diario_{data_inicio_militar}_{data_fim_militar}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    
    return response