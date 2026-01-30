from django.utils import timezone
from datetime import time, timedelta

def calcular_janela_plantao(data_inicio_str=None, data_fim_str=None):
    # timezone.now() retorna o horário atual com timezone
    agora = timezone.now()
    
    if data_inicio_str and data_fim_str:
        # Converte strings do formulário para datetime às 07:00
        dt_inicio = timezone.make_aware(timezone.datetime.strptime(data_inicio_str, '%Y-%m-%d')).replace(hour=7)
        dt_fim = timezone.make_aware(timezone.datetime.strptime(data_fim_str, '%Y-%m-%d')).replace(hour=6, minute=59, second=59) + timedelta(days=1)
    else:
        # Lógica automática do Plantão Atual
        if agora.time() < time(7, 0):
            data_referencia = agora.date() - timedelta(days=1) # Antes das 07:00, considera o dia anterior
        else:
            data_referencia = agora.date() # Após as 07:00, considera o dia atual
            
        dt_inicio = timezone.make_aware(timezone.datetime.combine(data_referencia, time(7, 0)))
        dt_fim = dt_inicio + timedelta(hours=24) - timedelta(seconds=1)

    return {
        "dt_inicio": dt_inicio,
        "dt_fim": dt_fim,
        "data_inicio_str": data_inicio_str or dt_inicio.strftime('%Y-%m-%d'),
        "data_fim_str": data_fim_str or (dt_fim - timedelta(days=1)).strftime('%Y-%m-%d'),
    }