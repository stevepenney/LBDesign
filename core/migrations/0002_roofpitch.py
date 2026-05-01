"""
Move RoofPitch from jobs to core.  Step 1: create the table in core.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RoofPitch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(help_text="Display label, e.g. '15°'", max_length=50)),
                ('pitch_degrees', models.DecimalField(
                    decimal_places=2,
                    max_digits=5,
                    help_text='Roof pitch angle in degrees, e.g. 15, 22.5, 30.',
                )),
                ('sort_order', models.PositiveIntegerField(default=0)),
            ],
            options={
                'ordering': ['sort_order', 'pitch_degrees'],
            },
        ),
    ]
