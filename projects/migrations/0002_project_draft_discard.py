from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='client_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='project',
            name='site_address',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft',       'Draft'),
                    ('preliminary', 'Preliminary'),
                    ('quoting',     'Quoting'),
                    ('quoted',      'Quoted'),
                    ('ordered',     'Ordered'),
                    ('supplied',    'Supplied'),
                    ('on_hold',     'On Hold'),
                    ('cancelled',   'Cancelled'),
                    ('discarded',   'Discarded'),
                ],
                default='draft',
                max_length=20,
            ),
        ),
    ]
