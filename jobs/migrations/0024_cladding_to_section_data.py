"""
Data migration: cladding folded into Section.

For every Job that has cladding areas/extra items/cutlist lines (or a
cladding_cutlist/stock_contingency_pct set) attached directly, create one
Section(system_type=CLADDING) and re-parent that data onto it. Preserves the
last-computed subtotal/schedule; hardware_allowance_amount is deliberately
left for a fresh recalculation (it's a derived figure, and the new part
follows the "fresh cladding part defaults to 0% hardware allowance"
convention used by the equivalent code path in jobs.views.section_create).
"""
from django.db import migrations


def migrate_cladding_to_sections(apps, schema_editor):
    Job = apps.get_model('jobs', 'Job')
    Section = apps.get_model('jobs', 'Section')
    CladdingArea = apps.get_model('jobs', 'CladdingArea')
    CladdingExtraItem = apps.get_model('jobs', 'CladdingExtraItem')
    CladdingCutlistLine = apps.get_model('jobs', 'CladdingCutlistLine')

    job_ids = set(CladdingArea.objects.values_list('job_id', flat=True))
    job_ids |= set(CladdingExtraItem.objects.values_list('job_id', flat=True))
    job_ids |= set(CladdingCutlistLine.objects.values_list('job_id', flat=True))
    job_ids |= set(Job.objects.exclude(cladding_cutlist=None).values_list('id', flat=True))
    job_ids.discard(None)

    for job in Job.objects.filter(id__in=job_ids):
        section = Section.objects.create(
            job=job,
            label=job.label or 'Cladding',
            system_type='cladding',
            hardware_allowance_pct='0',
            stock_contingency_pct=job.stock_contingency_pct,
            cladding_cutlist=job.cladding_cutlist,
            calculated_subtotal=job.calculated_subtotal,
            member_schedule=job.member_schedule,
        )
        CladdingArea.objects.filter(job=job).update(section=section)
        CladdingExtraItem.objects.filter(job=job).update(section=section)
        CladdingCutlistLine.objects.filter(job=job).update(section=section)


def noop_reverse(apps, schema_editor):
    # Not reversible — folding back would need to pick one cladding Section per
    # job to collapse back onto the Job, which is lossy if more than one exists.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0023_cladding_to_section_schema'),
    ]

    operations = [
        migrations.RunPython(migrate_cladding_to_sections, noop_reverse),
    ]
