from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import (
    Ocorrencia,
    Envolvido,
    RelatorioDiario,
    Apreensao,
    OcorrenciaImagem,
    Instrumento,
    MaterialApreendidoTipo,
)

# Obtém o modelo de usuário ativo (geralmente User ou CustomUser)
User = get_user_model()


class CadastroUsuarioForm(UserCreationForm):
    # Campos adicionais com labels em português e atributos
    first_name = forms.CharField(label="Primeiro nome", max_length=150, required=False)
    last_name = forms.CharField(label="Último nome", max_length=150, required=False)
    email = forms.EmailField(label="Endereço de email", max_length=254, required=True)

    # Customizando a label da Confirmação de senha
    password2 = forms.CharField(
        label="Confirmação de senha",
        widget=forms.PasswordInput(),
        help_text="Digite a mesma senha informada anteriormente, para verificação.",
    )

    class Meta(UserCreationForm.Meta):
        model = User

        # 1. Lista os campos na ordem correta, garantindo que 'password' e 'password2'
        # VENHAM DEPOIS dos campos de informação pessoal.
        # Usa o 'UserCreationForm.Meta.fields' para INCLUIR os campos de senha
        # (que são ('password', 'password2')) de uma só vez, no final.
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
        ) + UserCreationForm.Meta.fields  # Isso adiciona ('password', 'password2') no final.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Aplica a classe form-control a TODOS os campos
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"

        # Adiciona placeholders
        self.fields["first_name"].widget.attrs["placeholder"] = "Seu primeiro nome"
        self.fields["last_name"].widget.attrs["placeholder"] = "Seu último nome"
        self.fields["email"].widget.attrs["placeholder"] = "exemplo@dominio.com"





# --- 1. CLASSES DE FORMULÁRIOS ---


class ApreensaoForm(forms.ModelForm):
    class Meta:
        model = Apreensao
        fields = ["material_tipo", "descricao_adicional", "quantidade", "unidade_medida"]
        widgets = {
            "quantidade": forms.TextInput(
                attrs={"placeholder": "1.00 ou 100", "class": "form-control"}
            ),
            "unidade_medida": forms.TextInput(
                attrs={"placeholder": "Un, g, Kg...", "class": "form-control"}
            ),
            "descricao_adicional": forms.TextInput(
                attrs={"placeholder": "Descrição adicional...", "class": "form-control"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ["quantidade", "descricao_adicional", "unidade_medida"]:
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
        
        # Transformar automaticamente o resumo do cabeçalho em maiúsculas
        self.fields['resumo_cabecalho'].widget.attrs.update({
            'style': 'text-transform: uppercase;',
            'oninput': 'this.value = this.value.toUpperCase()'
        })

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
            
class MaterialApreendidoTipoForm(forms.ModelForm):
    class Meta:
        model = MaterialApreendidoTipo
        fields = ["nome"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"