"""
Add optional price_book FK to Organisation.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('products', '0003_pricebook_redesign'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='price_book',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='organisations',
                to='products.pricebook',
                help_text='Leave blank to use the default price book for all products. '
                          'Assign a specific book to override prices by exception.',
            ),
        ),
    ]
