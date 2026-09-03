"""
Estimation calculation engine.

Entry points
------------
run_subjob_calculation(sub_job)
    Calculate one framing sub-job (Section) and persist results.  Call this
    immediately after saving a sub-job and its area / beam formsets.

run_cladding_calculation(job)
    Calculate a cladding job's areas and persist results directly onto the Job
    (cladding has no Section layer — see Job.is_cladding).  Call this
    immediately after saving a job's cladding area formset.

run_job_estimate(job)
    Recalculate a whole job — every framing sub-job, or the cladding areas —
    then refresh freight.  Returns the job total as a Decimal.

calc_freight(subtotal, freight_settings)
    Pure function — returns (freight_charge, surcharge).
"""

from decimal import Decimal

from core.models import SystemSettings
from products.pricing import get_product_price
from .models import Job, Section


_CENT = Decimal('0.01')


def _d(value):
    """Cast any numeric value to Decimal without float rounding."""
    return Decimal(str(value))


def _area_lm(area_m2, dimension_mm, wastage_factor, pitch_factor=Decimal('1')):
    """
    Shared area → lineal-metres conversion: area / (dimension in m) * pitch * wastage.
    Used for both joist/rafter spacing (FloorRoofArea) and cladding cover (CladdingArea) —
    same formula, different source for the mm dimension (a per-area design choice for
    spacing, vs a fixed product property for cladding cover).
    """
    dimension_m = _d(dimension_mm) / Decimal('1000')
    return (_d(area_m2) / dimension_m * pitch_factor * wastage_factor).quantize(_CENT)


# ── Core calculation ──────────────────────────────────────────────────────────

