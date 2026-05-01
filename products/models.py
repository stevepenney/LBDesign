from django.db import models
from django.conf import settings


class ProductType(models.TextChoices):
    I_JOIST = 'i_joist', 'I-Joist'
    LVL = 'lvl', 'LVL'
    GLULAM = 'glulam', 'Glulam'


class Product(models.Model):
    """
    A single timber product (e.g. LIB240.88 I-Joist, LVL8 90x45).
    The product list is maintained by Lumberbank Admin and shared across
    all price books. A product may be suitable for multiple uses —
    e.g. a 240x45 LVL11 can serve as a joist, beam, or boundary joist.
    """
    name = models.CharField(max_length=100)
    product_type = models.CharField(max_length=20, choices=ProductType)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    # A product may be used in multiple roles — tick all that apply.
    use_as_joist_rafter       = models.BooleanField(default=False, verbose_name='Joist / Rafter')
    use_as_boundary_joist     = models.BooleanField(default=False, verbose_name='Boundary Joist')
    use_as_stair_void_trimmer = models.BooleanField(default=False, verbose_name='Stair Void Trimmer')
    use_as_beam               = models.BooleanField(default=False, verbose_name='Beam')

    class Meta:
        ordering = ['product_type', 'sort_order', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_product_type_display()})'


class PriceBook(models.Model):
    """
    A named set of wholesale unit prices (per lineal metre).

    One price book should be flagged as the default.  An Organisation may
    be assigned a specific price book; entries in that book override the
    default.  Any product not in the org's book falls back to the default
    price book automatically — price books are therefore set up "by exception".
    """
    name = models.CharField(max_length=200)
    is_default = models.BooleanField(
        default=False,
        help_text='There should only be one default price book. '
                  'Setting this will unset any existing default.',
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['-is_default', 'name']

    def __str__(self):
        return f'{self.name}{"  [default]" if self.is_default else ""}'

    def save(self, *args, **kwargs):
        if self.is_default:
            # Enforce single default — clear any other before saving.
            PriceBook.objects.exclude(pk=self.pk).filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_default(cls):
        return cls.objects.filter(is_default=True).first()


class PriceBookEntry(models.Model):
    """
    The per-lineal-metre wholesale price for a single product within
    a merchant's price book.
    """
    price_book = models.ForeignKey(
        PriceBook,
        on_delete=models.CASCADE,
        related_name='entries',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='price_book_entries',
    )
    price_per_lm = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text='Wholesale price per lineal metre, ex GST.',
    )

    class Meta:
        unique_together = ('price_book', 'product')
        ordering = ['product__product_type', 'product__name']

    def __str__(self):
        return f'{self.product.name} @ ${self.price_per_lm}/lm'
