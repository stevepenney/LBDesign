from django.conf import settings
from django.db import models


class RoofPitch(models.Model):
    """
    Supported roof pitches.  Store the angle in degrees; the pitch factor
    (1 / cos θ) used to convert plan area to rafter lm is derived automatically.
    Maintained by Lumberbank Admin.
    """
    label = models.CharField(max_length=50, help_text="Display label, e.g. '15°'")
    pitch_degrees = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Roof pitch angle in degrees, e.g. 15, 22.5, 30.',
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'pitch_degrees']

    def __str__(self):
        return self.label

    @property
    def pitch_factor(self):
        """1 / cos(pitch_degrees) — multiplies plan-area lm to get rafter lm."""
        import math
        return 1 / math.cos(math.radians(float(self.pitch_degrees)))


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


class StairVoidSettings(models.Model):
    """
    System-wide stair void trimmer allowance, managed by Lumberbank Admin.
    Singleton — always use StairVoidSettings.get(), never .objects.first().
    """
    allowance_lm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        help_text='Standard lineal metre allowance applied when the stair void trimmer toggle is on.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stair Void Settings'
        verbose_name_plural = 'Stair Void Settings'

    def __str__(self):
        return f'Stair Void Settings ({self.allowance_lm} lm)'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Feedback(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='feedback_submissions',
    )
    page_url = models.URLField(max_length=500)
    page_title = models.CharField(max_length=255, blank=True)
    comments = models.TextField()
    screenshot = models.ImageField(upload_to='feedback/', null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'
        ordering = ['-submitted_at']

    def __str__(self):
        return f'Feedback from {self.user} on {self.submitted_at:%Y-%m-%d %H:%M}'
