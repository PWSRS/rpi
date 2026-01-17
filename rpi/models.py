from datetime import datetime
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

# --- UTILITÁRIOS E CONVERSÃO ---

MESES_MAP = {
    "JAN": "01",
    "FEV": "02",
    "MAR": "03",
    "ABR": "04",
    "MAI": "05",
    "JUN": "06",
    "JUL": "07",
    "AGO": "08",
    "SET": "09",
    "OUT": "10",
    "NOV": "11",
    "DEZ": "12",
}


def converter_data_customizada(data_bruta_str):
    """
    Converte a string no formato 'DDHHMMMESAA' (ex: '151435DEZ25') para datetime.
    """
    if not data_bruta_str or len(data_bruta_str) < 11:
        return None

    try:
        dia = data_bruta_str[0:2]
        hora_minuto = data_bruta_str[2:6]
        sigla_mes = data_bruta_str[6:9].upper()
        ano_abrev = data_bruta_str[9:11]

        mes = MESES_MAP.get(sigla_mes)
        if not mes:
            raise ValueError(f"Sigla de mês desconhecida: {sigla_mes}")

        # Formata para o padrão brasileiro para o strptime
        data_formatada = (
            f"{dia}/{mes}/20{ano_abrev} {hora_minuto[:2]}:{hora_minuto[2:]}"
        )
        return datetime.strptime(data_formatada, "%d/%m/%Y %H:%M")

    except Exception as e:
        print(f"Erro ao converter data customizada '{data_bruta_str}': {e}")
        return None


# --- TABELAS AUXILIARES ---


class NaturezaOcorrencia(models.Model):
    IMPACTO_CHOICES = [
        ("N", "Negativo"),
        ("P", "Positivo"),
    ]
    nome = models.CharField(
        max_length=255, unique=True, verbose_name="Natureza do Fato"
    )
    tipo_impacto = models.CharField(
        max_length=1, choices=IMPACTO_CHOICES, verbose_name="Aspecto"
    )
    # Armazena termos de busca alternativos, separados por vírgula (ex: HOMICIDIO, HD, 121)
    tags_busca = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Tags de Busca (Opcional)",
        help_text="Termos alternativos para pesquisa, separados por vírgula."
    )

    def __str__(self):
        return f"[{self.get_tipo_impacto_display()}] {self.nome}"

    class Meta:
        verbose_name = "Natureza da Ocorrência"
        verbose_name_plural = "Naturezas de Ocorrências"


class Municipio(models.Model):
    nome = models.CharField(
        max_length=100, unique=True, verbose_name="Nome do Município"
    )

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Município"
        verbose_name_plural = "Municípios"


class OPM(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome da OPM")
    sigla = models.CharField(max_length=20, verbose_name="Sigla da OPM", unique=True)
    municipio = models.ForeignKey(
        Municipio, on_delete=models.PROTECT, related_name="opms"
    )

    def __str__(self):
        return f"{self.sigla} - {self.municipio.nome}"

    class Meta:
        verbose_name = "OPM"
        verbose_name_plural = "OPMs"
        unique_together = ("nome", "municipio")


# --- MODELO DE AGRUPAMENTO (RELATÓRIO) ---


class RelatorioDiario(models.Model):
    nr_relatorio = models.PositiveIntegerField(verbose_name="Número do Relatório")
    ano_criacao = models.PositiveIntegerField(verbose_name="Ano de Criação")
    data_inicio = models.DateTimeField(verbose_name="Início do Período (24h)")
    data_fim = models.DateTimeField(
        null=True, blank=True, verbose_name="Fim do Período (24h)"
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    finalizado = models.BooleanField(default=False, verbose_name="Relatório Finalizado")
    usuario_responsavel = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="relatorios_diarios"
    )

    @classmethod
    def obter_relatorio_atual(cls, usuario):
        # Verifica se o usuário é real antes de filtrar
        if not usuario or usuario.is_anonymous:
            return None
        return cls.objects.filter(usuario_responsavel=usuario, finalizado=False).last()

    class Meta:
        unique_together = ("nr_relatorio", "ano_criacao")
        verbose_name = "Relatório Diário"
        verbose_name_plural = "Relatórios Diários"


# --- ENTIDADE PRINCIPAL E RELACIONADAS ---


class OcorrenciaImagem(models.Model):
    """
    Modelo para armazenar múltiplas imagens relacionadas a uma ocorrência.
    O relacionamento ForeignKey com Ocorrencia permite o 'Um-para-Muitos'.
    """

    # CRÍTICO: Relacionamento One-to-Many com Ocorrencia
    ocorrencia = models.ForeignKey(
        "Ocorrencia",  # Usa string se a classe Ocorrencia estiver abaixo ou em outro arquivo
        on_delete=models.CASCADE,
        related_name="imagens",  # Nome usado para acessar as imagens a partir da Ocorrencia
        verbose_name="Ocorrência",
    )

    # Campo de Imagem: É a imagem real, stored no MEDIA_ROOT/ocorrencias/imagens/
    imagem = models.ImageField(
        upload_to="ocorrencias/imagens/",
        verbose_name="Imagem",
        null=True,  # Permite nulo no DB (Opcional)
        blank=True,  # Permite campo vazio no formulário (Opcional)
    )

    legenda = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Legenda"
    )

    class Meta:
        verbose_name = "Imagem da Ocorrência"
        verbose_name_plural = "Imagens da Ocorrência"
        ordering = ["id"]  # Ordena as imagens pela ordem de inserção

    def __str__(self):
        return f"Imagem de Ocorrência {self.ocorrencia.pk} ({self.legenda or 'Sem Legenda'})"


