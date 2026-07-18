import logging

import requests
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'

# Where the "new booking" notification goes. Override in settings.py with
# ADMIN_NOTIFICATION_EMAIL if you want it configurable per-environment.
ADMIN_NOTIFICATION_EMAIL = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', 'crosscheckup@gmail.com')


def _send_via_brevo(to_email, to_name, subject, text, html):
    payload = {
        'sender': {'email': settings.BREVO_SENDER_EMAIL, 'name': settings.BREVO_SENDER_NAME},
        'to': [{'email': to_email, 'name': to_name}],
        'subject': subject,
        'textContent': text,
        'htmlContent': html,
    }
    headers = {
        'api-key': settings.BREVO_API_KEY,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=10)

    if response.status_code >= 300:
        logger.error('Brevo email send failed (%s): %s', response.status_code, response.text)
        raise RuntimeError(f'Failed to send email via Brevo: {response.text}')


def _send_via_smtp(to_email, subject, text):
    send_mail(
        subject=subject,
        message=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=False,
    )


def send_email(to_email, to_name, subject, text, html):
    """
    Sends via Brevo's HTTP API when BREVO_API_KEY is configured (works on
    free hosting tiers that block outbound SMTP ports); otherwise falls
    back to Django's SMTP backend.
    """
    if getattr(settings, 'BREVO_API_KEY', ''):
        _send_via_brevo(to_email, to_name, subject, text, html)
    else:
        _send_via_smtp(to_email, subject, text)


def send_booking_confirmation_email(booking):
    """Email to the customer confirming their booking."""
    subject = 'Your inspection booking is confirmed'
    text = (
        f'Hi {booking.first_name} {booking.last_name},\n\n'
        f'Your booking is successful. Here are the details:\n\n'
        f'City: {booking.city}\n'
        f'Status: {booking.status}\n\n'
        f'We will be in touch shortly to confirm your slot.\n\n'
        f'Thank you!\n'
    )
    html = (
        f'<p>Hi {booking.first_name} {booking.last_name},</p>'
        f'<p>Your booking is <strong>successful</strong>. Here are the details:</p>'
        f'<ul>'
        f'<li><strong>City:</strong> {booking.city}</li>'
        f'<li><strong>Status:</strong> {booking.status}</li>'
        f'</ul>'
        f'<p>We will be in touch shortly to confirm your slot.</p>'
        f'<p>Thank you!</p>'
    )

    try:
        send_email(booking.email, booking.full_name, subject, text, html)
    except Exception:
        # Don't let an email-provider hiccup break the booking API response.
        logger.exception('Failed to send booking confirmation email to %s', booking.email)


def send_booking_notification_email(booking):
    """Internal notification email to the admin inbox."""
    subject = 'New booking received'
    text = (
        f'You have received a new booking.\n\n'
        f'Name: {booking.first_name} {booking.last_name}\n'
        f'Email: {booking.email}\n'
        f'Phone: {booking.phone}\n'
        f'City: {booking.city}\n'
        f'Status: {booking.status}\n'
    )
    html = (
        f'<p>You have received a new booking.</p>'
        f'<ul>'
        f'<li><strong>Name:</strong> {booking.first_name} {booking.last_name}</li>'
        f'<li><strong>Email:</strong> {booking.email}</li>'
        f'<li><strong>Phone:</strong> {booking.phone}</li>'
        f'<li><strong>City:</strong> {booking.city}</li>'
        f'<li><strong>Status:</strong> {booking.status}</li>'
        f'</ul>'
    )

    try:
        send_email(ADMIN_NOTIFICATION_EMAIL, 'Admin', subject, text, html)
    except Exception:
        logger.exception('Failed to send booking notification email to %s', ADMIN_NOTIFICATION_EMAIL)


def send_inspection_account_email(user, password):
    """Send credentials for the account created after an inspection begins."""
    subject = 'Your Crosscheckup account is ready'
    text = (
        f'Hi {user.full_name},\n\n'
        'Your inspection account has been created and is ready to use.\n\n'
        f'Email: {user.email}\n'
        f'Temporary password: {password}\n\n'
        'Please log in and change your password as soon as possible.\n'
    )
    html = (
        f'<p>Hi {user.full_name},</p>'
        '<p>Your inspection account has been created and is ready to use.</p>'
        f'<p><strong>Email:</strong> {user.email}<br>'
        f'<strong>Temporary password:</strong> {password}</p>'
        '<p>Please log in and change your password as soon as possible.</p>'
    )
    try:
        send_email(user.email, user.full_name, subject, text, html)
    except Exception:
        logger.exception('Failed to send inspection account email to %s', user.email)
