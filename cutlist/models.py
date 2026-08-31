from django.conf import settings
from django.db import models


class CutlistProject(models.Model):
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='cutlist_projects',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cutlist_projects',
    )
    name       = models.CharField(max_length=100, default='Untitled Cutlist')
    state      = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.name} ({self.project.lb_ref})'

    def stock_order(self):
        """
        Flat list of {'group', 'product', 'length_m', 'qty'} rows — one row per
        distinct (group, stock length) combination for every optimised member,
        sorted by group then product then length descending.

        Mirrors updateSummary() in static/js/cutlist.js — this is the same
        stock order the Summary & Export step shows, read back from the saved
        state rather than recomputed.
        """
        rows = []
        for tab_index, tab in enumerate((self.state or {}).get('tabs', [])):
            results = tab.get('results')
            if not results:
                continue
            counts = {}
            for bin_ in results.get('bins', []):
                group = bin_.get('group') or ''
                length_m = bin_.get('stockLength', 0) / 1000
                key = (group, length_m)
                counts[key] = counts.get(key, 0) + 1
            for (group, length_m), qty in counts.items():
                rows.append({
                    'tab_index': tab_index,
                    'group': group,
                    'product': tab.get('memberName', ''),
                    'length_m': length_m,
                    'qty': qty,
                })
        rows.sort(key=lambda r: (r['group'], r['product'], -r['length_m']))
        return rows


class MemberProductMapping(models.Model):
    """
    Remembers which real Product a raw (freeform, typically CSV-imported) cutlist member
    name resolves to, so recurring names auto-link to a product on future imports without
    the user having to map them again.

    Keyed on a whitespace/case-normalized form of the name since real-world CSV exports vary
    in formatting for the same product (e.g. "LIB 240.88s" vs "LIB240.88s").
    """
    normalized_name = models.CharField(max_length=100, unique=True)
    raw_name = models.CharField(
        max_length=100,
        help_text='Most recent raw text this was set from (for display only).',
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='member_mappings',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['raw_name']

    def __str__(self):
        return f'{self.raw_name} → {self.product.name}'
