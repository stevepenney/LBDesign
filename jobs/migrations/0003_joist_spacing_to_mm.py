"""
Change FloorRoofArea.joist_spacing from CharField (choices, stored as '0.400')
to PositiveIntegerField (stored as mm, e.g. 400).

Data migration converts existing rows: 0.400 → 400, 0.450 → 450, 0.600 → 600.
"""

from django.db import migrations, models


def spacing_str_to_mm(apps, schema_editor):
    FloorRoofArea = apps.get_model('jobs', 'FloorRoofArea')
    mapping = {'0.400': 400, '0.450': 450, '0.600': 600}
    for area in FloorRoofArea.objects.all():
        area.joist_spacing_mm = mapping.get(area.joist_spacing, 400)
        area.save(update_fields=['joist_spacing_mm'])


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0002_add_product_description_fields'),
    ]

    operations = [
        # Step 1: add the new integer column (nullable so existing rows are OK)
        migrations.AddField(
            model_name='floorroofarea',
            name='joist_spacing_mm',
            field=models.PositiveIntegerField(
                null=True,
                help_text='Joist / rafter spacing in mm, e.g. 400, 450, 600.',
            ),
        ),
        # Step 2: populate the new column from the old one
        migrations.RunPython(spacing_str_to_mm, migrations.RunPython.noop),
        # Step 3: drop the old column
        migrations.RemoveField(
            model_name='floorroofarea',
            name='joist_spacing',
        ),
        # Step 4: rename new column to 'joist_spacing'
        migrations.RenameField(
            model_name='floorroofarea',
            old_name='joist_spacing_mm',
            new_name='joist_spacing',
        ),
        # Step 5: make it non-nullable now that all rows have a value
        migrations.AlterField(
            model_name='floorroofarea',
            name='joist_spacing',
            field=models.PositiveIntegerField(
                help_text='Joist / rafter spacing in mm, e.g. 400, 450, 600.',
            ),
        ),
    ]
