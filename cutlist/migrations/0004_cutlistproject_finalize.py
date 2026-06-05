from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Make project FK non-nullable; remove old organisation and job FKs."""

    dependencies = [
        ('cutlist', '0003_cutlistproject_populate_project'),
        ('jobs', '0010_job_finalize_project'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cutlistproject',
            name='project',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cutlist_projects',
                to='projects.project',
            ),
        ),
        migrations.RemoveField(model_name='cutlistproject', name='organisation'),
        migrations.RemoveField(model_name='cutlistproject', name='job'),
    ]
