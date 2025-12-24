from django import forms
from django.forms import inlineformset_factory
from .models import Ocorrencia, Envolvido, RelatorioDiario, Apreensao

# --- 1. CLASSES DE FORMULÁRIOS ---


class ApreensaoForm(forms.ModelForm):
    class Meta:
        model = Apreensao
        fields = ["material_tipo", "quantidade", "unidade_medida"]
        widgets = {
            "quantidade": forms.TextInput(
                attrs={"placeholder": "1.00 ou 100", "class": "form-control"}
            ),
            "unidade_medida": forms.TextInput(
                attrs={"placeholder": "Un, g, Kg...", "class": "form-control"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ["quantidade", "unidade_medida"]:
                field.widget.attrs["class"] = "form-control"


class EnvolvidoForm(forms.ModelForm):
    class Meta:
        model = Envolvido
        fields = ("nome", "tipo_participante", "idade", "antecedentes")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

        # 🚨 ESSENCIAL: Descomente estas linhas para não travar o salvamento
        if "antecedentes" in self.fields:
            self.fields["antecedentes"].required = False


class OcorrenciaForm(forms.ModelForm):
    class Meta:
        model = Ocorrencia  # 🚨 ISSO É O QUE ESTAVA FALTANDO E GERANDO O ERRO
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
        widgets = {
            "relato_historico": forms.Textarea(
                attrs={"rows": 6, "placeholder": "Descrição..."}
            ),
            "data_hora_bruta": forms.TextInput(
                attrs={"placeholder": "Ex: 151435DEZ25", "maxlength": "11"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = "form-select"
            elif not isinstance(widget, forms.HiddenInput):
                widget.attrs["class"] = "form-control"


# --- 2. FÁBRICAS DE FORMSETS ---

EnvolvidoFormSet = inlineformset_factory(
    Ocorrencia, Envolvido, form=EnvolvidoForm, extra=1, can_delete=True
)

ApreensaoFormSet = inlineformset_factory(
    Ocorrencia, Apreensao, form=ApreensaoForm, extra=1, can_delete=True
)
