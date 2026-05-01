"""
Replace RoofPitch.pitch_factor (manually-entered multiplier) with
pitch_degrees (angle in degrees). The factor is now a computed property.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0003_joist_spacing_to_mm'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='roofpitch',
            name='pitch_factor',
        ),
        migrations.AddField(
            model_name='roofpitch',
            name='pitch_degrees',
            field=models.DecimalField(
                max_digits=5,
                decimal_places=2,
                default=15,
                help_text='Roof pitch angle in degrees, e.g. 15, 22.5, 30.',
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name='roofpitch',
            options={'ordering': ['sort_order', 'pitch_degrees']},
        ),
    ]
