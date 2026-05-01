"""
Rename SubJob model to Section throughout.
  - jobs_subjob table → jobs_section
  - floorroofarea.sub_job_id column → section_id
  - additionalbeam.sub_job_id column → section_id
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0005_move_roofpitch_to_core'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='SubJob',
            new_name='Section',
        ),
        migrations.RenameField(
            model_name='floorroofarea',
            old_name='sub_job',
            new_name='section',
        ),
        migrations.RenameField(
            model_name='additionalbeam',
            old_name='sub_job',
            new_name='section',
        ),
    ]
