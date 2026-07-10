from django.conf import settings
from django.core.mail import send_mail


def send_verification_email(user, verification_token):
    """
    Sends the account-verification email via Gmail SMTP
    (configured in settings.py through EMAIL_HOST_USER / EMAIL_HOST_PASSWORD).
    """
    verification_link = f'{settings.FRONTEND_URL}/auth/verify-email/{verification_token.token}/'

    subject = 'Verify your email address'
    message = (
        f'Hi {user.first_name},\n\n'
        f'Thanks for registering. Please verify your email address by clicking the link below:\n\n'
        f'{verification_link}\n\n'
        f'This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS} hours.\n\n'
        f'If you did not create this account, you can safely ignore this email.\n'
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
