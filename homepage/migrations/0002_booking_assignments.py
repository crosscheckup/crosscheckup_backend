from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('authentication', '0003_user_is_available'),
        ('homepage', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='assigned_admin',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admin_bookings', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='booking',
            name='assigned_engineer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='engineer_bookings', to=settings.AUTH_USER_MODEL),
        ),
    ]
