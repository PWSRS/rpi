from django import template
from datetime import datetime

register = template.Library()

# Mapeamento de Mês (Número como string) para a Sigla Militar (Português/Maiúsculas)
MESES_MILITAR_SAIDA = {
    "01": "JAN",
    "02": "FEV",
    "03": "MAR",
    "04": "ABR",
    "05": "MAI",
    "06": "JUN",
    "07": "JUL",
    "08": "AGO",
    "09": "SET",
    "10": "OUT",
    "11": "NOV",
    "12": "DEZ",
}


@register.filter
def formatar_data_militar(data, hora_fixa="0700"):
    """
    Formata um objeto datetime no padrão militar DDHHEstadoEstadoEstadoAno.
    Exemplo: 210700DEZ25
    """
    if not isinstance(data, datetime):
        return data

    # 1. Extrai as partes necessárias
    dia = data.strftime("%d")  # DD
    mes_num = data.strftime("%m")  # MM (ex: 12)
    ano = data.strftime("%y")  # AA (ex: 25)

    # 2. Converte o número do mês para a sigla militar em maiúsculas
    sigla_mes = MESES_MILITAR_SAIDA.get(mes_num, mes_num)

    # 3. Constrói a string final com o horário fixo
    return f"{dia}{hora_fixa}{sigla_mes}{ano}"
