"""
Estimation calculation engine.

Entry points
------------
run_section_calculation(section, user=None)
    Calculate one Part (Section) — framing or cladding, dispatched on
    section.is_cladding — and persist its results, including its own hardware
    allowance amount, then refresh job freight. Call this after saving a part
    and its area/beam or cladding-area/extra-item formsets.

run_job_estimate(job, user=None)
    Recalculate every Part in a job, then refresh freight. Returns the job
    total as a Decimal. Useful for bulk recalculation (e.g. after a price book
    update).

calc_freight(subtotal, freight_settings)
    Pure function — returns (freight_charge, surcharge).

Both entry points take an optional `user` — pass `request.user` from a view to
record a UsageEvent (see core.usage.log_usage_event). Leave it out for
non-request-driven callers (e.g. load_dummy_data) so seed/bulk work never
pollutes real usage stats.
"""

from decimal import Decimal

from core.models import SystemSettings, UsageEvent
from core.usage import log_usage_event
from products.pricing import get_product_price
from .models import Job, Section


_CENT = Decimal('0.01')


def _d(value):
    """Cast any numeric value to Decimal without float rounding."""
    return Decimal(str(value))


def _effective_pct(section, field):
    """
    Three-tier override resolution: the Part's own value, else the Job's
    default, else the global SystemSettings value. Used for wastage_pct and
    hardware_allowance_pct — the two factors that moved from Job to Section so
    each part of an estimate can carry its own rate.
    """
    section_value = getattr(section, field)
    if section_value is not None:
        return _d(section_value)
    job_value = getattr(section.job, field)
    if job_value is not None:
        return _d(job_value)
    return _d(getattr(SystemSettings.get(), field))


def _area_lm(area_m2, dimension_mm, wastage_factor, pitch_factor=Decimal('1')):
    """
    Shared area → lineal-metres conversion: area / (dimension in m) * pitch * wastage.
    Used for both joist/rafter spacing (FloorRoofArea) and cladding cover (CladdingArea) —
    same formula, different source for the mm dimension (a per-area design choice for
    spacing, vs a fixed product property for cladding cover).
    """
    dimension_m = _d(dimension_mm) / Decimal('1000')
    return (_d(area_m2) / dimension_m * pitch_factor * wastage_factor).quantize(_CENT)


def _priced_quantity(product, length_m, quantity):
    """
    The number multiplied by unit price for one schedule line. EACH products price
    per piece — length_m is ignored (a scriber's price doesn't depend on its
    length), only quantity counts. LM products (the default) price by
    length_m * quantity, same as every other calculation in this module.

    Only used by the two "flat line item" blocks (Additional beams, Cladding
    extra items) — every other block derives its lineal metres from an area or a
    real cut length, with no independent piece count to price "each" against.
    """
    if product and product.unit_of_measure == product.UnitOfMeasure.EACH:
        return _d(quantity)
    return _d(length_m) * _d(quantity)


# ── Core calculation ──────────────────────────────────────────────────────────

def _calc_subjob(sub_job, wastage_factor):
    """
    Returns (subtotal, schedule, has_unpriced) for a framing Part.

    subtotal     — Decimal sum of all priced line items.
    schedule     — list of dicts, one per line item.
    has_unpriced — True if any line item has no price in the active book.

    Line item dict keys:
        label, description, lineal_metres, unit, unit_price, line_total
        (unit_price and line_total are None when not priced; unit is only set
        on the Additional beams block — see _priced_quantity)

    Only "Additional beams" is unit-of-measure aware (via _priced_quantity).
    Joists/rafters, boundary joists, stair void trimmers, and cutlist import
    lines all derive their lineal metres from an area or a real cut length —
    there's no independent piece count there to price "each" against, so they
    stay pure lineal-metre calculations regardless of a linked product's
    unit_of_measure.
    """
    organisation = sub_job.job.project.organisation
    schedule = []
    subtotal = Decimal('0')
    has_unpriced = False

    freight_settings = SystemSettings.get()

    # ── Areas (joists / rafters) ──────────────────────────────────────────
    for area in sub_job.areas.select_related('joist_product', 'roof_pitch').all():
        if not area.joist_product:
            has_unpriced = True
            continue
        pitch_factor = Decimal('1')
        if sub_job.is_roof and area.roof_pitch:
            pitch_factor = _d(area.roof_pitch.pitch_factor)
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

    # ── Additional beams (unit-of-measure aware — see _priced_quantity) ────
    for beam in sub_job.additional_beams.select_related('product').all():
        if not beam.product:
            has_unpriced = True
            continue
        lm = _priced_quantity(beam.product, _d(beam.length_m) * wastage_factor, beam.quantity)
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
            'unit': beam.product.unit_of_measure,
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


