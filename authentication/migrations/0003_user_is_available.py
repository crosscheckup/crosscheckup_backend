from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('authentication', '0002_user_sensitivity_and_manager')]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_available',
            field=models.BooleanField(default=True, help_text='Whether an engineer is currently available for a new order.'),
        ),
    ]
