from django.db import models


class FreightSettings(models.Model):
    """
    System-wide freight configuration managed by Lumberbank Admin.
    Only one active record is used (singleton pattern enforced in admin).
    """
    freight_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1000.00,
        help_text='Job total below this value attracts the fixed freight fee.',
    )
    fixed_freight_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text='Fixed fee applied to orders below the freight threshold.',
    )
    surcharge_enabled = models.BooleanField(
        default=False,
        help_text='System-wide toggle for the fuel surcharge.',
    )
    surcharge_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text='Percentage surcharge applied to qualifying order totals when enabled.',
    )
    stair_void_trimmer_allowance_lm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        help_text='Standard lineal metre allowance applied when the stair void trimmer toggle is on.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Freight Settings'
        verbose_name_plural = 'Freight Settings'

    def __str__(self):
        return f'Freight Settings (threshold: ${self.freight_threshold})'

    def save(self, *args, **kwargs):
        # Enforce singleton — always use pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
