from django.db import migrations


def backfill_visible_to_merchant(apps, schema_editor):
    """Existing estimates a merchant created themselves should stay visible to them —
    only ones LB staff created should newly default to hidden."""
    Job = apps.get_model('jobs', 'Job')
    Job.objects.filter(created_by__role='merchant_user').update(visible_to_merchant=True)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0029_job_visible_to_merchant'),
    ]

    operations = [
        migrations.RunPython(backfill_visible_to_merchant, noop),
    ]