class Instrumento(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Instrumento"
        verbose_name_plural = "Instrumentos"
        ordering = ["nome"]


class Ocorrencia(models.Model):

    TIPO_ACAO_CHOICES = [
        ("C", "Consumado"),
        ("T", "Tentado"),
    ]
    instrumento = models.ForeignKey(
        Instrumento,
        on_delete=models.SET_NULL,  # Se o instrumento for deletado, a ocorrência permanece como "null"
        null=True,
        blank=True,
        verbose_name="Instrumento utilizado (para CVLI)",
    )

    tipo_acao = models.CharField(
        max_length=1, choices=TIPO_ACAO_CHOICES, default="C", verbose_name="Ação"
    )

    data_hora_bruta = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Formato DDHHMMMESAA (Ex: 151435DEZ25)",
        verbose_name="Data/Hora Customizada",
    )
    # Definido como null/blank pois o preenchimento ocorre no save()
    data_hora_fato = models.DateTimeField(
        verbose_name="Data e Hora do Fato (DB)", null=True, blank=True
    )

    natureza = models.ForeignKey(
        NaturezaOcorrencia, on_delete=models.PROTECT, related_name="ocorrencias"
    )
    relatorio_diario = models.ForeignKey(
        RelatorioDiario, on_delete=models.PROTECT, related_name="ocorrencias"
    )
    opm = models.ForeignKey(
        OPM,
        on_delete=models.PROTECT,
        related_name="ocorrencias",
        verbose_name="OPM do Fato",
    )

    relato_historico = models.TextField(blank=True, verbose_name="Histórico Detalhado")
    resumo_cabecalho = models.CharField(
        max_length=255, blank=True, verbose_name="Resumo para Sumário"
    )
    rua = models.CharField(
        max_length=255, verbose_name="Rua/Via", blank=True, null=True
    )
    numero = models.CharField(
        max_length=10, blank=True, null=True, verbose_name="Número"
    )
    bairro = models.CharField(
        max_length=100, verbose_name="Bairro", blank=True, null=True
    )

    def __str__(self):
        data_str = (
            self.data_hora_fato.strftime("%d/%m %H:%M")
            if self.data_hora_fato
            else "Sem Data"
        )
        return f"Ocorrência ({self.natureza.nome}) em {data_str}"

    def save(self, *args, **kwargs):
        # Converte a data militar para datetime do Python antes de salvar
        if self.data_hora_bruta:
            data_convertida = converter_data_customizada(self.data_hora_bruta)
            if data_convertida:
                self.data_hora_fato = data_convertida
            else:
                raise ValidationError(
                    {"data_hora_bruta": "Formato de data inválido. Use DDHHMMMESAA."}
                )

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Ocorrência"
        verbose_name_plural = "Ocorrências"


class Envolvido(models.Model):
    TIPO_PARTICIPANTE_CHOICES = [
        ("V", "Vítima"),
        ("A", "Autor"),
        ("M", "Menor Infrator"),
        ("P", "Preso"),
        ("T", "Testemunha"),
        ("S", "Suspeito"),
    ]
    ANTECEDENTES_CHOICES = [
        ("S", "Sim"),
        ("N", "Não"),
        ("I", "N/D"),  # Opção para casos em que o status é desconhecido
    ]
    
    TIPO_DOCUMENTO = [
        ("1", "RG"),
        ("2", "CPF"),
    ]
    
    tipo_documento = models.CharField(
        max_length=1,
        choices=TIPO_DOCUMENTO,
        verbose_name="Documento",
    )
    
    nr_documento = models.CharField(max_length=14, blank=True, null=True, verbose_name="Nr",)
    
    antecedentes = models.CharField(
        max_length=1,
        choices=ANTECEDENTES_CHOICES,
        default="I",
        verbose_name="Antec.",
    )
    nome = models.CharField(max_length=255)
    tipo_participante = models.CharField(
        max_length=1, choices=TIPO_PARTICIPANTE_CHOICES, verbose_name="Tipo",
    )
    ocorrencia = models.ForeignKey(
        Ocorrencia, on_delete=models.CASCADE, related_name="envolvidos"
    )
    idade = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_participante_display()})"

    def save(self, *args, **kwargs):
        # Garante que nomes de pessoas sejam salvos em CAIXA ALTA
        if self.nome:
            self.nome = self.nome.upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Envolvido"
        verbose_name_plural = "Envolvidos"

# --- TABELA AUXILIAR PARA TIPOS DE MATERIAIS ---
class MaterialApreendidoTipo(models.Model):
    # Ex: 'Pistola', 'Maconha', 'Munição Cal .40'
    nome = models.CharField(
        max_length=255, unique=True, verbose_name="Tipo de Material"
    )

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Tipo de Material Apreendido"
        verbose_name_plural = "Tipos de Materiais Apreendidos"
        ordering = ["nome"]


# --- ENTIDADE DE RELACIONAMENTO (APREENSÃO) ---
class Apreensao(models.Model):
    ocorrencia = models.ForeignKey(
        "Ocorrencia", on_delete=models.CASCADE, related_name="apreensoes"
    )
    material_tipo = models.ForeignKey(
        MaterialApreendidoTipo,
        on_delete=models.PROTECT,
        verbose_name="Material Apreendido",
    )
    quantidade = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Quantidade",
        help_text="Use vírgula para separar (Ex: 10.50 ou 1)",
        default=1,
    )

    # Exemplo: 'unidades', 'gramas', 'metros', 'reais'
    unidade_medida = models.CharField(
        max_length=50, blank=True, verbose_name="Unidade de Medida"
    )
    
    descricao_adicional = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Descrição Adicional"
    )

    def __str__(self):
        return f"{self.quantidade} {self.unidade_medida} de {self.material_tipo.nome}"

    class Meta:
        verbose_name = "Apreensão"
        verbose_name_plural = "Apreensões"
