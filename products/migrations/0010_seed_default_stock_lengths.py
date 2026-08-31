"""
Data migration: seed TimberTypeDefaultStockLengths and existing Product.stock_lengths from the
values the Cutlist Optimizer's hardcoded getDefaultStockLengths() (static/js/cutlist.js) already
used — this is the "starting point" every reviewer can subsequently edit in Django admin.
"""
from django.db import migrations

TIMBER_TYPE_DEFAULTS = {
    'LIB':   '7200,6000,4800,4200,3600,3000',
    'LVL8':  '6000',
    'LVL11': '7200,6000,5400,4800,3600',
    'LVL13': '7200,6000,5400,4800,3600',
    'GL':    '7200,6000,5400,4800,3600',
    'OTHER': '7200,6000,5400,4800,3600',
}


def classify(name):
    """Mirrors getTimberType() in static/js/cutlist.js exactly."""
    upper = name.upper()
    if 'LIB' in upper:
        return 'LIB'
    if 'LVL8' in upper:
        return 'LVL8'
    if 'LVL11' in upper:
        return 'LVL11'
    if 'LVL13' in upper:
        return 'LVL13'
    if 'GL' in upper:
        return 'GL'
    return 'OTHER'


def seed(apps, schema_editor):
    TimberTypeDefaultStockLengths = apps.get_model('products', 'TimberTypeDefaultStockLengths')
    Product = apps.get_model('products', 'Product')

    for timber_type, stock_lengths in TIMBER_TYPE_DEFAULTS.items():
        TimberTypeDefaultStockLengths.objects.get_or_create(
            timber_type=timber_type,
            defaults={'stock_lengths': stock_lengths},
        )

    for product in Product.objects.filter(stock_lengths=''):
        product.stock_lengths = TIMBER_TYPE_DEFAULTS[classify(product.name)]
        product.save(update_fields=['stock_lengths'])


def unseed(apps, schema_editor):
    TimberTypeDefaultStockLengths = apps.get_model('products', 'TimberTypeDefaultStockLengths')
    TimberTypeDefaultStockLengths.objects.all().delete()
    # Product.stock_lengths values are left in place on reverse — they're now real editable
    # data, not safe to assume still match what this migration set.


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0009_timbertypedefaultstocklengths_product_stock_lengths'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
