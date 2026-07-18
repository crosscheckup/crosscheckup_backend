from django.db import models
from django.conf import settings

from .storage import InspectionDocumentStorage


class Booking(models.Model):
    """
    A single inspection-booking request submitted from the public form.
    """

    STATUS_BOOKED = 'booked'
    STATUS_PROCESSING = 'processing'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (STATUS_BOOKED, 'Booked'),
        (STATUS_PROCESSING, 'Inspection processing'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=20)
    city = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_BOOKED)
    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='admin_bookings',
    )
    assigned_engineer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='engineer_bookings',
    )
    customer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='customer_bookings',
    )
    document = models.FileField(
        upload_to='inspection_documents/',
        storage=InspectionDocumentStorage(),
        null=True,
        blank=True,
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.email}) - {self.status}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()
