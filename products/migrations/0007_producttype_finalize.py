from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0006_producttype_populate'),
    ]

    operations = [
        # Make the FK non-nullable now that every row has been populated.
        migrations.AlterField(
            model_name='product',
            name='product_type',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='products',
                to='products.producttype',
            ),
        ),
        migrations.RemoveField(
            model_name='product',
            name='product_type_legacy',
        ),
    ]
