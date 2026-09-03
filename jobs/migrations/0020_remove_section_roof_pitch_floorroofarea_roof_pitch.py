# Moves roof_pitch from Section to FloorRoofArea so one roof Section (e.g. "Unit 1
# Roof") can span multiple pitches across its areas (main roof vs porch, hips, etc.)
# instead of one pitch for the whole section.

import django.db.models.deletion
from django.db import migrations, models


def populate_area_roof_pitch(apps, schema_editor):
    Section = apps.get_model('jobs', 'Section')
    for section in Section.objects.exclude(roof_pitch=None):
        section.areas.update(roof_pitch_id=section.roof_pitch_id)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_alter_systemsettings_options'),
        ('jobs', '0019_claddingarea_job_fk_and_job_totals'),
    ]

    operations = [
        migrations.AddField(
            model_name='floorroofarea',
            name='roof_pitch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='areas', to='core.roofpitch'),
        ),
        migrations.RunPython(populate_area_roof_pitch, noop_reverse),
        migrations.RemoveField(
            model_name='section',
            name='roof_pitch',
        ),
    ]
