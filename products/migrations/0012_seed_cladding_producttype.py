# Seed the 'Cladding' ProductType for the Cladding Estimator — same pattern as
# 0006_producttype_populate.py. Actual Product rows are added via admin, not seeded here.
from django.db import migrations


def forward(apps, schema_editor):
    ProductType = apps.get_model('products', 'ProductType')
    ProductType.objects.get_or_create(
        name='Cladding',
        defaults={'sort_order': 10},
    )


def reverse(apps, schema_editor):
    ProductType = apps.get_model('products', 'ProductType')
    ProductType.objects.filter(name='Cladding', products__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0011_product_cover_mm_product_use_as_cladding'),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
