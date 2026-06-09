from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0010_job_finalize_project'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='hardware_allowance_pct',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Override hardware allowance %. Leave blank to use the global default.',
                max_digits=5,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='job',
            name='hardware_allowance_amount',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
            ),
        ),
    ]
