from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_freightsettings_hardware_allowance_pct'),
    ]

    operations = [
        migrations.AddField(
            model_name='freightsettings',
            name='estimate_uncertainty_pct',
            field=models.DecimalField(
                decimal_places=2,
                default=30.0,
                help_text='Total uncertainty band % for estimates. Displayed to merchants as ±half this value (e.g. 30 → ±15%).',
                max_digits=5,
            ),
        ),
    ]
