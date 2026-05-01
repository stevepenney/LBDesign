"""
Redesign PriceBook from org-specific to named/default with fallback.

Before: PriceBook had a OneToOneField to Organisation.
After:  PriceBook is standalone with name + is_default flag.
        Organisation will gain a FK to PriceBook in accounts 0002.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_remove_product_use_add_use_flags'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Remove the old org-tied relationship
        migrations.RemoveField(
            model_name='pricebook',
            name='organisation',
        ),
        # Add identifying fields
        migrations.AddField(
            model_name='pricebook',
            name='name',
            field=models.CharField(default='Unnamed', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='pricebook',
            name='is_default',
            field=models.BooleanField(
                default=False,
                help_text='There should only be one default price book. '
                          'Setting this will unset any existing default.',
            ),
        ),
        migrations.AddField(
            model_name='pricebook',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='pricebook',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterModelOptions(
            name='pricebook',
            options={'ordering': ['-is_default', 'name']},
        ),
    ]
