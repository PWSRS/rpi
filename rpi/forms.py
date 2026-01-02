from django import forms
from django.forms import inlineformset_factory
from .models import (
    Ocorrencia,
    Envolvido,
    RelatorioDiario,
    Apreensao,
    OcorrenciaImagem,
    Instrumento,
)

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
        model = Ocorrencia
        fields = [
            "data_hora_bruta",
            "natureza",
            "tipo_acao",
            "instrumento",  # Agora ele carregará todos os Instrumentos do banco
            "opm",
            "rua",
            "numero",
            "bairro",
            "resumo_cabecalho",
            "relato_historico",
        ]
        widgets = {
            "relato_historico": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Relate detalhadamente o fato..."}
            ),
            "resumo_cabecalho": forms.TextInput(
                attrs={"placeholder": "Breve título para o sumário"}
            ),
            "data_hora_bruta": forms.TextInput(
                attrs={"placeholder": "Ex: 151435DEZ25", "maxlength": "15"}
            ),
            "rua": forms.TextInput(attrs={"placeholder": "Nome da rua/avenida"}),
            "numero": forms.TextInput(attrs={"placeholder": "Nº"}),
            "bairro": forms.TextInput(attrs={"placeholder": "Bairro"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Otimização: Ordenar os instrumentos por nome no dropdown do formulário
        if "instrumento" in self.fields:
            self.fields["instrumento"].queryset = Instrumento.objects.all().order_by(
                "nome"
            )
            self.fields["instrumento"].empty_label = "Selecione o instrumento..."

        # Aplicação automática de classes CSS (Bootstrap)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = "form-select"
            elif not isinstance(widget, (forms.HiddenInput, forms.CheckboxInput)):
                widget.attrs["class"] = "form-control"


class OcorrenciaImagemForm(forms.ModelForm):
    class Meta:
        model = OcorrenciaImagem
        fields = ("imagem", "legenda")
        widgets = {
            # ESSENCIAL: Garante que o input de arquivo tenha o estilo form-control
            "imagem": forms.FileInput(attrs={"class": "form-control"}),
            "legenda": forms.TextInput(attrs={"class": "form-control"}),
        }


# --- 2. FÁBRICAS DE FORMSETS ---

EnvolvidoFormSet = inlineformset_factory(
    Ocorrencia, Envolvido, form=EnvolvidoForm, extra=1, can_delete=True
)

ApreensaoFormSet = inlineformset_factory(
    Ocorrencia, Apreensao, form=ApreensaoForm, extra=1, can_delete=True
)

ImagemFormSet = inlineformset_factory(
    Ocorrencia,
    OcorrenciaImagem,
    form=OcorrenciaImagemForm,  # AGORA USAMOS A CLASSE CUSTOMIZADA
    extra=1,
    can_delete=True,
)
class InstrumentoForm(forms.ModelForm):
    class Meta:
        model = Instrumento
        fields = ["nome"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"