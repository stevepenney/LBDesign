"""
Management command: fix_duplicate_cutlist_bins

One-time data correction for a bug (fixed in static/js/cutlist.js) where re-optimising a
tab with a locked bin, after that bin's cuts fully consumed the remaining quantity of some
cut length, duplicated the locked bin(s) in tab.results.bins — same object appearing twice
(or, after repeated re-optimises, more), inflating stockCount/totalStockUsed and therefore
both the stock-order quantities shown to users and the $ figure cladding_import_cutlist_results
pulls into a priced estimate. Locked bins are never touched by a normal re-optimise, so
already-corrupted saves don't self-heal even after the JS fix — this corrects the stored
CutlistProject.state directly.

Usage:
    python manage.py fix_duplicate_cutlist_bins            # dry run — reports only
    python manage.py fix_duplicate_cutlist_bins --apply     # writes the fix
    python manage.py fix_duplicate_cutlist_bins --apply --pk 9 --pk 60   # only these projects

Safe to re-run: projects with no duplicate (non-null) bin ids are left untouched, so a
second run after --apply reports nothing left to fix.
"""

from django.core.management.base import BaseCommand

from cutlist.models import CutlistProject


def _kerf_loss(bin_, kerf_width):
    real_cuts = sum(1 for c in bin_.get('cuts', []) if not (isinstance(c, dict) and c.get('isFullStick')))
    return real_cuts * kerf_width


def _display_length(cut):
    if isinstance(cut, dict):
        dl = cut.get('displayLength')
        return dl if dl is not None else cut.get('length', 0)
    return cut


def _dedupe_tab_results(results, kerf_width):
    """
    Returns (changed, removed_count) — mutates `results` in place if there were real
    (non-null) duplicate bin ids. Bins with no id (a separate, pre-existing, unrelated
    quirk in some older saves) are left alone entirely — never deduped against each other.
    """
    bins = results.get('bins', [])
    real_ids = [b.get('id') for b in bins if b.get('id') is not None]
    if len(set(real_ids)) == len(real_ids):
        return False, 0

    seen = set()
    deduped, removed = [], []
    for b in bins:
        bid = b.get('id')
        if bid is not None:
            if bid in seen:
                removed.append(b)
                continue
            seen.add(bid)
        deduped.append(b)

    # totalStockUsed/totalKerfLoss are always recomputed fresh from the bins list by the
    # app itself (never accumulated), so recomputing from the deduped list exactly matches
    # what a correct run would have produced — no ambiguity.
    total_stock_used = sum(b['stockLength'] for b in deduped)
    total_kerf_loss  = sum(_kerf_loss(b, kerf_width) for b in deduped)

    # totalCutLength IS accumulated incrementally (+= lockedCutLength per re-optimise), so
    # instead of recomputing it from scratch — which would double-count overlength split
    # pieces whose displayLength is the full original length on every segment, a pre-existing
    # display-only quirk unrelated to this bug — subtract exactly what the buggy extra concat
    # added, using the app's own formula, over just the removed bins.
    extra_cut_length = sum(_display_length(c) for b in removed for c in b.get('cuts', []))
    total_cut_length = results.get('totalCutLength', 0) - extra_cut_length

    total_waste = total_stock_used - total_cut_length - total_kerf_loss
    waste_pct = f'{(total_waste / total_stock_used * 100):.2f}' if total_stock_used else '0.00'

    results['bins']             = deduped
    results['stockCount']       = len(deduped)
    results['totalStockUsed']   = total_stock_used
    results['totalKerfLoss']    = total_kerf_loss
    results['totalCutLength']   = total_cut_length
    results['totalWaste']       = total_waste
    results['wastePercentage']  = waste_pct
    return True, len(removed)


class Command(BaseCommand):
    help = 'Dedupe locked cutlist bins corrupted by the fixed re-optimise-with-locks bug.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write the fix (default is dry run).')
        parser.add_argument('--pk', action='append', type=int, dest='pks', help='Limit to specific CutlistProject pk(s).')

    def handle(self, *args, **options):
        qs = CutlistProject.objects.all().order_by('pk')
        if options['pks']:
            qs = qs.filter(pk__in=options['pks'])

        any_found = False
        for cl in qs:
            state = cl.state or {}
            kerf_width = (state.get('jobDetails') or {}).get('kerfWidth', 0)
            tabs = state.get('tabs', [])
            project_changed = False

            for tab in tabs:
                results = tab.get('results')
                if not results:
                    continue
                before = {k: results.get(k) for k in
                          ('stockCount', 'totalStockUsed', 'totalCutLength', 'totalKerfLoss', 'totalWaste', 'wastePercentage')}
                changed, removed_count = _dedupe_tab_results(results, kerf_width)
                if not changed:
                    continue

                any_found = True
                project_changed = True
                self.stdout.write(
                    f'CutlistProject {cl.pk} ({cl.name!r}) / {tab.get("memberName")!r}: '
                    f'{removed_count} duplicate bin(s) removed'
                )
                self.stdout.write(f'  before: {before}')
                self.stdout.write(f'  after : ' + str({k: results.get(k) for k in before}))

            if project_changed and options['apply']:
                cl.state = state
                cl.save(update_fields=['state', 'updated_at'])
                self.stdout.write(self.style.SUCCESS(f'  -> saved CutlistProject {cl.pk}'))

        if not any_found:
            self.stdout.write(self.style.SUCCESS('No duplicate-bin corruption found.'))
        elif not options['apply']:
            self.stdout.write(self.style.WARNING('Dry run only — re-run with --apply to write these changes.'))
