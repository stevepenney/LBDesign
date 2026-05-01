"""
Estimation calculation engine.

Entry points
------------
run_subjob_calculation(sub_job)
    Calculate one sub-job and persist results.  Call this immediately after
    saving a sub-job and its area / beam formsets.

run_job_estimate(job)
    Recalculate every sub-job in a job, then refresh freight.  Returns the
    job total as a Decimal.

calc_freight(subtotal, freight_settings)
    Pure function — returns (freight_charge, surcharge).
"""

from decimal import Decimal

from core.models import FreightSettings, StairVoidSettings
from products.pricing import get_product_price
from .models import Job, Section


_CENT = Decimal('0.01')


def _d(value):
    """Cast any numeric value to Decimal without float rounding."""
    return Decimal(str(value))


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
    organisation = sub_job.job.organisation
    schedule = []
    subtotal = Decimal('0')
    has_unpriced = False

    pitch_factor = Decimal('1')
    if sub_job.is_roof and sub_job.roof_pitch:
        pitch_factor = _d(sub_job.roof_pitch.pitch_factor)

    # ── Areas (joists / rafters) ──────────────────────────────────────────
    for area in sub_job.areas.select_related('joist_product').all():
        if not area.joist_product:
            has_unpriced = True
            continue
        lm = (_d(area.area_m2) / _d(area.spacing_m) * pitch_factor).quantize(_CENT)
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
        lm = (_d(sub_job.boundary_perimeter_lm) * _d('1.5')).quantize(_CENT)
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
        lm = _d(StairVoidSettings.get().allowance_lm)
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
        lm = (_d(beam.length_m) * _d(beam.quantity)).quantize(_CENT)
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
    """Recompute and store freight/surcharge for the whole job."""
    from django.db.models import Sum
    subtotal = (
        job.sections.aggregate(s=Sum('calculated_subtotal'))['s'] or Decimal('0')
    )
    freight_settings = FreightSettings.get()
    freight_charge, surcharge = calc_freight(subtotal, freight_settings)
    Job.objects.filter(pk=job.pk).update(
        freight_charge=freight_charge,
        freight_surcharge=surcharge,
    )


# ── Public entry points ───────────────────────────────────────────────────────

def run_subjob_calculation(sub_job):
    """
    Calculate and persist results for one sub-job, then refresh job freight.
    Call this after saving a sub-job and its area / beam formsets.

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


def run_job_estimate(job):
    """
    Recalculate every sub-job in a job, refresh freight, return the job total.
    Useful for bulk recalculation (e.g. after a price book update).
    """
    for sub_job in job.sections.prefetch_related(
        'areas__joist_product',
        'additional_beams__product',
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
