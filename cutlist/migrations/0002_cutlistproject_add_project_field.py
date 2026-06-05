from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cutlist', '0001_initial'),
        ('projects', '0001_initial'),
        ('jobs', '0009_job_create_stub_projects'),
    ]

    operations = [
        migrations.AddField(
            model_name='cutlistproject',
            name='project',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cutlist_projects',
                to='projects.project',
            ),
        ),
    ]
