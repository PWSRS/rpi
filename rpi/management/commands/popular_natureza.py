from django.core.management.base import BaseCommand
from rpi.models import NaturezaOcorrencia

class Command(BaseCommand):
    help = "Atualiza ou popula a tabela NaturezaOcorrencia sem apagar registros protegidos"

    def handle(self, *args, **kwargs):
        # Lista atualizada com os crimes e as tags solicitadas
        valores = [
            ("Homicídio Doloso", "N", "Homicídio,Doloso,cvli"),
            ("Feminicídio", "N", "feminicídio,cvli"),
            ("Aborto", "N", "aborto,cvli"),
            ("Lesão Corporal Seguida de Morte", "N", "lcsm,Doloso,cvli"),
            ("Roubo com Morte", "N", "roubo,com morte,morte"),
            ("Latrocínio", "N", "latrocínio,cvli"),
            ("Roubo a Pedestre com Morte", "N", "roubo,pessoa,morte, cvli"),
            ("Roubo a Residência com Morte", "N", "roubo,residência,morte, cvli"),
            ("Roubo a Estabelecimento com Morte", "N", "roubo,estabelecimento, comércio, Doloso,cvli"),
            ("Roubo a Estabelecimento Bancário com Morte", "N", "roubo,banco,morte, cvli"),
            ("Instigação ao Suicídio", "N", "insigação,suicídio,cvli"),
            ("Roubo a Pedestre", "N", "roubo, pessoa, pedestre"),
            ("Recuperação de Veículo", "P", "Recuperado,Veículo,Apreendido"),
            ("Tráfico de Entorpecentes", "N", "tráfico,drogas,entorpecentes"),
            ("Roubo de Veículo", "N", "Roubo,Assalto,veículo"),
            ("Abigeato", "N", "abigeato, animal, furto"),
        ]

        self.stdout.write("Iniciando atualização da tabela NaturezaOcorrencia...")
        
        contador_criado = 0
        contador_atualizado = 0

        for nome, tipo_impacto, tags_busca in valores:
            try:
                # O update_or_create evita o erro de ProtectedError
                # Ele busca pelo 'nome'. Se existir, atualiza os 'defaults'.
                obj, created = NaturezaOcorrencia.objects.update_or_create(
                    nome=nome,
                    defaults={
                        'tipo_impacto': tipo_impacto,
                        'tags_busca': tags_busca
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Registro '{nome}' criado."))
                    contador_criado += 1
                else:
                    self.stdout.write(f"Registro '{nome}' atualizado.")
                    contador_atualizado += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Erro ao processar '{nome}': {e}")
                )

        # Resumo Final
        total = contador_criado + contador_atualizado
        self.stdout.write(
            self.style.SUCCESS(
                f"\nProcesso concluído! {total} registros processados ({contador_criado} novos, {contador_atualizado} atualizados)."
            )
        )