from django.db import migrations


def backfill_visible_to_merchant(apps, schema_editor):
    """Existing cutlists a merchant created themselves should stay visible to them —
    only ones LB staff created should newly default to hidden."""
    CutlistProject = apps.get_model('cutlist', 'CutlistProject')
    CutlistProject.objects.filter(created_by__role='merchant_user').update(visible_to_merchant=True)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cutlist', '0006_cutlistproject_visible_to_merchant'),
    ]

    operations = [
        migrations.RunPython(backfill_visible_to_merchant, noop),
    ]
