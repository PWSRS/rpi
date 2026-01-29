# 1. Bibliotecas padrão do Python (Standard Library)
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, time, timedelta
from pathlib import Path


# 2. Bibliotecas de terceiros (Third-party)
from weasyprint import CSS, HTML

# 3. Django Core e Utilitários
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.contrib.staticfiles.finders import find
from django.core.mail import send_mail

# 4. Django Banco de Dados e Modelos
from django.db import IntegrityError, transaction
from django.db.models import F, Prefetch, Q, Sum, Count, ProtectedError

# 5. Django HTTP e View Helpers
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from .utils import calcular_janela_plantao
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

# 6. Django Generic Views e Formulários
from django.forms import inlineformset_factory, modelformset_factory
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

# 7. Importações do seu App Local (Internal)
from .forms import (
    ApreensaoForm,
    ApreensaoFormSet,
    CadastroUsuarioForm,
    EnvolvidoForm,
    EnvolvidoFormSet,
    ImagemFormSet,
    InstrumentoForm,
    MaterialApreendidoTipoForm,
    NaturezaOcorrenciaForm,
    OcorrenciaForm,
)
from .models import (
    Apreensao,
    Envolvido,
    Instrumento,
    MaterialApreendidoTipo,
    NaturezaOcorrencia,
    Ocorrencia,
    OcorrenciaImagem,
    RelatorioDiario,
    Municipio,
    OPM,
)
# O @user_passes_test verifica se o usuário é staff (admin)
# Apenas usuários staff podem ativar o cadastro de novos usuários
# lambda é uma função anônima que retorna True se o usuário for staff
# u: representa o usuário atual e u.is_staff verifica se ele é staff
@user_passes_test(lambda u: u.is_staff)
def ativar_policial(request, user_id):
    # Busca o usuário ou retorna 404 se não existir
    policial = get_object_or_404(User, id=user_id)
    
    # Se não estiver ativo, ativa e salva
    if not policial.is_active:
        policial.is_active = True
        policial.save()
        
        # Opcional: Avisar o policial por e-mail
        assunto = "Acesso Liberado - Sistema RPI"
        mensagem = f"Olá {policial.first_name},\n\nSua solicitação de acesso ao Sistema RPI da ARI Sul foi aprovada. Você já pode realizar o login com seu e-mail institucional e senha cadastrada."
        
        send_mail(assunto, mensagem, 'pablo.weber@hotmail.com', [policial.email], fail_silently=True)
        
        messages.success(request, f"O policial {policial.first_name} foi ativado com sucesso!")
    else:
        messages.info(request, "Este policial já está ativo.")
        
    return redirect('painel_gestao')

@user_passes_test(lambda u: u.is_staff)
def deletar_usuario(request, user_id):
    policial = get_object_or_404(User, id=user_id)
    
    if request.method == "POST":
        policial_nome = policial.first_name  # Salva antes de deletar!
        policial.delete()
        return JsonResponse({'success': True, 'message': f"O policial {policial_nome} foi deletado com sucesso!"})
    
    return JsonResponse({'success': False, 'error': 'Requisição inválida.'}, status=400)

@user_passes_test(lambda u: u.is_staff)
def listar_usuarios(request):
    usuarios = User.objects.filter(is_active=True).order_by('-date_joined')
    return render(request, 'rpi/lista_usuarios.html', {'usuarios': usuarios})


#User = get_user_model() # Obtém o modelo de usuário customizado ou o padrão do Django
User = get_user_model()
@user_passes_test(lambda u: u.is_staff)
def painel_gestao(request):
    # User.objects.filter(is_active=False).order_by('-date_joined') busca todos os usuários inativos (pendentes)
    # -date_joined é usado para ordenar do mais recente ao mais antigo
    pendentes = User.objects.filter(is_active=False).order_by('-date_joined')
    return render(request, 'rpi/dashboard_admin.html', {'pendentes': pendentes})

