from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.apps import apps
from rpi.models import AuditCleanupLog
from django.conf import settings

class Command(BaseCommand):
    help = 'Limpa o histórico de todos os modelos que utilizam django-simple-history'

    def handle(self, *args, **options):
        # 1. Configurações Iniciais
        #retention_days =90
        # Tenta ler do settings, se não existir, usa 180 como padrão de segurança
        retention_days = getattr(settings, 'AUDIT_LOG_RETENTION_DAYS', 180)
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        total_deleted = 0
        
        self.stdout.write(f"Iniciando limpeza de logs anteriores a {cutoff_date}...")

        try:
            # 2. Pegar todos os modelos do projeto
            all_models = apps.get_models()
            
            for model in all_models:
                # Verifica se o modelo tem o atributo 'history'
                if hasattr(model, 'history'):
                    model_name = model.__name__
                    
                    # Executa a exclusão
                    deleted_count, _ = model.history.filter(history_date__lt=cutoff_date).delete()
                    
                    if deleted_count > 0:
                        self.stdout.write(self.style.SUCCESS(f"  - {model_name}: Removidos {deleted_count} registros."))
                        total_deleted += deleted_count
                    else:
                        self.stdout.write(f"  - {model_name}: Nenhum registro antigo.")

            # 3. Salva o sucesso no banco de dados
            AuditCleanupLog.objects.create(
                records_deleted=total_deleted,
                status='Sucesso',
                message=f"Limpeza concluída para registros anteriores a {cutoff_date}."
            )
            
            self.stdout.write(self.style.SUCCESS(f"\nTotal geral de registros removidos: {total_deleted}"))

        except Exception as e:
            # 4. Em caso de erro, registra a falha
            error_msg = f"Erro durante a limpeza: {str(e)}"
            AuditCleanupLog.objects.create(
                records_deleted=total_deleted, # Registra o que conseguiu deletar até o erro
                status='Erro',
                message=error_msg
            )
            self.stderr.write(self.style.ERROR(error_msg))