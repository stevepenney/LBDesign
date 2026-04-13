from django.db import models
from django.conf import settings


class Job(models.Model):
    """
    Top-level record representing a construction project.
    Belongs to a single merchant Organisation.
    """

    class Status(models.TextChoices):
        ESTIMATE = 'estimate', 'Estimate'
        DRAWING_UPLOADED = 'drawing_uploaded', 'Drawing Uploaded'
        ORDER_PLACED = 'order_placed', 'Order Placed'

    organisation = models.ForeignKey(
        'accounts.Organisation',
        on_delete=models.PROTECT,
        related_name='jobs',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_jobs',
    )
    job_reference = models.CharField(max_length=200)
    client_name = models.CharField(max_length=200)
    site_address = models.TextField()
    status = models.CharField(max_length=30, choices=Status, default=Status.ESTIMATE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Freight applied at job level (stored after calculation)
    freight_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    freight_surcharge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.job_reference} — {self.client_name}'

    @property
    def subtotal(self):
        return sum(sj.calculated_subtotal or 0 for sj in self.sub_jobs.all())

    @property
    def total(self):
        total = self.subtotal
        if self.freight_charge:
            total += self.freight_charge
        if self.freight_surcharge:
            total += self.freight_surcharge
        return total


class SubJob(models.Model):
    """
    A discrete floor or roof system within a Job, with its own
    estimate inputs and calculated sub-total.
    """

    class SystemType(models.TextChoices):
        MIDFLOOR = 'midfloor', 'Midfloor'
        ROOF = 'roof', 'Roof'

    class JoistSpacing(models.TextChoices):
        S400 = '0.400', '400 c/c'
        S450 = '0.450', '450 c/c'
        S600 = '0.600', '600 c/c'

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='sub_jobs')
    label = models.CharField(max_length=200, help_text="e.g. 'Unit 1 Midfloor'")
    system_type = models.CharField(max_length=10, choices=SystemType)

    # Boundary joists (midfloor only)
    include_boundary_joists = models.BooleanField(default=True)
    boundary_perimeter_lm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
    )
    boundary_joist_product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='boundary_joist_sub_jobs',
        limit_choices_to={'product_use': 'boundary_joist'},
    )

    # Stair void trimmers (midfloor only)
    include_stair_void_trimmers = models.BooleanField(default=False)
    stair_void_trimmer_product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stair_void_sub_jobs',
        limit_choices_to={'product_use': 'stair_void_trimmer'},
    )

    # Roof pitch (roof only)
    roof_pitch = models.ForeignKey(
        'RoofPitch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_jobs',
    )

    # Calculated result (stored after engine runs)
    calculated_subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )

    # Background member schedule stored as JSON for internal use
    member_schedule = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.job.job_reference} / {self.label}'

    @property
    def is_midfloor(self):
        return self.system_type == self.SystemType.MIDFLOOR

    @property
    def is_roof(self):
        return self.system_type == self.SystemType.ROOF


class FloorRoofArea(models.Model):
    """
    One or more areas within a sub-job, each with their own joist
    type, size, and spacing. Supports different zones within a floor
    or roof (e.g. bathroom vs main floor).
    """

    class JoistSpacing(models.TextChoices):
        S400 = '0.400', '400 c/c'
        S450 = '0.450', '450 c/c'
        S600 = '0.600', '600 c/c'

    sub_job = models.ForeignKey(SubJob, on_delete=models.CASCADE, related_name='areas')
    area_label = models.CharField(max_length=200, blank=True)
    area_m2 = models.DecimalField(max_digits=10, decimal_places=2)
    joist_product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='floor_roof_areas',
        limit_choices_to={'product_use': 'joist_rafter'},
    )
    joist_spacing = models.CharField(max_length=5, choices=JoistSpacing)

    class Meta:
        ordering = ['id']

    def __str__(self):
        label = self.area_label or f'Area {self.pk}'
        return f'{self.sub_job.label} / {label}'

    @property
    def spacing_m(self):
        return float(self.joist_spacing)

    def lineal_metres(self, pitch_factor=1.0):
        return float(self.area_m2) / self.spacing_m * pitch_factor


class AdditionalBeam(models.Model):
    """
    Optional additional LVL or Glulam beams added to a sub-job estimate.
    """
    sub_job = models.ForeignKey(SubJob, on_delete=models.CASCADE, related_name='additional_beams')
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='additional_beam_lines',
        limit_choices_to={'product_use': 'beam'},
    )
    length_m = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.product.name} x{self.quantity} @ {self.length_m}m'

    @property
    def lineal_metres(self):
        return float(self.length_m) * self.quantity


class RoofPitch(models.Model):
    """
    Lookup table of supported roof pitches and their pitch factors.
    Maintained by Lumberbank Admin.
    """
    label = models.CharField(max_length=50, help_text="e.g. '15°' or '1:4'")
    pitch_factor = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        help_text='Multiply plan area by this factor to get rafter lineal metres.',
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'label']

    def __str__(self):
        return self.label


class DrawingUpload(models.Model):
    """
    Files uploaded against a job by a merchant user.
    Upload triggers an email notification to the Lumberbank detailing team.
    """
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='drawing_uploads')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    file = models.FileField(upload_to='drawings/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.original_filename} ({self.job.job_reference})'