def _calc_subjob(sub_job):
    """
    Returns (subtotal, schedule, has_unpriced).

    subtotal     — Decimal sum of all priced line items.
    schedule     — list of dicts, one per line item.
    has_unpriced — True if any line item has no price in the active book.

    Line item dict keys:
        label, description, lineal_metres, unit_price, line_total
        (unit_price and line_total are None when not priced)
    """
    organisation = sub_job.job.project.organisation
    schedule = []
    subtotal = Decimal('0')
    has_unpriced = False

    freight_settings = SystemSettings.get()
    effective_wastage = sub_job.job.wastage_pct if sub_job.job.wastage_pct is not None else freight_settings.wastage_pct
    wastage_factor = Decimal('1') + _d(effective_wastage) / Decimal('100')

    pitch_factor = Decimal('1')
    if sub_job.is_roof and sub_job.roof_pitch:
        pitch_factor = _d(sub_job.roof_pitch.pitch_factor)

    # ── Areas (joists / rafters) ──────────────────────────────────────────
    for area in sub_job.areas.select_related('joist_product').all():
        if not area.joist_product:
            has_unpriced = True
            continue
        lm = _area_lm(area.area_m2, area.joist_spacing, wastage_factor, pitch_factor)
        price = get_product_price(area.joist_product, organisation)
        line_total = (lm * price).quantize(_CENT) if price else None
        if line_total:
            subtotal += line_total
        else:
            has_unpriced = True
        schedule.append({
            'label': area.area_label or 'Joists / Rafters',
            'description': str(area.joist_product),
            'lineal_metres': str(lm),
            'unit_price': str(price) if price else None,
            'line_total': str(line_total) if line_total else None,
        })

    # ── Boundary joists (midfloor only) ──────────────────────────────────
    if (sub_job.is_midfloor
            and sub_job.include_boundary_joists
            and sub_job.boundary_joist_product
            and sub_job.boundary_perimeter_lm):
        lm = (_d(sub_job.boundary_perimeter_lm) * _d('1.5') * wastage_factor).quantize(_CENT)
        price = get_product_price(sub_job.boundary_joist_product, organisation)
        line_total = (lm * price).quantize(_CENT) if price else None
        if line_total:
            subtotal += line_total
        else:
            has_unpriced = True
        schedule.append({
            'label': 'Boundary joists',
            'description': str(sub_job.boundary_joist_product),
            'lineal_metres': str(lm),
            'unit_price': str(price) if price else None,
            'line_total': str(line_total) if line_total else None,
        })

    # ── Stair void trimmers (midfloor only) ──────────────────────────────
    if (sub_job.is_midfloor
            and sub_job.include_stair_void_trimmers
            and sub_job.stair_void_trimmer_product):
        lm = (_d(freight_settings.stair_void_allowance_lm) * wastage_factor).quantize(_CENT)
        price = get_product_price(sub_job.stair_void_trimmer_product, organisation)
        line_total = (lm * price).quantize(_CENT) if price else None
        if line_total:
            subtotal += line_total
        else:
            has_unpriced = True
        schedule.append({
            'label': 'Stair void trimmers',
            'description': str(sub_job.stair_void_trimmer_product),
            'lineal_metres': str(lm),
            'unit_price': str(price) if price else None,
            'line_total': str(line_total) if line_total else None,
        })

    # ── Additional beams ──────────────────────────────────────────────────
    for beam in sub_job.additional_beams.select_related('product').all():
        if not beam.product:
            has_unpriced = True
            continue
        lm = (_d(beam.length_m) * _d(beam.quantity) * wastage_factor).quantize(_CENT)
        price = get_product_price(beam.product, organisation)
        line_total = (lm * price).quantize(_CENT) if price else None
        if line_total:
            subtotal += line_total
        else:
            has_unpriced = True
        schedule.append({
            'label': f'Beam ×{beam.quantity}',
            'description': str(beam.product),
            'lineal_metres': str(lm),
            'unit_price': str(price) if price else None,
            'line_total': str(line_total) if line_total else None,
        })

    # ── Cutlist import lines ────────────────────────────────────────────────
    for line in sub_job.cutlist_import_lines.select_related('product').all():
        lm = (_d(line.length_m) * _d(line.quantity) * wastage_factor).quantize(_CENT)
        if not line.product:
            has_unpriced = True
            schedule.append({
                'label': 'Cutlist output',
                'description': line.product_description or 'Unmatched cutlist member',
                'lineal_metres': str(lm),
                'unit_price': None,
                'line_total': '0.00',
            })
            continue
        price = get_product_price(line.product, organisation)
        line_total = (lm * price).quantize(_CENT) if price else None
        if line_total:
            subtotal += line_total
        else:
            has_unpriced = True
        schedule.append({
            'label': 'Cutlist output',
            'description': str(line.product),
            'lineal_metres': str(lm),
            'unit_price': str(price) if price else None,
            'line_total': str(line_total) if line_total else None,
        })

    return subtotal, schedule, has_unpriced


def _calc_cladding(job):
    """
    Same (subtotal, schedule, has_unpriced) contract as _calc_subjob, but for a
    cladding job's areas directly — cladding has no Section, no pitch, no boundary
    joists/beams/cutlist lines, so it's a much shorter calculation.
    """
    organisation = job.project.organisation
    schedule = []
    subtotal = Decimal('0')
    has_unpriced = False

    freight_settings = SystemSettings.get()
    effective_wastage = job.wastage_pct if job.wastage_pct is not None else freight_settings.wastage_pct
    wastage_factor = Decimal('1') + _d(effective_wastage) / Decimal('100')

    for area in job.cladding_areas.select_related('cladding_product').all():
        if not area.cladding_product or not area.cladding_product.cover_mm:
            has_unpriced = True
            continue
        lm = _area_lm(area.area_m2, area.cladding_product.cover_mm, wastage_factor)
        price = get_product_price(area.cladding_product, organisation)
        line_total = (lm * price).quantize(_CENT) if price else None
        if line_total:
            subtotal += line_total
        else:
            has_unpriced = True
        schedule.append({
            'label': area.area_label or 'Cladding',
            'description': str(area.cladding_product),
            'lineal_metres': str(lm),
            'unit_price': str(price) if price else None,
            'line_total': str(line_total) if line_total else None,
        })

    return subtotal, schedule, has_unpriced


# ── Freight ───────────────────────────────────────────────────────────────────

