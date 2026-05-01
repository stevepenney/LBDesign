"""
Create StairVoidSettings singleton (copying value from FreightSettings),
remove stair_void_trimmer_allowance_lm from FreightSettings,
and create the Feedback model.
"""

import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


def copy_allowance_to_stairvoid(apps, schema_editor):
    FreightSettings = apps.get_model('core', 'FreightSettings')
    StairVoidSettings = apps.get_model('core', 'StairVoidSettings')
    try:
        fs = FreightSettings.objects.get(pk=1)
        allowance = fs.stair_void_trimmer_allowance_lm
    except FreightSettings.DoesNotExist:
        allowance = Decimal('0.00')
    StairVoidSettings.objects.get_or_create(pk=1, defaults={'allowance_lm': allowance})


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_roofpitch'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Create StairVoidSettings
        migrations.CreateModel(
            name='StairVoidSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('allowance_lm', models.DecimalField(
                    decimal_places=2,
                    default=0.0,
                    help_text='Standard lineal metre allowance applied when the stair void trimmer toggle is on.',
                    max_digits=8,
                )),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Stair Void Settings',
                'verbose_name_plural': 'Stair Void Settings',
            },
        ),

        # 2. Copy existing value before we drop the column
        migrations.RunPython(copy_allowance_to_stairvoid, migrations.RunPython.noop),

        # 3. Remove the field from FreightSettings
        migrations.RemoveField(
            model_name='freightsettings',
            name='stair_void_trimmer_allowance_lm',
        ),

        # 4. Create Feedback
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_url', models.URLField(max_length=500)),
                ('page_title', models.CharField(blank=True, max_length=255)),
                ('comments', models.TextField()),
                ('screenshot', models.ImageField(blank=True, null=True, upload_to='feedback/')),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='feedback_submissions',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Feedback',
                'verbose_name_plural': 'Feedback',
                'ordering': ['-submitted_at'],
            },
        ),
    ]
