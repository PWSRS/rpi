from django.db import migrations

def popular_tipos_materiais(apps, schema_editor):
    # Obtemos o modelo do app 'rpi'
    MaterialApreendidoTipo = apps.get_model("rpi", "MaterialApreendidoTipo")
    
    # Lista de tipos para popular o banco inicialmente
    tipos = [
        "Pistola",
        "Revólver",
        "Espingarda",
        "Rádio Comunicador (HT)",
        "Maconha",
        "Cocaína",
        "Crack",
        "Dinheiro (Espécie)",
    ]

    for nome_tipo in tipos:
        # get_or_create evita duplicidade quando rodar a migration novamente
        MaterialApreendidoTipo.objects.get_or_create(nome=nome_tipo)

class Migration(migrations.Migration):

    dependencies = [
        ("rpi", "0002_alter_apreensao_unidade_medida_and_more"),
    ]

    operations = [
        migrations.RunPython(popular_tipos_materiais),
    ]