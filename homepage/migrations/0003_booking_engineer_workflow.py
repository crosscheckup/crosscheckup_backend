from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import homepage.storage


class Migration(migrations.Migration):

    dependencies = [
        ('homepage', '0002_booking_assignments'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='customer_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customer_bookings', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='booking',
            name='document',
            field=models.FileField(blank=True, null=True, storage=homepage.storage.InspectionDocumentStorage(), upload_to='inspection_documents/'),
        ),
        migrations.AlterField(
            model_name='booking',
            name='status',
            field=models.CharField(choices=[('booked', 'Booked'), ('processing', 'Inspection processing'), ('cancelled', 'Cancelled'), ('completed', 'Completed')], default='booked', max_length=20),
        ),
    ]