def calc_freight(subtotal, freight_settings):
    """
    Pure freight calculation.  Returns (freight_charge, surcharge).

    Below threshold  →  fixed_freight_fee charged, no surcharge.
    At/above threshold →  no freight fee, optional surcharge percentage.
    """
    if subtotal < freight_settings.freight_threshold:
        return freight_settings.fixed_freight_fee, Decimal('0')
    surcharge = Decimal('0')
    if freight_settings.surcharge_enabled:
        surcharge = (
            subtotal * freight_settings.surcharge_percentage / Decimal('100')
        ).quantize(_CENT)
    return Decimal('0'), surcharge


def _update_job_freight(job):
    """Recompute and store hardware allowance, freight, and surcharge for the whole job."""
    from django.db.models import Sum
    if job.is_cladding:
        materials = job.calculated_subtotal or Decimal('0')
    else:
        materials = (
            job.sections.aggregate(s=Sum('calculated_subtotal'))['s'] or Decimal('0')
        )
    freight_settings = SystemSettings.get()
    pct = (
        _d(job.hardware_allowance_pct)
        if job.hardware_allowance_pct is not None
        else _d(freight_settings.hardware_allowance_pct)
    )
    hardware_amount = (materials * pct / Decimal('100')).quantize(_CENT)
    pre_freight = materials + hardware_amount
    freight_charge, surcharge = calc_freight(pre_freight, freight_settings)
    Job.objects.filter(pk=job.pk).update(
        hardware_allowance_amount=hardware_amount,
        freight_charge=freight_charge,
        freight_surcharge=surcharge,
    )


# ── Public entry points ───────────────────────────────────────────────────────

def run_subjob_calculation(sub_job):
    """
    Calculate and persist results for one framing sub-job (Section), then refresh
    job freight. Call this after saving a sub-job and its area / beam formsets.

    Stores the partial subtotal (sum of priced lines only).
    If ALL lines are unpriced, calculated_subtotal is set to None.
    The member_schedule JSON always records every line and whether any
    items are missing prices.
    """
    subtotal, schedule, has_unpriced = _calc_subjob(sub_job)

    # None means "cannot price yet" — only set when nothing could be priced.
    stored_subtotal = None if (has_unpriced and subtotal == 0) else subtotal

    Section.objects.filter(pk=sub_job.pk).update(
        calculated_subtotal=stored_subtotal,
        member_schedule={
            'items': schedule,
            'has_unpriced': has_unpriced,
        },
    )
    _update_job_freight(sub_job.job)


def run_cladding_calculation(job):
    """
    Calculate and persist results for a cladding job's areas directly onto the
    Job, then refresh freight. Call this after saving the job's cladding area
    formset. Same None/partial-pricing semantics as run_subjob_calculation.
    """
    subtotal, schedule, has_unpriced = _calc_cladding(job)

    stored_subtotal = None if (has_unpriced and subtotal == 0) else subtotal

    Job.objects.filter(pk=job.pk).update(
        calculated_subtotal=stored_subtotal,
        member_schedule={
            'items': schedule,
            'has_unpriced': has_unpriced,
        },
    )
    job.calculated_subtotal = stored_subtotal
    _update_job_freight(job)


def run_job_estimate(job):
    """
    Recalculate a whole job — every framing sub-job, or (for a cladding job) its
    areas directly — refresh freight, and return the job total. Useful for bulk
    recalculation (e.g. after a price book update).
    """
    if job.is_cladding:
        run_cladding_calculation(job)
    else:
        for sub_job in job.sections.prefetch_related(
            'areas__joist_product',
            'additional_beams__product',
            'cutlist_import_lines__product',
            'boundary_joist_product',
            'stair_void_trimmer_product',
            'roof_pitch',
        ).all():
            subtotal, schedule, has_unpriced = _calc_subjob(sub_job)
            stored_subtotal = None if (has_unpriced and subtotal == 0) else subtotal
            Section.objects.filter(pk=sub_job.pk).update(
                calculated_subtotal=stored_subtotal,
                member_schedule={
                    'items': schedule,
                    'has_unpriced': has_unpriced,
                },
            )
        _update_job_freight(job)
    job.refresh_from_db()
    return job.total
