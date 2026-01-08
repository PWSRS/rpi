from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=User)
def avisar_novo_cadastro(sender, instance, created, **kwargs):
    if created:
        # Configurações do e-mail de aviso
        assunto = f"NOVA SOLICITAÇÃO DE ACESSO: {instance.first_name} {instance.last_name}"
        mensagem = (
            f"O policial {instance.first_name} {instance.last_name} solicitou acesso ao sistema RPI.\n"
            f"E-mail: {instance.email}\n"
            f"Número Funcional/Username: {instance.username}\n\n"
            "Acesse o painel administrativo para ativar esta conta se os dados estiverem corretos."
        )
        email_admin = "pablo.weber@hotmail.com"  # Substitua pelo e-mail da administração
        
        try:
            send_mail(
                assunto,
                mensagem,
                'sistema.rpi@bm.rs.gov.br', # Remetente
                [email_admin],
                fail_silently=True,
            )
        except Exception:
            pass # Evita que o erro de envio de e-mail trave o cadastro do usuário