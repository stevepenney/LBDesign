from django.db import models
from django.conf import settings


class Job(models.Model):
    """
    A single estimate (set of sections + freight) belonging to a Project.
    One project may have multiple estimates for optioneering purposes.
    """
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='estimates',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_jobs',
    )
    source_cutlist = models.ForeignKey(
        'cutlist.CutlistProject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_jobs',
        help_text='Set when this estimate was created from a cutlist stock order.',
    )
    label = models.CharField(
        max_length=100,
        blank=True,
        default='Untitled Estimate',
        help_text="Optional label to distinguish multiple estimates on the same project, e.g. 'Option A'.",
    )

    # Per-job overrides — null means use the global SystemSettings value
    hardware_allowance_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Override hardware allowance %. Leave blank to use the global default.',
    )
    wastage_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Override wastage %. Leave blank to use the global default.',
    )
    estimate_uncertainty_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Override estimate uncertainty band %. Leave blank to use the global default.',
    )

    # Stored totals computed by the calculation engine
    hardware_allowance_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    # Calculated result for a cladding estimate (no Section layer — see is_cladding below).
    calculated_subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    member_schedule = models.JSONField(default=dict, blank=True)
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Estimate'
        verbose_name_plural = 'Estimates'

    def __str__(self):
        label_part = f' ({self.label})' if self.label else ''
        return f'{self.project.lb_ref}{label_part}'

    @property
    def is_cladding(self):
        """
        A cladding estimate has no Section layer — its areas (elevations) attach
        directly to the Job, since unlike midfloor/roof there's no per-physical-system
        setting (roof pitch, boundary joists) that would need its own container.
        """
        return self.cladding_areas.exists()

    @property
    def subtotal(self):
        if self.is_cladding:
            return self.calculated_subtotal or 0
        return sum(s.calculated_subtotal or 0 for s in self.sections.all())

    @property
    def total(self):
        total = self.subtotal
        if self.hardware_allowance_amount:
            total += self.hardware_allowance_amount
        if self.freight_charge:
            total += self.freight_charge
        if self.freight_surcharge:
            total += self.freight_surcharge
        return total


class Section(models.Model):
    """
    A discrete floor or roof framing system within an estimate (e.g. Unit 1 Midfloor,
    Unit 1 Roof). Each section has its own areas, beams, and calculated subtotal.
    """

    class SystemType(models.TextChoices):
        MIDFLOOR = 'midfloor', 'Midfloor'
        ROOF = 'roof', 'Roof'
        OTHER = 'other', 'Other'

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='sections')
    label = models.CharField(max_length=200, help_text="e.g. 'Unit 1 Midfloor'")
    system_type = models.CharField(max_length=10, choices=SystemType)

    # Boundary joists (midfloor only)
    include_boundary_joists = models.BooleanField(default=True)
    boundary_perimeter_lm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
    )
    boundary_joist_description = models.CharField(max_length=200, blank=True)
    boundary_joist_product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='boundary_joist_sections',
        limit_choices_to={'use_as_boundary_joist': True},
    )

    # Stair void trimmers (midfloor only)
    include_stair_void_trimmers = models.BooleanField(default=False)
    stair_void_trimmer_description = models.CharField(max_length=200, blank=True)
    stair_void_trimmer_product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stair_void_sections',
        limit_choices_to={'use_as_stair_void_trimmer': True},
    )

    # Roof pitch (roof only)
    roof_pitch = models.ForeignKey(
        'core.RoofPitch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sections',
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
        verbose_name = 'section'
        verbose_name_plural = 'sections'

    def __str__(self):
        return f'{self.job.project.lb_ref} / {self.label}'

    @property
    def is_midfloor(self):
        return self.system_type == self.SystemType.MIDFLOOR

    @property
    def is_roof(self):
        return self.system_type == self.SystemType.ROOF

    @property
    def is_other(self):
        return self.system_type == self.SystemType.OTHER


class FloorRoofArea(models.Model):
    """
    One or more areas within a section, each with their own joist
    type, size, and spacing. Supports different zones within a floor
    or roof (e.g. bathroom vs main floor).
    """
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='areas')
    area_label = models.CharField(max_length=200, blank=True)
    area_m2 = models.DecimalField(max_digits=10, decimal_places=2)
    product_description = models.CharField(
        max_length=200, blank=True,
        help_text='e.g. LIB240.88 I-Joist or LVL11 240x45',
    )
    joist_product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='floor_roof_areas',
        limit_choices_to={'use_as_joist_rafter': True},
    )
    # Stored in millimetres, e.g. 400, 450, 600.
    joist_spacing = models.PositiveIntegerField(
        help_text='Joist / rafter spacing in mm, e.g. 400, 450, 600.',
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        label = self.area_label or f'Area {self.pk}'
        return f'{self.section.label} / {label}'

    @property
    def spacing_m(self):
        """Spacing converted to metres for lm calculations."""
        return self.joist_spacing / 1000

    def lineal_metres(self, pitch_factor=1.0):
        return float(self.area_m2) / self.spacing_m * pitch_factor


class CladdingArea(models.Model):
    """
    One elevation/zone within a cladding estimate (e.g. North Elevation, Internal
    Stairway), each covered by a single product. Lineal metres are derived from
    area_m2 and the product's cover_mm — there is no user-entered spacing/cover,
    unlike FloorRoofArea's joist_spacing.

    Attaches directly to Job, not Section — a cladding estimate has no equivalent
    of midfloor/roof's per-physical-system settings (roof pitch, boundary joists),
    so there's nothing for a Section layer to hold; elevations are areas, not
    sections, from a data perspective.
    """
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='cladding_areas')
    area_label = models.CharField(max_length=200, blank=True)
    area_m2 = models.DecimalField(max_digits=10, decimal_places=2)
    cladding_product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cladding_areas',
        limit_choices_to={'use_as_cladding': True},
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        label = self.area_label or f'Area {self.pk}'
        return f'{self.job.project.lb_ref} / {label}'


class AdditionalBeam(models.Model):
    """
    Optional additional LVL or Glulam beams added to a section estimate.
    """
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='additional_beams')
    product_description = models.CharField(
        max_length=200, blank=True,
        help_text='e.g. LVL11 360x63 or Glulam 315x90',
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='additional_beam_lines',
        limit_choices_to={'use_as_beam': True},
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


class CutlistImportLine(models.Model):
    """
    A priced member line created by converting a cutlist stock order into an
    estimate. length_m is the net lineal metres required for the member —
    wastage is applied via the section's job-level wastage_pct, not baked in here.
    """
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='cutlist_import_lines')
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cutlist_import_lines',
    )
    product_description = models.CharField(
        max_length=200, blank=True,
        help_text='Raw member name from the cutlist, kept as a placeholder label when no product was matched.',
    )
    length_m = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    tab_index = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Index into the source cutlist state.tabs[] this line was mapped from — used to join back to the per-stick stock order for display.',
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        label = self.product or self.product_description or 'Unmatched member'
        return f'{label} x{self.quantity} @ {self.length_m}m'

    @property
    def lineal_metres(self):
        return float(self.length_m) * self.quantity


class DrawingUpload(models.Model):
    """
    Files uploaded against an estimate by a merchant user.
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
        return f'{self.original_filename} ({self.job.project.lb_ref})'
