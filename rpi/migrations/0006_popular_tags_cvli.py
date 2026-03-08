from django.db import migrations

def adicionar_tags_cvli(apps, schema_editor):
    # Obtemos a model dinamicamente para garantir compatibilidade
    NaturezaOcorrencia = apps.get_model('rpi', 'NaturezaOcorrencia')
    
    palavras_chave = ['HOMICIDIO', 'LATROCINIO', 'FEMINICIDIO', 'MORTE', 'LESAO CORPORAL SEGUIDA', 'LATROCINIO', 'HOMICIDIO TENTADO']
    
    for nat in NaturezaOcorrencia.objects.all():
        nome_upper = nat.nome.upper()
        if any(p in nome_upper for p in palavras_chave):
            # Lógica para não duplicar e manter as tags atuais
            tags_atuais = nat.tags_busca or ""
            if 'CVLI' not in tags_atuais.upper():
                separador = ", " if tags_atuais else ""
                nat.tags_busca = f"{tags_atuais}{separador}CVLI"
                nat.save()

def remover_tags_cvli(apps, schema_editor):
    # Função para o caso de você querer dar um "Rollback" (opcional)
    NaturezaOcorrencia = apps.get_model('rpi', 'NaturezaOcorrencia')
    for nat in NaturezaOcorrencia.objects.filter(tags_busca__icontains='CVLI'):
        # Remove apenas a palavra CVLI e limpa as vírgulas
        nova_tag = nat.tags_busca.replace('CVLI', '').replace(', ,', ',').strip(', ')
        nat.tags_busca = nova_tag
        nat.save()

class Migration(migrations.Migration):

    dependencies = [
        ('rpi', '0005_envolvido_foto_historicalenvolvido_foto'), # O Django preencherá isso sozinho
    ]

    operations = [
        migrations.RunPython(adicionar_tags_cvli, reverse_code=remover_tags_cvli),
    ]