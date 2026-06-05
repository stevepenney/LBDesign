from django.db import migrations


def populate_project(apps, schema_editor):
    """
    Link each CutlistProject to its Project.
    - If the cutlist has a linked Job, use that job's project.
    - Otherwise create a stub Project from the org alone.
    """
    CutlistProject = apps.get_model('cutlist',   'CutlistProject')
    Project        = apps.get_model('projects',  'Project')

    from django.db.models import Max
    counter_base = Project.objects.aggregate(Max('lb_job_number'))['lb_job_number__max'] or 0
    counter = counter_base + 1

    for cp in CutlistProject.objects.select_related('job', 'organisation').all():
        if cp.job and cp.job.project:
            cp.project = cp.job.project
        else:
            project = Project.objects.create(
                lb_job_number      = counter,
                client_name        = '',
                site_address       = '',
                merchant_reference = cp.name,
                organisation       = cp.organisation,
                created_by         = cp.created_by,
                status             = 'preliminary',
            )
            cp.project = project
            counter += 1
        cp.save(update_fields=['project'])


def reverse_populate(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cutlist', '0002_cutlistproject_add_project_field'),
    ]

    operations = [
        migrations.RunPython(populate_project, reverse_code=reverse_populate),
    ]
