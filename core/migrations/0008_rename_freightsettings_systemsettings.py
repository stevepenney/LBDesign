from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_freightsettings_wastage_pct'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='FreightSettings',
            new_name='SystemSettings',
        ),
    ]
