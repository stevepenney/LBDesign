from django.db import migrations, models


def copy_stair_void_allowance(apps, schema_editor):
    StairVoidSettings = apps.get_model('core', 'StairVoidSettings')
    SystemSettings = apps.get_model('core', 'SystemSettings')
    try:
        sv = StairVoidSettings.objects.get(pk=1)
        ss, _ = SystemSettings.objects.get_or_create(pk=1)
        ss.stair_void_allowance_lm = sv.allowance_lm
        ss.save(update_fields=['stair_void_allowance_lm'])
    except StairVoidSettings.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_rename_freightsettings_systemsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='stair_void_allowance_lm',
            field=models.DecimalField(
                max_digits=8,
                decimal_places=2,
                default=0.00,
                help_text='Standard lineal metre allowance applied when the stair void trimmer toggle is on.',
            ),
        ),
        migrations.RunPython(copy_stair_void_allowance, migrations.RunPython.noop),
        migrations.DeleteModel(name='StairVoidSettings'),
    ]
