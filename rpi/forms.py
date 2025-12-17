# SeuApp/forms.py

from django import forms
from .models import Ocorrencia, Envolvido  # Importe todos os modelos necessários


class OcorrenciaForm(forms.ModelForm):

    # Sobrescreve o construtor __init__ para aplicar 'form-control' automaticamente
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Itera sobre todos os campos e adiciona a classe Bootstrap
        for field_name, field in self.fields.items():
            # A classe 'form-control' não deve ser aplicada a Checkboxes ou outros tipos específicos
            # Mas é ideal para TextInputs, Selects, Textareas (que são os tipos padrão do ModelForm)
            if field_name not in ["algum_checkbox_se_existir"]:
                field.widget.attrs["class"] = "form-control"

    class Meta:
        model = Ocorrencia
        fields = [
            "data_hora_bruta",
            "natureza",
            "opm",
            "relato_historico",
            "resumo_cabecalho",
            "relatorio_diario",
        ]

        widgets = {
            # O Textarea precisa de um widget específico para definir 'rows',
            # mas o __init__ adicionará 'form-control'
            "relato_historico": forms.Textarea(attrs={"rows": 6}),
            # O data_hora_bruta usa TextInput (padrão) e adicionamos o placeholder/class
            "data_hora_bruta": forms.TextInput(
                attrs={
                    "placeholder": "Ex: 151435DEZ25"
                }  # 'form-control' será adicionado no __init__
            ),
        }

        labels = {
            "data_hora_bruta": "Data/Hora (Ex: 151435DEZ25)",
            "relato_historico": "Relato Detalhado",
            "resumo_cabecalho": "Resumo para Sumário",
        }


# --- Formulário para o Modelo Envolvido ---


class EnvolvidoForm(forms.ModelForm):

    # Aplica 'form-control' em todos os campos do Formset
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"

    class Meta:
        model = Envolvido
        exclude = ("ocorrencia",)
        labels = {
            "nome": "Nome do Envolvido",
            "tipo_participante": "Participação",
        }
