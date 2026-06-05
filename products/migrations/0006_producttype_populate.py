from django.db import migrations

# Maps old char values → (display name, sort_order)
LEGACY_MAP = {
    'i_joist': ('I-Joist', 1),
    'lvl':     ('LVL',     2),
    'glulam':  ('Glulam',  3),
}


def forward(apps, schema_editor):
    ProductType = apps.get_model('products', 'ProductType')
    Product = apps.get_model('products', 'Product')

    type_objects = {}
    for legacy_value, (display_name, sort_order) in LEGACY_MAP.items():
        pt, _ = ProductType.objects.get_or_create(
            name=display_name,
            defaults={'sort_order': sort_order},
        )
        type_objects[legacy_value] = pt

    for product in Product.objects.all():
        pt = type_objects.get(product.product_type_legacy)
        if pt:
            product.product_type = pt
            product.save(update_fields=['product_type'])


def reverse(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    name_to_legacy = {v[0]: k for k, v in LEGACY_MAP.items()}

    for product in Product.objects.select_related('product_type').all():
        if product.product_type:
            legacy = name_to_legacy.get(product.product_type.name)
            if legacy:
                product.product_type_legacy = legacy
                product.save(update_fields=['product_type_legacy'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0005_producttype_create'),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=reverse),
    ]
