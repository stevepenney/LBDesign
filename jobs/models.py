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

    # Per-job overrides — null means use the global SystemSettings value. Also the default a new
    # Part/Section starts from for wastage_pct/hardware_allowance_pct — see Section below, which
    # is where these are actually applied now (a job's total is just its parts summed).
    hardware_allowance_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Default hardware allowance % for new Parts. Leave blank to use the global '
                   'default. Each Part can override this individually.',
    )
    wastage_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Default wastage % for new Parts. Leave blank to use the global default. '
                   'Each Part can override this individually.',
    )
    estimate_uncertainty_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Override estimate uncertainty band %. Leave blank to use the global default.',
    )
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
    def subtotal(self):
        """Materials only, summed across every Part — hardware is tracked separately below."""
        return sum(s.calculated_subtotal or 0 for s in self.sections.all())

    @property
    def hardware_allowance_amount(self):
        """Sum of every Part's own hardware allowance $ — each Part can carry a different rate."""
        return sum(s.hardware_allowance_amount or 0 for s in self.sections.all())

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
    A discrete system within an estimate (e.g. Unit 1 Midfloor, Unit 1 Roof, or a
    Cladding part) — user-facing term is "Part" (see CLAUDE.md), same as this model
    itself is user-facing "Section" internally vs. the old "sub-job" term. Each part
    has its own areas/items, wastage/hardware factors, and calculated subtotal.

    CLADDING is a part type like any other — it has no boundary-joist/stair-void
    settings (nothing for those fields to apply to) but is otherwise a peer of
    MIDFLOOR/ROOF/OTHER, priced and factored independently. This is what lets one
    job hold both framing and cladding parts (or several cladding parts) together.
    """

    class SystemType(models.TextChoices):
        MIDFLOOR = 'midfloor', 'Midfloor'
        ROOF = 'roof', 'Roof'
        OTHER = 'other', 'Other'
        CLADDING = 'cladding', 'Cladding'

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='sections')
    label = models.CharField(max_length=200, help_text="e.g. 'Unit 1 Midfloor'")
    system_type = models.CharField(max_length=10, choices=SystemType)

    # Per-part overrides — null means use the job's default, which itself falls back to the
    # global SystemSettings value (three-tier: SystemSettings -> Job -> Section).
    wastage_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Override wastage % for this part. Leave blank to use the job default.',
    )
    hardware_allowance_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Override hardware allowance % for this part. Leave blank to use the job default.',
    )
    stock_contingency_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Override cutlist stock contingency % for this part (cladding only). Leave '
                   'blank to use the global default.',
    )

    # Cutlist generated from this part's own vertical cladding elevations, if any.
    cladding_cutlist = models.ForeignKey(
        'cutlist.CutlistProject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cladding_source_sections',
        help_text='Cutlist generated from this part\'s own vertical elevations, if any.',
    )

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

    # Calculated result (stored after engine runs) — materials only, hardware tracked separately.
    calculated_subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    hardware_allowance_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )

    # Background member schedule stored as JSON for internal use
    member_schedule = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'part'
        verbose_name_plural = 'parts'

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

    @property
    def is_cladding(self):
        return self.system_type == self.SystemType.CLADDING


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
    # Roof pitch (roof sections only) — per-area, not per-section, so one roof section
    # (e.g. "Unit 1 Roof") can span multiple pitches (main roof vs porch, hips, etc.).
    roof_pitch = models.ForeignKey(
        'core.RoofPitch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='areas',
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
    One elevation/zone within a cladding part (e.g. North Elevation, Internal
    Stairway), each covered by a single product. Lineal metres are derived from
    area_m2 (= width_m * height_m) and the product's cover_mm — there is no
    user-entered spacing/cover, unlike FloorRoofArea's joist_spacing.

    Attaches to a Section whose system_type is CLADDING — cladding is a part type
    like Midfloor/Roof/Other, just one with no boundary-joist/stair-void settings
    to hold (those fields are simply unused on a cladding Section).

    orientation matters beyond display: vertical-run boards can't have joins (a
    board must span the full height in one piece), so a vertical elevation can be
    broken down into discrete cut pieces (see cut_piece()) and fed to the cutlist
    optimizer. Horizontal runs tolerate joins, so a course has no single fixed
    piece length — it stays on the area-based lm estimate below instead of ever
    producing discrete pieces.
    """
    class Orientation(models.TextChoices):
        VERTICAL = 'vertical', 'Vertical'
        HORIZONTAL = 'horizontal', 'Horizontal'

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='cladding_areas')
    area_label = models.CharField(max_length=200, blank=True)
    orientation = models.CharField(
        max_length=10, choices=Orientation.choices, default=Orientation.VERTICAL,
    )
    width_m = models.DecimalField(max_digits=8, decimal_places=2)
    height_m = models.DecimalField(max_digits=8, decimal_places=2)
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
        return f'{self.section.job.project.lb_ref} / {label}'

    @property
    def area_m2(self):
        return self.width_m * self.height_m

    def cut_piece(self):
        """
        Vertical boards only — (length_mm, qty) for the discrete boards this
        elevation needs, or None if it can't be priced/cut yet. A horizontal
        course tolerates joins, so it has no single fixed piece length; it stays
        on the area-based lm estimate in jobs.calculations instead.
        """
        if self.orientation != self.Orientation.VERTICAL:
            return None
        if not self.cladding_product or not self.cladding_product.cover_mm:
            return None
        height_mm = int(self.height_m * 1000)
        width_mm = int(self.width_m * 1000)
        qty = -(-width_mm // self.cladding_product.cover_mm)  # ceil division
        return height_mm, qty


class CladdingExtraItem(models.Model):
    """
    Extra cladding-related products that don't come from an elevation's area —
    scribers, corner mouldings, flashings, etc. Mirrors AdditionalBeam's shape
    (product + length + quantity) for the same reason AdditionalBeam exists for
    framing: a flat, freely-added line that isn't derived from anything else.
    Attaches to a cladding-type Section, same as CladdingArea.
    """
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='cladding_extra_items')
    product_description = models.CharField(
        max_length=200, blank=True,
        help_text='e.g. Vertica Scriber 40x19 or Corner Mould',
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cladding_extra_items',
    )
    length_m = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['id']

    def __str__(self):
        label = self.product or self.product_description or 'Extra item'
        return f'{label} x{self.quantity} @ {self.length_m}m'

    @property
    def lineal_metres(self):
        return float(self.length_m) * self.quantity


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
    wastage is applied via the section's own effective wastage_pct, not baked in here.
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


class CladdingCutlistLine(models.Model):
    """
    A priced product line created by importing a cladding part's generated cutlist
    results — mirrors CutlistImportLine (same shape, both now Section-scoped).
    length_m is the real optimized gross stock length required for the product,
    with the part's stock contingency % already applied — see
    jobs.calculations._calc_cladding.
    """
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='cladding_cutlist_lines')
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cladding_cutlist_lines',
    )
    product_description = models.CharField(
        max_length=200, blank=True,
        help_text='Raw member name from the cutlist, kept as a placeholder label when no product was matched.',
    )
    length_m = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

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
