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
