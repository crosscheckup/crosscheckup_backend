from django.db import models

# Create your models here.
import secrets
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model. Email is the username field.
    is_active stays False until the user verifies their email address.
    """
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    # Access to operational data is controlled by this application-level
    # sensitivity value, not by Django's admin-site flags.
    SENSITIVITY_USER = 0
    SENSITIVITY_ENGINEER = 100
    SENSITIVITY_ADMIN = 200
    SENSITIVITY_SUPER_ADMIN = 1000

    sensitivity = models.PositiveIntegerField(default=SENSITIVITY_USER, db_index=True)
    is_available = models.BooleanField(
        default=True,
        help_text='Whether an engineer is currently available for a new order.',
    )
    manager = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='engineers',
        help_text='The admin/manager responsible for this engineer.',
    )
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def is_super_admin(self):
        return self.sensitivity >= self.SENSITIVITY_SUPER_ADMIN

    @property
    def is_admin_manager(self):
        return self.sensitivity == self.SENSITIVITY_ADMIN

    @property
    def is_engineer(self):
        return self.sensitivity == self.SENSITIVITY_ENGINEER


class AuthToken(models.Model):
    """
    Login token used for protected API endpoints.
    Unlike DRF's built-in Token, this one expires after a period of
    inactivity (no API calls) rather than only on logout.
    """
    key = models.CharField(max_length=64, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='auth_tokens', on_delete=models.CASCADE
    )
    created = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    @staticmethod
    def generate_key():
        return secrets.token_hex(32)

    def is_expired(self):
        timeout_minutes = settings.TOKEN_INACTIVITY_TIMEOUT_MINUTES
        return timezone.now() > self.last_used + timezone.timedelta(minutes=timeout_minutes)

    def refresh(self):
        """Called on every authenticated request to reset the inactivity clock."""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])

    def __str__(self):
        return f'Token({self.key[:8]}...) for {self.user.email}'


class EmailVerificationToken(models.Model):
    """
    Single-use, time-limited token emailed to the user to confirm their
    address after registration.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='verification_tokens', on_delete=models.CASCADE
    )
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        expiry_hours = settings.EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS
        return timezone.now() > self.created + timezone.timedelta(hours=expiry_hours)

    def __str__(self):
        return f'Verification token for {self.user.email}'
