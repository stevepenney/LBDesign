from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_project_draft_discard'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(
                    choices=[
                        ('drawing', 'Drawing'),
                        ('design',  'Design File'),
                        ('quote',   'Quote'),
                        ('other',   'Other'),
                    ],
                    default='drawing',
                    max_length=20,
                )),
                ('name',         models.CharField(blank=True, max_length=200)),
                ('file',         models.FileField(blank=True, upload_to='project_docs/%Y/%m/')),
                ('external_url', models.URLField(blank=True, max_length=500, verbose_name='Cloud storage link')),
                ('notes',        models.TextField(blank=True)),
                ('uploaded_at',  models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='documents',
                    to='projects.project',
                )),
                ('uploaded_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
