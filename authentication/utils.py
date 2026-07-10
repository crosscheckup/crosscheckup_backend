import logging

import requests
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'


def _build_verification_content(user, verification_token):
    verification_link = f'{settings.FRONTEND_URL}/auth/verify-email/{verification_token.token}/'
    subject = 'Verify your email address'
    text = (
        f'Hi {user.first_name},\n\n'
        f'Thanks for registering. Please verify your email address by clicking the link below:\n\n'
        f'{verification_link}\n\n'
        f'This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS} hours.\n\n'
        f'If you did not create this account, you can safely ignore this email.\n'
    )
    html = (
        f'<p>Hi {user.first_name},</p>'
        f'<p>Thanks for registering. Please verify your email address by clicking the link below:</p>'
        f'<p><a href="{verification_link}">{verification_link}</a></p>'
        f'<p>This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS} hours.</p>'
        f'<p>If you did not create this account, you can safely ignore this email.</p>'
    )
    print('in build verification content')
    return subject, text, html


def _send_via_brevo(user, subject, text, html):
    """
    Sends over Brevo's REST API (HTTPS/443) instead of raw SMTP. This is what
    lets email delivery work on free-tier hosts like Render, which block
    outbound SMTP ports (25/465/587) but never block normal HTTPS traffic.

    Requires in settings/.env:
        BREVO_API_KEY     - from Brevo dashboard -> SMTP & API -> API Keys
        BREVO_SENDER_EMAIL - an address you've verified as a Brevo "sender"
                              (a plain Gmail address works, no custom domain
                              needed on the free plan)
    """
    payload = {
        'sender': {'email': settings.BREVO_SENDER_EMAIL, 'name': settings.BREVO_SENDER_NAME},
        'to': [{'email': user.email, 'name': user.full_name}],
        'subject': subject,
        'textContent': text,
        'htmlContent': html,
    }
    headers = {
        'api-key': settings.BREVO_API_KEY,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    print('in brevo send email')

    response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=10)

    if response.status_code >= 300:
        logger.error('Brevo email send failed (%s): %s', response.status_code, response.text)
        raise RuntimeError(f'Failed to send verification email via Brevo: {response.text}')


def _send_via_smtp(user, subject, text):
    """
    Falls back to Django's normal SMTP backend (e.g. Gmail SMTP). Only works
    if the host allows outbound traffic on port 587/465 — on Render this
    requires a paid instance type.
    """

    print('in smtp send email')

    send_mail(
        subject=subject,
        message=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_verification_email(user, verification_token):
    """
    Sends the account-verification email. Uses Brevo's HTTP API when
    BREVO_API_KEY is configured (recommended, works on free hosting tiers);
    otherwise falls back to SMTP (settings.EMAIL_BACKEND).
    """
    subject, text, html = _build_verification_content(user, verification_token)

    if getattr(settings, 'BREVO_API_KEY', ''):
        print('in brevo send email')
        _send_via_brevo(user, subject, text, html)
    else:
        _send_via_smtp(user, subject, text)
