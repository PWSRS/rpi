from django.contrib import admin
from .models import (
    NaturezaOcorrencia,
    Municipio,
    OPM,
    RelatorioDiario,
    Ocorrencia,
    OcorrenciaImagem,
    Envolvido,
    Apreensao,
    MaterialApreendidoTipo,
    Instrumento,
)

# ----------------- 1. CONFIGURAÇÃO DE INLINES -----------------


class EnvolvidoInline(admin.TabularInline):
    """
    Inline para o modelo Envolvido. Usado dentro da OcorrenciaAdmin.
    Configuração: Tabular, mínimo 1, campos detalhados.
    """

    model = Envolvido
    extra = 0  # Não adiciona linhas extras vazias por padrão
    min_num = 1  # Garante pelo menos um envolvido
    # Campos que aparecerão no inline
    fields = ("tipo_participacao", "nome", "cpf_cnpj", "contato", "observacoes")
    # Campos de busca (para a FK de Pessoa, se houver)
    # autocomplete_fields = ["nome"] # Descomente se 'nome' for uma FK para um modelo grande


class ApreensaoInline(admin.TabularInline):
    """
    Inline para o modelo Apreensao. Usado dentro da OcorrenciaAdmin.
    Configuração: Tabular, 1 linha extra por padrão.
    """

    model = Apreensao
    extra = 1  # Adiciona 1 linha extra vazia por padrão
    # Campos que aparecerão no inline
    fields = ("material_tipo", "quantidade", "unidade_medida")
    # Otimização para campo ForeignKey 'material_tipo'
    autocomplete_fields = ["material_tipo"]


# ----------------- 2. REGISTROS DE MODELOS AUXILIARES -----------------


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

    # Preenche o campo 'usuario_responsavel' com o usuário logado ao salvar
    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario_responsavel = request.user
        super().save_model(request, obj, form, change)


@admin.register(MaterialApreendidoTipo)
class MaterialApreendidoTipoAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)


class OcorrenciaImagemInline(admin.TabularInline):
    """Configuração para cadastrar múltiplas imagens em linha."""

    model = OcorrenciaImagem
    extra = 1  # Quantidade de formulários extras para imagens
    fields = (
        "imagem",
        "legenda",
    )


# ----------------- 3. MODEL ADMIN PRINCIPAL (OCORRENCIA) -----------------


@admin.register(Ocorrencia)
class OcorrenciaAdmin(admin.ModelAdmin):
    # 1. Campos exibidos na listagem principal
    list_display = (
        "data_hora_fato",
        "natureza",
        "tipo_acao",    # Adicionei para você ver se é Consumado/Tentado
        "instrumento",   # O novo campo ForeignKey
        "opm",
        "relatorio_diario",
    )

    # 2. Filtros laterais
    # Adicionado 'instrumento' e 'tipo_acao' nos filtros
    list_filter = (
        "natureza__tipo_impacto", 
        "tipo_acao",
        "instrumento", 
        "opm__municipio", 
        "opm", 
        "natureza"
    )

    # 3. Campos de busca
    search_fields = (
        "relato_historico",
        "resumo_cabecalho",
        "opm__sigla",
        "natureza__nome",
    )

    # 4. Layout do formulário (Fieldsets)
    fieldsets = (
        (
            "Dados da Ocorrência",
            {
                "fields": (
                    ("data_hora_fato", "data_hora_bruta"),
                    ("natureza", "tipo_acao"), # Agrupados na mesma linha
                    "instrumento",              # Novo campo aqui
                    "opm",
                    "relatorio_diario",
                )
            },
        ),
        (
            "Localização",
            {
                "fields": (("rua", "numero"), "bairro"),
            },
        ),
        (
            "Relato e Resumo",
            {
                "fields": ("relato_historico", "resumo_cabecalho"),
                "classes": ("wide",),
            },
        ),
    )

    # 5. Inlines (Agrupados em uma única lista)
    inlines = [OcorrenciaImagemInline, EnvolvidoInline, ApreensaoInline]

    # 6. Ordenação
    ordering = ("-data_hora_fato",)

    # 7. Autocomplete (Otimização)
    # IMPORTANTE: Para o autocomplete do instrumento funcionar, 
    # você deve registrar o InstrumentoAdmin com search_fields=['nome']
    autocomplete_fields = ["opm", "relatorio_diario", "natureza", "instrumento"]

@admin.register(Instrumento)
class InstrumentoAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)