@login_required
def dashboard_admin(request):
    # Se não for staff, redireciona para a lista de ocorrências
    if not request.user.is_staff:
        return redirect('ocorrencia_list')
    
    # Busca apenas os policiais que se cadastraram mas ainda não foram aprovados
    pendentes = User.objects.filter(is_active=False).order_by('-date_joined')
    
    return render(request, 'rpi/dashboard_admin.html', {'pendentes': pendentes})

def registro_usuario(request):
    if request.method == "POST":
        form = CadastroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False) # Não salva no banco ainda
            
            # REGRA DE SEGURANÇA CRÍTICA:
            user.is_active = False # O usuário nasce desativado
            
            user.save()

            messages.warning(
                request,
                "Solicitação enviada! Sua conta está em análise pela administração. "
                "Você receberá um aviso assim que seu acesso for liberado."
            )
            return redirect("login")
    else:
        form = CadastroUsuarioForm()

    return render(request, "rpi/registro.html", {"form": form})

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            # Tenta encontrar o usuário pelo e-mail
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            return None
        
        # Verifica a senha
        if user.check_password(password):
            return user
        return None

# --- GERENCIAMENTO DO RELATÓRIO ---

@login_required
def finalizar_relatorio(request, pk):
    relatorio = get_object_or_404(RelatorioDiario, pk=pk)

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

@login_required
def download_pdf_relatorio(request, pk):
    """
    View que aciona a função de geração do PDF.
    Recebe 'request' e 'pk' da URL.
    """
    relatorio = get_object_or_404(RelatorioDiario, pk=pk)

    # CORREÇÃO: Passa 'relatorio' e 'request' para a função de geração de PDF
    response = gerar_pdf_relatorio_weasyprint(relatorio, request)

    # O Content-Disposition 'inline' na função de PDF deve fazer o navegador abrir a nova guia.
    return response


