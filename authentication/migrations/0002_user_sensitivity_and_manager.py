from django.db import migrations, models
import django.db.models.deletion


def give_existing_superusers_top_sensitivity(apps, schema_editor):
    User = apps.get_model('authentication', 'User')
    User.objects.filter(is_superuser=True).update(sensitivity=1000)


class Migration(migrations.Migration):
    dependencies = [('authentication', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='user',
            name='sensitivity',
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name='user',
            name='manager',
            field=models.ForeignKey(blank=True, help_text='The admin/manager responsible for this engineer.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='engineers', to='authentication.user'),
        ),
        migrations.RunPython(give_existing_superusers_top_sensitivity, migrations.RunPython.noop),
    ]
