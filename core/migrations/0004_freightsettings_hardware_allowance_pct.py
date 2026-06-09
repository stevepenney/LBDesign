from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_stairvoidsettings_feedback'),
    ]

    operations = [
        migrations.AddField(
            model_name='freightsettings',
            name='hardware_allowance_pct',
            field=models.DecimalField(
                decimal_places=2,
                default=10.0,
                help_text='Default hardware allowance % applied to all estimates. Individual estimates can override this.',
                max_digits=5,
            ),
        ),
    ]