# NOVO: Reverte o status de finalização do relatório para permitir a edição
@login_required
def reabrir_relatorio(request, pk):
    relatorio = get_object_or_404(RelatorioDiario, pk=pk)

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
    relatorio = get_object_or_404(RelatorioDiario, pk=pk)

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

        # 2. LÓGICA DO DIA DO ANO (Ordinal)
        # tm_yday retorna 1 para 1º de Jan, 16 para 16 de Jan, etc.
        
        # o número do relatório seja baseado no início do plantão(mesmo que aberto após a meia-noite)
        # o dia_do_ano = inicio_plantao.date().timetuple().tm_yday
        dia_do_ano = agora.date().timetuple().tm_yday
        ano_atual = agora.year

        # 3. VERIFICAÇÃO DE SEGURANÇA (Opcional)
        # Verifica se já existe um relatório com esse número para evitar duplicidade no mesmo dia
        existe_hoje = RelatorioDiario.objects.filter(
            nr_relatorio=dia_do_ano, 
            ano_criacao=ano_atual
        ).exists()

        if existe_hoje:
            messages.error(request, f"Já existe um relatório (Nº {dia_do_ano}) iniciado para a data de hoje.")
            return redirect("alguma_view_de_lista") # Redirecione para onde preferir

        # 4. CRIAÇÃO DO RELATÓRIO
        relatorio_aberto = RelatorioDiario.objects.create(
            nr_relatorio=dia_do_ano, # Agora é o dia do ano, não mais incremento +1
            ano_criacao=ano_atual,
            data_inicio=inicio_plantao,
            data_fim=fim_plantao,
            usuario_responsavel=request.user,
            finalizado=False,
        )

        messages.success(
            request, f"Relatório {dia_do_ano}/{ano_atual} iniciado com sucesso!"
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
        relatorio_aberto = RelatorioDiario.objects.filter(finalizado=False).last()

        # 2. Se houver um aberto, mostra apenas as ocorrências dele
        if relatorio_aberto:
            return relatorio_aberto.ocorrencias.all().order_by("-data_hora_fato")

        # 3. Se NÃO houver nenhum aberto (plantão finalizado e nenhum novo iniciado),
        # você pode optar por mostrar as do ÚLTIMO finalizado para não ver a tela vazia,
        # OU retornar vazio para forçar o início de um novo dia.
        ultimo_finalizado = (
            RelatorioDiario.objects.filter(finalizado=True).order_by("-data_inicio").first()
        )

        if ultimo_finalizado:
            return ultimo_finalizado.ocorrencias.all().order_by("-data_hora_fato")

        return Ocorrencia.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Busca o mesmo relatório para o template decidir se mostra os botões de Editar/Excluir
        relatorio = (
            RelatorioDiario.objects.filter(
               finalizado=False
            ).last()
            or RelatorioDiario.objects.filter(
               finalizado=True
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
            finalizado=False
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
            
def ajax_carregar_municipios(request):
    opm_id = request.GET.get('opm_id')
    
    if not opm_id:
        return JsonResponse([], safe=False)

    try:
        # 1. Buscamos a OPM específica
        opm = OPM.objects.get(id=opm_id)
        
        # 2. Pegamos todos os municípios associados a essa OPM
        # Como é ManyToMany, usamos .all() no campo municipios
        municipios = opm.municipios.all().order_by('nome')
        
        # 3. Formatamos para JSON
        data = [
            {'id': m.id, 'nome': m.nome} 
            for m in municipios
        ]
        return JsonResponse(data, safe=False)
        
    except OPM.DoesNotExist:
        return JsonResponse({'error': 'OPM não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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

    def dispatch(self, request, *args, **kwargs):
        """ Impede a edição se o relatório estiver finalizado """
        obj = self.get_object()
        if obj.relatorio_diario.finalizado:
            messages.error(request, "Este relatório já está finalizado e não pode ser editado.")
            return redirect('ocorrencia_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        # Definição das fábricas de Formset
        EnvolvidoFormSet = inlineformset_factory(
            self.model, Envolvido, form=EnvolvidoForm, extra=1, can_delete=True
        )
        ApreensaoFormSet = inlineformset_factory(
            self.model, Apreensao, form=ApreensaoForm, extra=1, can_delete=True
        )
        OcorrenciaImagemFormSet = inlineformset_factory(
            self.model,
            OcorrenciaImagem,
            fields=("imagem", "legenda"),
            extra=1,
            can_delete=True,
        )

        if self.request.POST:
            data["envolvido_formset"] = EnvolvidoFormSet(
                self.request.POST, instance=self.object, prefix="envolvidos"
            )
            data["apreensao_formset"] = ApreensaoFormSet(
                self.request.POST, instance=self.object, prefix="apreensoes"
            )
            data["imagem_formset"] = OcorrenciaImagemFormSet(
                self.request.POST,
                self.request.FILES,
                instance=self.object,
                prefix="imagens",
            )
        else:
            data["envolvido_formset"] = EnvolvidoFormSet(
                instance=self.object, prefix="envolvidos"
            )
            data["apreensao_formset"] = ApreensaoFormSet(
                instance=self.object, prefix="apreensoes"
            )
            data["imagem_formset"] = OcorrenciaImagemFormSet(
                instance=self.object, prefix="imagens"
            )
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        envolvido_formset = context["envolvido_formset"]
        apreensao_formset = context["apreensao_formset"]
        imagem_formset = context["imagem_formset"]

        if (
            form.is_valid()
            and envolvido_formset.is_valid()
            and apreensao_formset.is_valid()
            and imagem_formset.is_valid()
        ):
            self.object = form.save()
            envolvido_formset.save()
            apreensao_formset.save()
            imagem_formset.save()

            messages.success(self.request, "Ocorrência atualizada com sucesso!")
            return redirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))


class OcorrenciaDeleteView(LoginRequiredMixin, DeleteView):
    """Permite excluir uma ocorrência."""
    model = Ocorrencia
    success_url = reverse_lazy("ocorrencia_list")

    def dispatch(self, request, *args, **kwargs):
        """ Impede a exclusão se o relatório estiver finalizado """
        obj = self.get_object()
        if obj.relatorio_diario.finalizado:
            messages.error(request, "Não é possível excluir ocorrências de um relatório finalizado.")
            return redirect('ocorrencia_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(
            self.request, f"Ocorrência {self.object.pk} excluída com sucesso."
        )
        return super().form_valid(form)

def listar_materiais_apreendidos(request):
    # 1. Chama a função utilitária para resolver as datas
    plantao = calcular_janela_plantao(
        request.GET.get("data_inicio"), 
        request.GET.get("data_fim")
    )

    # 2. Aplica os filtros usando o dicionário retornado (plantao)
    materiais = Apreensao.objects.select_related("material_tipo", "ocorrencia").filter(
        ocorrencia__data_hora_fato__range=(plantao["dt_inicio"], plantao["dt_fim"])
    )

    # 3. Resumo de totais
    resumo_totais = (
        materiais.values("material_tipo__nome", "unidade_medida")
        .annotate(total_quantidade=Sum("quantidade"))
        .order_by("material_tipo__nome")
    )

    # 4. Contexto organizado
    context = {
        "materiais": materiais.order_by("-ocorrencia__data_hora_fato"),
        "resumo_totais": resumo_totais,
        "data_inicio_full": plantao["dt_inicio"],  # Usado na legenda HTML
        "data_fim_full": plantao["dt_fim"],        # Usado na legenda HTML
        "data_inicio": plantao["data_inicio_str"], # Usado no valor do input date
        "data_fim": plantao["data_fim_str"],       # Usado no valor do input date
    }

    return render(request, "rpi/lista_materiais_apreendidos.html", context)

def deletar_materiais_apreendidos(request, apreensao_id):
    apreensao = get_object_or_404(Apreensao, id=apreensao_id)

    if request.method == "POST":
        apreensao.delete()
        messages.success(request, "Material apreendido excluído com sucesso.")

    return redirect("listar_materiais_apreendidos")

def listar_prisoes(request):
    # 1. Resolve a lógica de datas em uma linha
    plantao = calcular_janela_plantao(request.GET.get("data_inicio"), request.GET.get("data_fim"))

    # 2. Filtra envolvidos pela janela do plantão
    envolvidos = Envolvido.objects.filter(
        tipo_participante__in=["P", "S", "M", "A"],
        ocorrencia__data_hora_fato__range=(plantao["dt_inicio"], plantao["dt_fim"])
    ).select_related("ocorrencia")

    # 3. Resumo totalizado
    resumo_totais = (
        envolvidos.values("tipo_participante")
        .annotate(total=Count("id"))
        .order_by("tipo_participante")
    )

    context = {
        "envolvidos": envolvidos.order_by("-ocorrencia__data_hora_fato"),
        "resumo_totais": resumo_totais,
        "data_inicio_full": plantao["dt_inicio"],
        "data_fim_full": plantao["dt_fim"],
        "data_inicio": plantao["data_inicio_str"],
        "data_fim": plantao["data_fim_str"],
    }
    return render(request, "rpi/lista_prisoes.html", context)


def listar_prisoes_por_opm(request):
    # 1. Resolve a lógica de datas
    plantao = calcular_janela_plantao(request.GET.get("data_inicio"), request.GET.get("data_fim"))

    # 2. Query principal usando o range do plantão
    envolvidos = Envolvido.objects.filter(
        tipo_participante__in=["P", "S", "M", "A"],
        ocorrencia__data_hora_fato__range=(plantao["dt_inicio"], plantao["dt_fim"])
    ).select_related("ocorrencia", "ocorrencia__opm")

    # 3. Lógica de Totais por OPM
    totais_query = envolvidos.values("ocorrencia__opm__nome", "tipo_participante").annotate(total=Count("id"))
    
    totais_opm = defaultdict(lambda: {"P": 0, "S": 0, "A": 0, "M": 0, "total": 0})
    for row in totais_query:
        opm_nome = row["ocorrencia__opm__nome"] or "OPM não informada"
        tipo = row["tipo_participante"]
        totais_opm[opm_nome][tipo] = row["total"]
        totais_opm[opm_nome]["total"] += row["total"]

    # 4. Agrupamento para o Template
    envolvidos_por_opm = defaultdict(lambda: {"lista": [], "resumo": {}})
    for envolvido in envolvidos.order_by("ocorrencia__opm__nome", "-ocorrencia__data_hora_fato"):
        opm_nome = getattr(envolvido.ocorrencia.opm, "nome", "OPM não informada")
        envolvidos_por_opm[opm_nome]["lista"].append(envolvido)
        envolvidos_por_opm[opm_nome]["resumo"] = totais_opm[opm_nome]

    context = {
        "envolvidos_por_opm": dict(envolvidos_por_opm),
        "data_inicio_full": plantao["dt_inicio"],
        "data_fim_full": plantao["dt_fim"],
        "data_inicio": plantao["data_inicio_str"],
        "data_fim": plantao["data_fim_str"],
    }
    return render(request, "rpi/lista_prisoes_por_opm.html", context)

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
        relatorio_diario.ocorrencias.select_related("natureza", "opm") # municipio saiu daqui
        .prefetch_related("envolvidos", "apreensoes", "imagens", "opm__municipios") # municipios (plural) entrou aqui
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

        #municipio = ocorrencia.opm.municipio.nome if ocorrencia.opm else ""
        municipio = ocorrencia.municipio.nome if ocorrencia.municipio else ""
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
    paginate_by = 10

    def get_queryset(self):
        """
        Sobrescreve o queryset padrão para aplicar filtros por data
        usando parâmetros GET.
        """
        queryset = RelatorioDiario.objects.filter(
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
        return RelatorioDiario.objects.all()

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


class MaterialApreendidoTipoCreateView(LoginRequiredMixin, CreateView):
    model = MaterialApreendidoTipo
    form_class = MaterialApreendidoTipoForm
    template_name = "rpi/material_tipo_form.html"
    success_url = reverse_lazy("list_material_apreendido_tipo")

    def form_valid(self, form):
        messages.success(self.request, "Tipo de material cadastrado com sucesso!")
        return super().form_valid(form)
    
class MaterialApreendidoTipoListView(LoginRequiredMixin, ListView):
    model = MaterialApreendidoTipo
    template_name = "rpi/material_tipo_list.html"
    context_object_name = "materiais_tipos"
    ordering = ["nome"]
    paginate_by = 5
    
class MaterialApreendidoTipoDeleteView(LoginRequiredMixin, DeleteView):
    model = MaterialApreendidoTipo
    success_url = reverse_lazy("list_material_apreendido_tipo")

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            success_url = self.get_success_url()
            self.object.delete()
            messages.success(request, "Tipo de material excluído com sucesso.")
            return redirect(success_url)
        except ProtectedError:
            material = self.get_object()
            messages.error(
                request, 
                f"Não é possível excluir '{material.nome}'. Existem apreensões vinculadas."
            )
        return redirect(self.success_url)
    
class MaterialApreendidoTipoDetailView(LoginRequiredMixin, DetailView):
    model = MaterialApreendidoTipo
    template_name = "rpi/material_tipo_detail.html"
    context_object_name = "material_tipo"

class MaterialApreendidoTipoUpdateView(LoginRequiredMixin, UpdateView):
    model = MaterialApreendidoTipo
    form_class = MaterialApreendidoTipoForm
    template_name = "rpi/material_tipo_form.html"
    success_url = reverse_lazy("list_material_apreendido_tipo")

    def form_valid(self, form):
        messages.success(self.request, "Tipo de material atualizado com sucesso!")
        return super().form_valid(form)


@login_required
@require_POST
def salvar_material_apreendido_ajax(request):
    nome = request.POST.get("nome", "").strip()

    if not nome:
        return JsonResponse(
            {"error": "Nome não informado"},
            status=400
        )

    obj, created = MaterialApreendidoTipo.objects.get_or_create(
        nome__iexact=nome,
        defaults={"nome": nome}
    )

    return JsonResponse(
        {
            "id": obj.id,
            "nome": obj.nome,
            "created": created
        },
        status=200
    )
    
    
    
@require_GET
def buscar_naturezas_ajax(request):
    # 1. Obter o termo de busca (query)
    query = request.GET.get('q', '').strip()
    
    # 2. Configura a filtragem
    if query:
        # Usa o Q object para realizar uma busca OR (nome OU tags_busca)
        # icontains: busca o termo em qualquer parte da string, sem distinção de caixa
        filtros = Q(nome__icontains=query) | Q(tags_busca__icontains=query)
        naturezas = NaturezaOcorrencia.objects.filter(filtros).order_by('nome')[:30] # Limita a 30 resultados
    else:
        # Se não houver termo, mostra as 15 naturezas mais comuns (ou as primeiras)
        # Otimização: Ajuste este filtro para mostrar crimes frequentes
        naturezas = NaturezaOcorrencia.objects.all().order_by('nome')[:15]

    # 3. Formatar os resultados para o Select2
    results = []
    for nat in naturezas:
        results.append({
            'id': nat.pk, # Select2 usa 'id' para o valor
            'text': nat.nome, # Select2 usa 'text' para o que é exibido
        })

    # 4. Retorna a resposta JSON
    return JsonResponse({'results': results, 'pagination': {'more': False}})




@csrf_exempt # OBS: Mantenha este decorador apenas se o token CSRF estiver falhando no JS. 
             # A melhor prática é usá-lo no template com {% csrf_token %}.
@require_POST
def cadastrar_natureza_rapida(request):
    """
    Processa a requisição AJAX para salvar rapidamente uma nova NaturezaOcorrencia.
    Retorna 200 (Sucesso), 400 (Erro de Validação) ou 500 (Erro de Servidor/Banco).
    """
    
    form = NaturezaOcorrenciaForm(request.POST)
    
    if form.is_valid():
        try:
            # 1. Tenta salvar no banco de dados
            nova_natureza = form.save()
            
            # 2. Retorno de sucesso (Status 200 OK)
            return JsonResponse({
                'success': True,
                'id': nova_natureza.pk,
                'text': str(nova_natureza), 
            }, status=200)
        
        except Exception as e:
            # 3. Captura erros do banco (ex: Integridade/UNIQUE constraint)
            # Imprime o erro no console do servidor para debug
            print(f"Erro no banco ao salvar Natureza: {e}")
            
            # Retorno de erro interno (Status 500)
            return JsonResponse({
                'success': False,
                'errors': {'__all__': [f"Erro interno de servidor: Falha ao salvar a Natureza. ({e})"]}
            }, status=500)
            
    else:
        # 4. Erro de validação do formulário (campos obrigatórios ausentes/inválidos)
        # Retorno de erro de cliente (Status 400 Bad Request)
        return JsonResponse({
            'success': False,
            'errors': form.errors, 
        }, status=400)
    
    # OBS: O código NÃO PRECISA de um return final aqui, pois @require_POST 
    # já lida com métodos HTTP incorretos, e o if/else garante um retorno para POST.
    
@user_passes_test(lambda u: u.is_superuser)
def lista_auditoria_objeto(request, pk):
    objeto = get_object_or_404(Ocorrencia, pk=pk)
    # Filtra o histórico apenas deste objeto usando o ID original
    historico = objeto.history.select_related('history_user').filter(id=pk).order_by('-history_date')
    
    for registro in historico:
        lista_final_mudancas = []
        
        if registro.history_type == '~':
            try:
                anterior = registro.prev_record
                if anterior:
                    delta = registro.diff_against(anterior)
                    for change in delta.changes:
                        # Normalização do campo
                        field_name = change.field
                        clean_field_name = field_name[:-3] if field_name.endswith('_id') else field_name
                        
                        try:
                            field_obj = Ocorrencia._meta.get_field(clean_field_name)
                            nome_campo = field_obj.verbose_name.capitalize()
                        except:
                            nome_campo = field_name.capitalize()
                            field_obj = None

                        v_antigo = change.old
                        v_novo = change.new

                        # Lógica de tradução de IDs para Nomes
                        if field_obj and hasattr(field_obj, 'choices') and field_obj.choices:
                            choices_dict = dict(field_obj.choices)
                            v_antigo = choices_dict.get(v_antigo, v_antigo)
                            v_novo = choices_dict.get(v_novo, v_novo)
                        
                        elif field_obj and field_obj.is_relation:
                            modelo_relacionado = field_obj.related_model
                            if v_antigo:
                                obj_ant = modelo_relacionado.objects.filter(pk=v_antigo).first()
                                v_antigo = str(obj_ant) if obj_ant else f"ID {v_antigo}"
                            if v_novo:
                                obj_nov = modelo_relacionado.objects.filter(pk=v_novo).first()
                                v_novo = str(obj_nov) if obj_nov else f"ID {v_novo}"

                        lista_final_mudancas.append({
                            'campo': nome_campo,
                            'antigo': v_antigo,
                            'novo': v_novo
                        })
            except Exception:
                pass
        
        registro.mudancas_processadas = lista_final_mudancas
                
    return render(request, 'auditoria/detalhe_historico.html', {
        'objeto': objeto,
        'historico': historico
    })
from django.apps import apps # Import necessário no topo do arquivo

@user_passes_test(lambda u: u.is_superuser)
def auditoria_geral(request):
    historico = Ocorrencia.history.select_related('history_user').all()[:100]
    
    for registro in historico:
        lista_final_mudancas = []
        
        # Só processamos mudanças se for uma EDIÇÃO (~)
        if registro.history_type == '~': 
            try:
                anterior = registro.prev_record
                if anterior:
                    delta = registro.diff_against(anterior)
                    for change in delta.changes:
                        # Normaliza o nome do campo (remove _id se houver)
                        field_name = change.field
                        clean_field_name = field_name[:-3] if field_name.endswith('_id') else field_name
                        
                        try:
                            field_obj = Ocorrencia._meta.get_field(clean_field_name)
                            nome_campo = field_obj.verbose_name.capitalize()
                        except:
                            nome_campo = field_name.replace('_', ' ').capitalize()
                            field_obj = None

                        v_antigo = change.old
                        v_novo = change.new

                        # TRATA CHOICES (ex: Consumado/Tentado)
                        if field_obj and hasattr(field_obj, 'choices') and field_obj.choices:
                            choices_dict = dict(field_obj.choices)
                            v_antigo = choices_dict.get(v_antigo, v_antigo)
                            v_novo = choices_dict.get(v_novo, v_novo)
                        
                        # TRATA RELAÇÕES (Select2, ForeignKeys)
                        elif field_obj and field_obj.is_relation:
                            modelo_relacionado = field_obj.related_model
                            try:
                                if v_antigo:
                                    obj_ant = modelo_relacionado.objects.filter(pk=v_antigo).first()
                                    v_antigo = str(obj_ant) if obj_ant else f"ID {v_antigo} (Removido)"
                                if v_novo:
                                    obj_nov = modelo_relacionado.objects.filter(pk=v_novo).first()
                                    v_novo = str(obj_nov) if obj_nov else f"ID {v_novo} (Removido)"
                            except:
                                pass

                        lista_final_mudancas.append({
                            'campo': nome_campo,
                            'antigo': v_antigo,
                            'novo': v_novo
                        })
            except Exception:
                pass
        
        registro.mudancas_processadas = lista_final_mudancas

    return render(request, 'auditoria/lista_geral.html', {'historico': historico})

