from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from rpi.forms import EmailLoginForm

urlpatterns = [
    # =======================================================
    # ROTAS DE AUTENTICAÇÃO (Mapeadas Explicitamente)
    # Garante que as rotas customizadas usem seus templates (registration/*.html)
    # =======================================================
    # 1. LOGIN
    #path('auth/', include('django.contrib.auth.urls')),
    path(
        "contas/login/",
        auth_views.LoginView.as_view(template_name="rpi/registration/login.html",
        authentication_form=EmailLoginForm),
        name="login",
    ),
    # 2. LOGOUT
    path(
        "contas/logout/",
        auth_views.LogoutView.as_view(template_name="rpi/registration/logged_out.html"),
        name="logout",
    ),
    # 3. ALTERAÇÃO DE SENHA (FORMULÁRIO) - RESOLVE O PROBLEMA INICIAL
    path(
        "contas/password_change/",
        auth_views.PasswordChangeView.as_view(
            # 🟢 AQUI ESTÁ A MUDANÇA: USAR O TEMPLATE DE TESTE 🟢
            template_name="rpi/registration/mudar_senha.html"
        ),
        name="password_change",
    ),
    # 4. ALTERAÇÃO DE SENHA (CONCLUÍDA)
    path(
        "contas/password_change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="rpi/registration/mudar_senha_confirmacao.html"
        ),
        name="password_change_done",
    ),
    # 5. PASSWORD RESET (FORMULÁRIO) - RESOLVE O NoReverseMatch
    path(
        "contas/password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="rpi/registration/esqueci_minha_senha.html"
        ),
        name="password_reset",  # O nome que seu login.html está procurando
    ),
    # 6. PASSWORD RESET (E-MAIL ENVIADO)
    path(
        "contas/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="rpi/registration/esqueci_minha_senha_done.html"
        ),
        name="password_reset_done",
    ),
    # 7. PASSWORD RESET (CONFIRMAÇÃO DO TOKEN)
    path(
        "contas/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="rpi/registration/esqueci_minha_senha_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    # 8. PASSWORD RESET (COMPLETO)
    path(
        "contas/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="rpi/registration/esqueci_minha_senha_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("admin/", admin.site.urls),
    path("", include("rpi.urls")),
    
]
