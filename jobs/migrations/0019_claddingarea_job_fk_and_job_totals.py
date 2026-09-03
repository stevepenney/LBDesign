# Flattens the Cladding Estimator: CladdingArea moves from Section to Job (a cladding
# estimate has no per-physical-system settings for a Section to hold — elevations are
# areas, not sections, from a data perspective). See CLAUDE.md "Cladding Estimator".
#
# Follows 0018 (already applied wherever the cladding feature has shipped) rather than
# replacing it — a migration that's already run in a shared/production database must
# never be rewritten, only built on top of.

import django.db.models.deletion
from django.db import migrations, models


def populate_cladding_area_job(apps, schema_editor):
    CladdingArea = apps.get_model('jobs', 'CladdingArea')
    for area in CladdingArea.objects.select_related('section').all():
        area.job_id = area.section.job_id
        area.save(update_fields=['job'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0018_alter_section_system_type_claddingarea'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='calculated_subtotal',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='job',
            name='member_schedule',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='claddingarea',
            name='job',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cladding_areas', to='jobs.job'),
        ),
        migrations.RunPython(populate_cladding_area_job, noop_reverse),
        migrations.AlterField(
            model_name='claddingarea',
            name='job',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cladding_areas', to='jobs.job'),
        ),
        migrations.RemoveField(
            model_name='claddingarea',
            name='section',
        ),
        migrations.AlterField(
            model_name='section',
            name='system_type',
            field=models.CharField(choices=[('midfloor', 'Midfloor'), ('roof', 'Roof'), ('other', 'Other')], max_length=10),
        ),
    ]
