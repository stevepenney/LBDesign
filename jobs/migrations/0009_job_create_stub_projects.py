from django.db import migrations


def create_stub_projects(apps, schema_editor):
    """Create one Project per existing Job, preserving client/address/reference data."""
    Job     = apps.get_model('jobs',     'Job')
    Project = apps.get_model('projects', 'Project')

    counter = 1
    for job in Job.objects.select_related('organisation').order_by('created_at'):
        project = Project.objects.create(
            lb_job_number      = counter,
            client_name        = job.client_name or '',
            site_address       = job.site_address or '',
            merchant_reference = job.job_reference or '',
            organisation       = job.organisation,
            created_by         = job.created_by,
            status             = 'preliminary',
        )
        job.project = project
        job.save(update_fields=['project'])
        counter += 1


def reverse_stub_projects(apps, schema_editor):
    Job     = apps.get_model('jobs',     'Job')
    Project = apps.get_model('projects', 'Project')
    for job in Job.objects.select_related('project').all():
        if job.project:
            job.job_reference = job.project.merchant_reference
            job.client_name   = job.project.client_name
            job.site_address  = job.project.site_address
            job.organisation  = job.project.organisation
            job.save(update_fields=['job_reference', 'client_name', 'site_address', 'organisation'])
    Project.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0008_job_add_project_field'),
    ]

    operations = [
        migrations.RunPython(create_stub_projects, reverse_code=reverse_stub_projects),
    ]
