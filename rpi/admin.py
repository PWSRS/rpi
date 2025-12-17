from django.contrib import admin
from .models import (
    NaturezaOcorrencia,
    Municipio,
    OPM,
    RelatorioDiario,
    Ocorrencia,
    Envolvido,
)

# ----------------- 1. CONFIGURAÇÃO DE INLINES -----------------


# Define como o modelo 'Envolvido' deve aparecer na página da 'Ocorrencia'
class EnvolvidoInline(admin.TabularInline):
    model = Envolvido
    extra = 1  # Deixa 1 linha extra em branco para novo cadastro
    fields = ("nome", "tipo_participante", "idade")
    # Pode adicionar readonly_fields se quiser exibir campos que não podem ser alterados


@admin.register(NaturezaOcorrencia)
class NaturezaOcorrenciaAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo_impacto", "get_tipo_impacto_display")
    list_filter = ("tipo_impacto",)
    search_fields = ("nome",)


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)


@admin.register(OPM)
class OPMAdmin(admin.ModelAdmin):
    list_display = ("sigla", "nome", "municipio")
    list_filter = ("municipio",)
    search_fields = ("sigla", "nome")
    # Define os campos a serem exibidos no formulário de cadastro/edição
    fields = ("sigla", "nome", "municipio")


@admin.register(RelatorioDiario)
class RelatorioDiarioAdmin(admin.ModelAdmin):
    list_display = (
        "nr_relatorio",
        "ano_criacao",
        "data_inicio",
        "data_fim",
        "usuario_responsavel",
        "data_criacao",
    )
    list_filter = ("ano_criacao", "usuario_responsavel")
    search_fields = ("nr_relatorio",)
    # Garante que o usuário responsável seja preenchido automaticamente
    # readonly_fields = ('usuario_responsavel', 'data_criacao')

    # Preenche o campo 'usuario_responsavel' com o usuário logado ao salvar
    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario_responsavel = request.user
        super().save_model(request, obj, form, change)


# SeuApp/admin.py (continuação)


@admin.register(Ocorrencia)
class OcorrenciaAdmin(admin.ModelAdmin):
    # Campos exibidos na lista principal (tabela)
    list_display = (
        "data_hora_fato",
        "natureza",
        "opm",
        "relatorio_diario",
        "resumo_cabecalho",
    )

    # Filtros laterais
    list_filter = ("natureza__tipo_impacto", "opm__municipio", "opm", "natureza")

    # Campos que permitem a busca rápida
    search_fields = (
        "relato_historico",
        "resumo_cabecalho",
        "opm__sigla",
        "natureza__nome",
    )

    # Definição do layout do formulário de cadastro/edição
    fieldsets = (
        (
            "Dados da Ocorrência",
            {
                "fields": (
                    "data_hora_fato",
                    "data_hora_bruta",
                    "natureza",
                    "opm",
                    "relatorio_diario",
                )
            },
        ),
        (
            "Relato e Resumo",
            {
                # Use 'wide' para campos longos
                "fields": ("relato_historico", "resumo_cabecalho"),
                "classes": ("wide",),
            },
        ),
    )

    # Inclusão da tabela de pessoas envolvidas na mesma página
    inlines = [EnvolvidoInline]

    # ORDENAÇÃO: Ordena as ocorrências na listagem pela data mais recente
    ordering = ("-data_hora_fato",)

    # Otimização para campos ForeignKey (autocomplete)
    # Isso transforma o campo FK em um campo de busca, essencial para OPMS ou Relatórios
    autocomplete_fields = ["opm", "relatorio_diario", "natureza"]
