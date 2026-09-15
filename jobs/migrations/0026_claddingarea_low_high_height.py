from django.db import migrations, models
from django.db.models import F


def copy_low_to_high(apps, schema_editor):
    CladdingArea = apps.get_model('jobs', 'CladdingArea')
    CladdingArea.objects.update(high_height_m=F('low_height_m'))


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0025_cladding_to_section_finalize'),
    ]

    operations = [
        migrations.RenameField(
            model_name='claddingarea',
            old_name='height_m',
            new_name='low_height_m',
        ),
        migrations.AddField(
            model_name='claddingarea',
            name='high_height_m',
            field=models.DecimalField(max_digits=8, decimal_places=2, default=0),
            preserve_default=False,
        ),
        migrations.RunPython(copy_low_to_high, migrations.RunPython.noop),
    ]
