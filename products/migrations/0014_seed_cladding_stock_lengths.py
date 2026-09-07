# Seed the CLADDING row in TimberTypeDefaultStockLengths — same generic starting list as
# LVL11/LVL13/GL/OTHER (0010_seed_default_stock_lengths.py). Real cladding products should
# have their own Product.stock_lengths set, which take precedence over this fallback anyway
# (same behaviour as every other timber type).
from django.db import migrations

GENERIC_DEFAULT = '7200,6000,5400,4800,3600'


def forward(apps, schema_editor):
    TimberTypeDefaultStockLengths = apps.get_model('products', 'TimberTypeDefaultStockLengths')
    TimberTypeDefaultStockLengths.objects.get_or_create(
        timber_type='CLADDING',
        defaults={'stock_lengths': GENERIC_DEFAULT},
    )


def reverse(apps, schema_editor):
    TimberTypeDefaultStockLengths = apps.get_model('products', 'TimberTypeDefaultStockLengths')
    TimberTypeDefaultStockLengths.objects.filter(timber_type='CLADDING').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0013_alter_timbertypedefaultstocklengths_timber_type'),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
