from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import (
    Ocorrencia,
    Envolvido,
    RelatorioDiario,
    Apreensao,
    OcorrenciaImagem,
    Instrumento,
    MaterialApreendidoTipo,
    NaturezaOcorrencia,
)

# Obtém o modelo de usuário ativo (geralmente User ou CustomUser)
User = get_user_model()


class CadastroUsuarioForm(UserCreationForm):
    # Definição dos campos
    first_name = forms.CharField(label="Primeiro nome", max_length=150, required=False)
    last_name = forms.CharField(label="Último nome", max_length=150, required=False)
    email = forms.EmailField(label="Endereço de email", max_length=254, required=True)

    password2 = forms.CharField(
        label="Confirmação de senha",
        widget=forms.PasswordInput(),
        help_text="Digite a mesma senha informada anteriormente, para verificação.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
        ) + UserCreationForm.Meta.fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Configurações de auxílio e Placeholders
        self.fields['email'].help_text = "Obrigatório: utilize seu e-mail institucional @bm.rs.gov.br"
        self.fields["first_name"].widget.attrs["placeholder"] = "Seu primeiro nome"
        self.fields["last_name"].widget.attrs["placeholder"] = "Seu último nome"
        self.fields["email"].widget.attrs["placeholder"] = "usuario@bm.rs.gov.br"

        # 2. Aplica a classe CSS form-control do Bootstrap a TODOS os campos
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"

    # --- VALIDAÇÕES (CLEAN METHODS) ---

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        dominio_oficial = "@bm.rs.gov.br"
        
        if not email.endswith(dominio_oficial):
            raise forms.ValidationError(
                f"Acesso negado. O e-mail deve pertencer ao domínio {dominio_oficial}."
            )
        return email

    def clean_first_name(self):
        nome = self.cleaned_data.get('first_name')
        return nome.upper() if nome else nome

    def clean_last_name(self):
        sobrenome = self.cleaned_data.get('last_name')
        return sobrenome.upper() if sobrenome else sobrenome

class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'usuario@bm.rs.gov.br'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
    }))


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
        fields = ("nome", "tipo_participante", "idade", "tipo_documento", "nr_documento", "antecedentes")

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
            "municipio",
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
            'imagem': forms.FileInput(attrs={'class': 'form-control form-control-sm', 'onchange': 'previewImage(this)'}),
            'legenda': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Digite a legenda...'}),
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
            


class NaturezaOcorrenciaForm(forms.ModelForm):
    class Meta:
        model = NaturezaOcorrencia
        # Certifique-se de que 'nome' e 'tipo_impacto' são suficientes para o modelo.
        # Incluir 'tags_busca' aqui está OK, se for necessário para a criação.
        fields = ['nome', 'tipo_impacto', 'tags_busca']
        
        widgets = {
            # ✅ Widgets definidos corretamente
            'nome': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_natureza_nome_modal'}),
            'tipo_impacto': forms.Select(attrs={'class': 'form-select', 'id': 'id_natureza_aspecto_modal'}),
            # Se 'tags_busca' for Textarea, defina seu widget aqui
            # 'tags_busca': forms.Textarea(attrs={'class': 'form-control'}),
        }
    
    # ✅ __init__ MOVIDO PARA FORA do Meta class
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Otimização: Aplicar a classe CSS genérica apenas para campos
        # que VOCÊ NÃO DEFINIU explicitamente em 'widgets',
        # ou se precisar de uma customização avançada, mas
        # neste caso, pode ser simplificado.
        
        # Exemplo se você QUISER garantir a classe em TODOS (incluindo tags_busca)
        # e ignorar a redundância:
        for field in self.fields.values():
             # O 'form-select' em tipo_impacto será sobrescrito por form-control, 
             # o que pode ser um bug. Otimize assim:
             if 'class' not in field.widget.attrs:
                 field.widget.attrs['class'] = 'form-control'
             elif 'form-select' not in field.widget.attrs['class']:
                 field.widget.attrs['class'] += ' form-control'
             
             # Melhor ainda: se os widgets já estão definidos, remova o loop
             # ou use-o apenas para setar placeholders.
             
             # Se seu 'tags_busca' é o único que precisa do 'form-control', 
             # a melhor prática é definir o widget dele no 'class Meta'.
             
        # Sugestão: Se você definiu os widgets, pode remover esse __init__
        # se ele não tiver outra finalidade (como setar initial data ou placeholders dinâmicos).