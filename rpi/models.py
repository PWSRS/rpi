from datetime import datetime
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()

# --- TABELAS AUXILIARES ---

# Mapeamento para conversão do formato militar
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
    # Verifica o comprimento (DD HH MM MES AA -> 12 caracteres)
    if not data_bruta_str or len(data_bruta_str) < 11:
        return None

    try:
        # 1. Extrai as partes
        dia = data_bruta_str[0:2]
        hora_minuto = data_bruta_str[2:6]
        # Converte para maiúsculas para garantir que a busca no mapeamento funcione
        sigla_mes = data_bruta_str[6:9].upper()
        ano_abrev = data_bruta_str[9:11]

        # 2. Converte a sigla do mês para número
        mes = MESES_MAP.get(sigla_mes)
        if not mes:
            raise ValueError(f"Sigla de mês desconhecida: {sigla_mes}")

        # 3. Formata a string para o padrão esperado pelo datetime.strptime
        # Assumindo que "25" refere-se a "2025"
        data_formatada = (
            f"{dia}/{mes}/20{ano_abrev} {hora_minuto[:2]}:{hora_minuto[2:]}"
        )

        # 4. Cria e retorna o objeto datetime
        return datetime.strptime(data_formatada, "%d/%m/%Y %H:%M")

    except Exception as e:
        print(f"Erro ao converter data customizada '{data_bruta_str}': {e}")
        # Retorna None para que o método save possa lidar com o erro
        return None


class NaturezaOcorrencia(models.Model):
    IMPACTO_CHOICES = [
        ("N", "Negativo"),
        ("P", "Positivo"),
    ]
    nome = models.CharField(
        max_length=255, unique=True, verbose_name="Natureza do Fato"
    )  # Adicionado verbose_name
    tipo_impacto = models.CharField(
        max_length=1, choices=IMPACTO_CHOICES, verbose_name="Aspecto"
    )

    def __str__(self):
        return f"[{self.get_tipo_impacto_display()}] {self.nome}"


class Municipio(models.Model):
    nome = models.CharField(
        max_length=100, unique=True, verbose_name="Nome do Município"
    )
    # ... (Meta classes corretas) ...

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
        return f"{self.sigla} - {self.municipio.nome}"  # Melhoria na string

    class Meta:
        verbose_name = "OPM"
        verbose_name_plural = "OPMs"
        unique_together = ("nome", "municipio")


# --- MODELO DE AGRUPAMENTO (RELATÓRIO) ---


class RelatorioDiario(models.Model):
    data_inicio = models.DateTimeField(verbose_name="Início do Período (24h)")
    data_fim = models.DateTimeField(verbose_name="Fim do Período (24h)")
    nr_relatorio = models.PositiveIntegerField(verbose_name="Número do Relatório")
    ano_criacao = models.PositiveIntegerField(verbose_name="Ano de Criação")
    data_criacao = models.DateTimeField(auto_now_add=True)
    usuario_responsavel = models.ForeignKey(
        # Usando User diretamente ou 'auth.User' é OK, mas get_user_model é preferível
        User,
        on_delete=models.PROTECT,
        related_name="relatorios_diarios",
    )

    def __str__(self):
        # Exibição completa do relatório para evitar ambiguidade
        return f"Relatório Nº {self.nr_relatorio}/{self.ano_criacao} | Período: {self.data_inicio.date()}"

    class Meta:
        # CORREÇÃO: Aplicando a restrição de unicidade na combinação (número + ano)
        unique_together = ("nr_relatorio", "ano_criacao")
        verbose_name = "Relatório Diário"
        verbose_name_plural = "Relatórios Diários"


# --- ENTIDADE PRINCIPAL E RELACIONADAS ---


class Ocorrencia(models.Model):
    # Campo que o usuário preenche no Admin (Ex: 151435DEZ25)
    data_hora_bruta = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Formato DDHHMMMESAA (Ex: 151435DEZ25)",
        verbose_name="Data/Hora Customizada",
    )

    # Campo usado pelo Django para filtros e ordenação
    data_hora_fato = models.DateTimeField(verbose_name="Data e Hora do Fato (DB)")

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

    def __str__(self):
        return f"Ocorrência ({self.natureza.nome}) em {self.data_hora_fato.strftime('%d/%m %H:%M')}"

    # Método que será executado antes de salvar no banco de dados
    def save(self, *args, **kwargs):
        if self.data_hora_bruta:
            # Chama a função de conversão
            data_convertida = converter_data_customizada(self.data_hora_bruta)

            if data_convertida:
                # Se for bem-sucedida, preenche o campo de fato com o valor datetime
                self.data_hora_fato = data_convertida
            else:
                # Opcional: Levantar um erro se a conversão falhar e o campo for obrigatório
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    {
                        "data_hora_bruta": "Formato de data e hora customizada inválido. Utilize DDHHMMMESAA."
                    }
                )

        # Chama o save() original para persistir os dados no banco
        super().save(*args, **kwargs)


class Envolvido(models.Model):
    TIPO_PARTICIPANTE_CHOICES = [
        ("V", "Vítima"),
        ("A", "Autor"),
        ("P", "Preso"),
        ("T", "Testemunha"),
        ("S", "Suspeito"),
    ]
    nome = models.CharField(max_length=255)
    tipo_participante = models.CharField(
        max_length=1, choices=TIPO_PARTICIPANTE_CHOICES
    )
    ocorrencia = models.ForeignKey(
        Ocorrencia,
        on_delete=models.CASCADE,
        related_name="envolvidos",  # CASCADE aqui é adequado
    )
    idade = models.PositiveIntegerField(null=True, blank=True)

    # self.get_tipo_participante_display() para exibir o valor legível
    def __str__(self):
        return f"{self.nome} ({self.get_tipo_participante_display()})"
