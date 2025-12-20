from django import forms
from .models import (
    Ocorrencia,
    Envolvido,
    RelatorioDiario,
    Apreensao,
    MaterialApreendidoTipo,
)
from django.forms import DateTimeInput, TextInput, Textarea


class ApreensaoForm(forms.ModelForm):
    class Meta:
        model = Apreensao
        fields = ["material_tipo", "quantidade", "unidade_medida"]

        widgets = {
            # Adicionando 'form-control' no campo quantidade
            "quantidade": forms.TextInput(
                attrs={
                    "placeholder": "1.00 ou 100",
                    "class": "form-control",  # CLASSE ADICIONADA AQUI
                }
            ),
            # Adicionando 'form-control' no campo unidade_medida
            "unidade_medida": forms.TextInput(
                attrs={
                    "placeholder": "Un, g, Kg, Pés, R$...",
                    "class": "form-control",  # CLASSE ADICIONADA AQUI
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Itera sobre os campos para adicionar a classe 'form-control' ao Select (material_tipo)
        # e a qualquer outro campo que tenha sido esquecido.
        for field_name, field in self.fields.items():
            if field_name not in ["quantidade", "unidade_medida"] and field.widget:
                # O campo 'material_tipo' (Select) será pego aqui
                current_classes = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = current_classes + " form-control"


class RelatorioDiarioForm(forms.ModelForm):
    """Formulário para abrir o dia/serviço"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"

    class Meta:
        model = RelatorioDiario
        fields = ["nr_relatorio", "ano_criacao", "data_inicio", "data_fim"]
        widgets = {
            "data_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "data_fim": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class OcorrenciaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1. Aplica a classe 'form-control' se o widget NÃO for um Select ou Hidden Input
        for field_name, field in self.fields.items():
            widget = field.widget

            # Condição para aplicar 'form-control'
            is_select = isinstance(widget, forms.Select) or isinstance(
                widget, forms.SelectMultiple
            )
            is_hidden = isinstance(widget, forms.HiddenInput)

            if not is_select and not is_hidden:
                # Aplica 'form-control' a TextInputs, Textareas, etc.
                current_classes = widget.attrs.get("class", "")
                if "form-control" not in current_classes:
                    widget.attrs["class"] = current_classes + " form-control"

            elif is_select:
                # 2. Aplica a classe 'form-select' (necessário para Bootstrap 5 e Select2)
                current_classes = widget.attrs.get("class", "")
                if "form-select" not in current_classes:
                    widget.attrs["class"] = current_classes + " form-select"

    class Meta:
        model = Ocorrencia
        fields = [
            "data_hora_bruta",
            "natureza",
            "opm",
            "rua",
            "numero",
            "bairro",
            "tipo_acao",
            "relato_historico",
            "resumo_cabecalho",
        ]

        # Os widgets que você já definiu estão OK, mas garantimos as classes via __init__
        widgets = {
            "relato_historico": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": "Descrição do fato...",
                }
            ),
            "data_hora_bruta": forms.TextInput(
                attrs={"placeholder": "Ex: 151435DEZ25", "maxlength": "11"}
            ),
            "resumo_cabecalho": forms.TextInput(
                attrs={"placeholder": "Título curto da ocorrência"}
            ),
            # Não é necessário definir 'natureza', 'opm' e 'tipo_acao' aqui,
            # pois eles já são Selects e o __init__ cuidará da classe 'form-select'.
        }

        labels = {
            "data_hora_bruta": "Data/Hora (DDHHMMMESAA)",
            "natureza": "Natureza da Ocorrência",
            "opm": "(OPM)",
            "rua": "Endere",
            "numero": "Número",
            "bairro": "Bairro",
            "tipo_acao": "Tipo do Fato (Consumado/Tentado)",
            "relato_historico": "Relato Detalhado",
            "resumo_cabecalho": "Título Sumário",
        }


class EnvolvidoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"

    class Meta:
        model = Envolvido
        # O campo 'ocorrencia' fica de fora
        # Excluímos o campo de antecedente para usarmos o `fields`
        fields = (
            "nome",
            "tipo_participante",
            "idade",
            "antecedentes",  # <--- NOVO CAMPO
        )

        widgets = {
            "idade": forms.NumberInput(attrs={"min": 0, "max": 150}),
        }

        labels = {
            "nome": "Nome Completo",
            "tipo_participante": "Tipo de Participação",
            "idade": "Idade (Anos)",
            "antecedentes": "Antecedentes Criminais",  # Novo Label
        }
