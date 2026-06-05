from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_alter_pricebook_created_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
            ],
            options={
                'ordering': ['sort_order', 'name'],
            },
        ),
        # Preserve the old char values under a legacy name for the data migration.
        migrations.RenameField(
            model_name='product',
            old_name='product_type',
            new_name='product_type_legacy',
        ),
        migrations.AddField(
            model_name='product',
            name='product_type',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='products',
                to='products.producttype',
            ),
        ),
    ]
