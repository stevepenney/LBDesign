from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Add project FK and label to Job; keep old fields until data is migrated."""

    dependencies = [
        ('jobs', '0007_alter_section_options_and_more'),
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='project',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='estimates',
                to='projects.project',
            ),
        ),
        migrations.AddField(
            model_name='job',
            name='label',
            field=models.CharField(
                blank=True,
                max_length=100,
                help_text="Optional label to distinguish multiple estimates on the same project, e.g. 'Option A'.",
            ),
        ),
    ]
