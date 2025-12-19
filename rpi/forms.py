from django import forms
from .models import Ocorrencia, Envolvido, RelatorioDiario
from django.forms import DateTimeInput, TextInput, Textarea


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
                    "placeholder": "Descreva detalhadamente o fato ocorrido...",
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
            "data_hora_bruta": "Data/Hora Militar (DDHHMMMESAA)",
            "natureza": "Natureza do Fato",
            "opm": "Unidade Responsável (OPM)",
            "rua": "Rua/Via do Fato",
            "numero": "Número",
            "bairro": "Bairro",
            "tipo_acao": "Ação (Consumado/Tentado)",
            "relato_historico": "Relato Detalhado",
            "resumo_cabecalho": "Resumo para o Sumário",
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
            "tipo_participante": "Tipo de Envolvimento",
            "idade": "Idade (Anos)",
            "antecedentes": "Antecedentes Criminais",  # Novo Label
        }
