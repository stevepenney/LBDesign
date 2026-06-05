from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lb_job_number', models.PositiveIntegerField(editable=False, unique=True)),
                ('merchant_reference', models.CharField(blank=True, max_length=200)),
                ('client_name', models.CharField(max_length=200)),
                ('site_address', models.TextField()),
                ('status', models.CharField(
                    choices=[
                        ('preliminary', 'Preliminary'),
                        ('quoting',     'Quoting'),
                        ('quoted',      'Quoted'),
                        ('ordered',     'Ordered'),
                        ('supplied',    'Supplied'),
                        ('on_hold',     'On Hold'),
                        ('cancelled',   'Cancelled'),
                    ],
                    default='preliminary',
                    max_length=20,
                )),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organisation', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='projects',
                    to='accounts.organisation',
                )),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_projects',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-lb_job_number'],
            },
        ),
    ]
