from django.db import models
from django.conf import settings


class ProductType(models.TextChoices):
    I_JOIST = 'i_joist', 'I-Joist'
    LVL = 'lvl', 'LVL'
    GLULAM = 'glulam', 'Glulam'


class ProductUse(models.TextChoices):
    JOIST_RAFTER = 'joist_rafter', 'Joist / Rafter'
    BOUNDARY_JOIST = 'boundary_joist', 'Boundary Joist'
    STAIR_VOID_TRIMMER = 'stair_void_trimmer', 'Stair Void Trimmer'
    BEAM = 'beam', 'Beam'


class Product(models.Model):
    """
    A single timber product (e.g. LIB240.88 I-Joist, LVL8 90x45).
    The product list is maintained by Lumberbank Admin and shared across
    all price books.
    """
    name = models.CharField(max_length=100)
    product_type = models.CharField(max_length=20, choices=ProductType)
    product_use = models.CharField(max_length=30, choices=ProductUse)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['product_type', 'sort_order', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_product_type_display()})'


class PriceBook(models.Model):
    """
    A set of wholesale unit prices (per lineal metre) for a specific
    merchant organisation. Managed by Lumberbank Admin only.
    """
    organisation = models.OneToOneField(
        'accounts.Organisation',
        on_delete=models.CASCADE,
        related_name='price_book',
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f'Price Book — {self.organisation.name}'


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