def _calc_cladding(section, wastage_factor):
    """
    Same (subtotal, schedule, has_unpriced) contract as _calc_subjob, but for a
    cladding Part's areas directly.

    Areas and CladdingCutlistLines are merged per product, not switched wholesale:
    a vertical area whose product has already been imported from a generated
    cutlist (see cladding_import_cutlist_results) is priced from that real stock
    quantity instead of its rough area estimate; every other area (horizontal —
    which never goes through the cutlist — or vertical but not yet imported)
    keeps the area-based estimate. This avoids double-counting a product that's
    priced both ways while still supporting a part that mixes both orientations.

    Only "Cladding extra items" is unit-of-measure aware (via _priced_quantity).
    Areas (area→cover derived) and cutlist lines (real cut stock lengths) have no
    independent piece count to price "each" against, so they stay pure
    lineal-metre calculations regardless of a linked product's unit_of_measure.
    """
    organisation = section.job.project.organisation
    schedule = []
    subtotal = Decimal('0')
    has_unpriced = False

    cutlist_lines = list(section.cladding_cutlist_lines.select_related('product').all())
    cutlist_product_ids = {line.product_id for line in cutlist_lines if line.product_id}

    for area in section.cladding_areas.select_related('cladding_product').all():
        if area.orientation == area.Orientation.VERTICAL and area.cladding_product_id in cutlist_product_ids:
            continue
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

    for line in cutlist_lines:
        lm = _d(line.length_m) * _d(line.quantity)
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

    for item in section.cladding_extra_items.select_related('product').all():
        if not item.product:
            has_unpriced = True
            lm = _d(item.length_m) * _d(item.quantity) * wastage_factor
            schedule.append({
                'label': item.product_description or 'Extra item',
                'description': item.product_description or 'Unmatched product',
                'lineal_metres': str(lm),
                'unit_price': None,
                'line_total': '0.00',
            })
            continue
        lm = _priced_quantity(item.product, _d(item.length_m) * wastage_factor, item.quantity)
        price = get_product_price(item.product, organisation)
        line_total = (lm * price).quantize(_CENT) if price else None
        if line_total:
            subtotal += line_total
        else:
            has_unpriced = True
        schedule.append({
            'label': item.product_description or str(item.product),
            'description': str(item.product),
            'lineal_metres': str(lm),
            'unit': item.product.unit_of_measure,
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
    """
    Recompute and store freight/surcharge for the whole job. Hardware allowance
    is no longer a Job-level figure to compute here — each Part already stored
    its own (see run_section_calculation); this just sums materials + hardware
    across every part to get the pre-freight total.
    """
    materials = sum(
        (s.calculated_subtotal or Decimal('0')) + (s.hardware_allowance_amount or Decimal('0'))
        for s in job.sections.all()
    )
    freight_settings = SystemSettings.get()
    freight_charge, surcharge = calc_freight(materials, freight_settings)
    Job.objects.filter(pk=job.pk).update(
        freight_charge=freight_charge,
        freight_surcharge=surcharge,
    )


def _calc_and_store_section(section):
    """
    Calculate one Part (framing or cladding, dispatched on section.is_cladding)
    and persist its subtotal/hardware allowance/schedule — everything
    run_section_calculation does except refreshing job freight and logging,
    so run_job_estimate can call this per part and update freight once at the
    end instead of once per part.
    """
    wastage_factor = Decimal('1') + _effective_pct(section, 'wastage_pct') / Decimal('100')
    if section.is_cladding:
        subtotal, schedule, has_unpriced = _calc_cladding(section, wastage_factor)
    else:
        subtotal, schedule, has_unpriced = _calc_subjob(section, wastage_factor)

    # None means "cannot price yet" — only set when nothing could be priced.
    stored_subtotal = None if (has_unpriced and subtotal == 0) else subtotal

    hardware_pct = _effective_pct(section, 'hardware_allowance_pct')
    hardware_amount = ((stored_subtotal or Decimal('0')) * hardware_pct / Decimal('100')).quantize(_CENT)

    Section.objects.filter(pk=section.pk).update(
        calculated_subtotal=stored_subtotal,
        hardware_allowance_amount=hardware_amount,
        member_schedule={
            'items': schedule,
            'has_unpriced': has_unpriced,
        },
    )


# ── Public entry points ───────────────────────────────────────────────────────

def run_section_calculation(section, user=None):
    """
    Calculate and persist results for one Part (Section), then refresh job
    freight. Call this after saving a part and its area/beam or
    cladding-area/extra-item formsets.
    """
    _calc_and_store_section(section)
    _update_job_freight(section.job)
    log_usage_event(user, UsageEvent.EventType.ESTIMATE_CALCULATED)


def run_job_estimate(job, user=None):
    """
    Recalculate every Part in a job, refresh freight once, and return the job
    total. Useful for bulk recalculation (e.g. after a price book update).

    Logs at most one ESTIMATE_CALCULATED event for the whole call, regardless
    of how many parts get recalculated.
    """
    for section in job.sections.prefetch_related(
        'areas__joist_product',
        'areas__roof_pitch',
        'additional_beams__product',
        'cutlist_import_lines__product',
        'boundary_joist_product',
        'stair_void_trimmer_product',
        'cladding_areas__cladding_product',
        'cladding_extra_items__product',
        'cladding_cutlist_lines__product',
    ).all():
        _calc_and_store_section(section)
    _update_job_freight(job)
    log_usage_event(user, UsageEvent.EventType.ESTIMATE_CALCULATED)
    job.refresh_from_db()
    return job.total
