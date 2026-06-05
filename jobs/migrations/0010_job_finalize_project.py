from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Make project FK non-nullable; drop old fields that moved to Project."""

    dependencies = [
        ('jobs', '0009_job_create_stub_projects'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='project',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='estimates',
                to='projects.project',
            ),
        ),
        migrations.RemoveField(model_name='job', name='organisation'),
        migrations.RemoveField(model_name='job', name='job_reference'),
        migrations.RemoveField(model_name='job', name='client_name'),
        migrations.RemoveField(model_name='job', name='site_address'),
        migrations.RemoveField(model_name='job', name='status'),
    ]
