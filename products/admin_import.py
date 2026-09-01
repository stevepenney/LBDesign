"""
CSV bulk-import helpers for the Products admin section — kept out of admin.py so the
ModelAdmin classes there stay focused on admin config. Two independent imports:

- Products (one-off catalog seed): a changelist-level "Import CSV" button, see
  `import_products_csv` — wired up via ProductAdmin.get_urls() in admin.py.
- PriceBook entries (periodic price refresh): no separate view — parsed directly from
  PriceBookAdmin.save_model() in admin.py via `import_pricebook_entries_csv`, since the upload
  field lives on the PriceBook add/change form itself, not a standalone page.
"""
import csv
import io
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import Product, ProductType, PriceBookEntry

TRUE_VALUES = {'true', '1', 'yes'}


def _parse_bool(value):
    return (value or '').strip().lower() in TRUE_VALUES


def _read_csv_rows(uploaded_file):
    """Returns a csv.DictReader over the uploaded file, tolerating a BOM from Excel exports."""
    return csv.DictReader(io.TextIOWrapper(uploaded_file.file, encoding='utf-8-sig'))


def import_products_csv(request):
    """GET: show the upload form. POST: parse + upsert Products, report results, redirect
    back to the changelist."""
    if request.method != 'POST':
        return render(request, 'admin/products/product_import_csv.html')

    uploaded_file = request.FILES.get('csv_file')
    if not uploaded_file:
        messages.error(request, 'No file was selected.')
        return redirect('admin:products_product_changelist')

    created = updated = 0
    errors = []

    try:
        rows = list(_read_csv_rows(uploaded_file))
    except (UnicodeDecodeError, csv.Error) as e:
        messages.error(request, f"Couldn't read that file as CSV: {e}")
        return redirect('admin:products_product_changelist')

    with transaction.atomic():
        for i, row in enumerate(rows, start=2):  # row 1 is the header
            name = (row.get('name') or '').strip()
            if not name:
                errors.append(f'Row {i}: missing name, skipped')
                continue

            type_name = (row.get('product_type') or '').strip()
            if not type_name:
                errors.append(f'Row {i} ({name}): missing product_type, skipped')
                continue
            product_type, _ = ProductType.objects.get_or_create(name=type_name)

            try:
                sort_order = int((row.get('sort_order') or '0').strip() or 0)
            except ValueError:
                sort_order = 0

            defaults = {
                'product_type': product_type,
                'is_active': _parse_bool(row.get('is_active')),
                'sort_order': sort_order,
                'use_as_joist_rafter': _parse_bool(row.get('use_as_joist_rafter')),
                'use_as_boundary_joist': _parse_bool(row.get('use_as_boundary_joist')),
                'use_as_stair_void_trimmer': _parse_bool(row.get('use_as_stair_void_trimmer')),
                'use_as_beam': _parse_bool(row.get('use_as_beam')),
                'stock_lengths': (row.get('stock_lengths') or '').strip(),
            }
            _, was_created = Product.objects.update_or_create(name=name, defaults=defaults)
            if was_created:
                created += 1
            else:
                updated += 1

    if created or updated:
        messages.success(request, f'Products import: {created} created, {updated} updated.')
    if errors:
        messages.warning(request, 'Some rows were skipped:\n' + '\n'.join(errors))
    if not created and not updated and not errors:
        messages.warning(request, 'No rows found in that file.')

    return redirect('admin:products_product_changelist')


def import_pricebook_entries_csv(request, price_book, uploaded_file):
    """Parses a pricebook-entries CSV and fully replaces price_book's entries with what's in
    the file (any existing entry for a product not present in this upload is removed — a
    periodic refresh is the complete new price list, not a patch). Returns nothing; reports
    results via the messages framework. Called from PriceBookAdmin.save_model()."""
    try:
        rows = list(_read_csv_rows(uploaded_file))
    except (UnicodeDecodeError, csv.Error) as e:
        messages.error(request, f"Couldn't read the pricing CSV: {e}")
        return

    staged = []  # (product, price)
    errors = []
    for i, row in enumerate(rows, start=2):
        product_name = (row.get('product_name') or '').strip()
        price_raw = (row.get('price_per_lm') or '').strip()
        if not product_name or not price_raw:
            errors.append(f'Row {i}: missing product_name or price_per_lm, skipped')
            continue

        product = Product.objects.filter(name=product_name).first()
        if not product:
            errors.append(f'Row {i}: no product named "{product_name}", skipped')
            continue

        try:
            price = Decimal(price_raw)
        except InvalidOperation:
            errors.append(f'Row {i} ({product_name}): invalid price "{price_raw}", skipped')
            continue

        staged.append((product, price))

    matched_products = [product for product, _price in staged]
    with transaction.atomic():
        removed, _ = PriceBookEntry.objects.filter(price_book=price_book) \
            .exclude(product__in=matched_products).delete()
        updated = created = 0
        for product, price in staged:
            _, was_created = PriceBookEntry.objects.update_or_create(
                price_book=price_book, product=product, defaults={'price_per_lm': price},
            )
            created += was_created
            updated += not was_created

    messages.success(
        request,
        f'Pricing import for "{price_book}": {created} created, {updated} updated, '
        f'{removed} removed (not present in this upload).',
    )
    if errors:
        messages.warning(request, 'Some rows were skipped:\n' + '\n'.join(errors))
