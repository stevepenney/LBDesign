"""
Move RoofPitch from jobs to core.  Step 2:
  - Copy existing rows from jobs.RoofPitch → core.RoofPitch (preserving PKs)
  - Repoint SubJob.roof_pitch FK → core.RoofPitch
  - Drop the old jobs.RoofPitch table
"""

import django.db.models.deletion
from django.db import migrations, models


def copy_roof_pitches(apps, schema_editor):
    OldRoofPitch = apps.get_model('jobs', 'RoofPitch')
    NewRoofPitch = apps.get_model('core', 'RoofPitch')
    for old in OldRoofPitch.objects.all():
        NewRoofPitch.objects.get_or_create(
            pk=old.pk,
            defaults={
                'label': old.label,
                'pitch_degrees': old.pitch_degrees,
                'sort_order': old.sort_order,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_roofpitch'),
        ('jobs', '0004_roofpitch_degrees'),
    ]

    operations = [
        # Step 1: copy existing rows into the new core table before touching the FK
        migrations.RunPython(copy_roof_pitches, migrations.RunPython.noop),

        # Step 2: swap the FK to point at core.RoofPitch
        migrations.AlterField(
            model_name='subjob',
            name='roof_pitch',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sub_jobs',
                to='core.roofpitch',
            ),
        ),

        # Step 3: drop the old jobs table
        migrations.DeleteModel(
            name='RoofPitch',
        ),
    ]
