from django.conf import settings
from django.db import models


class CutlistProject(models.Model):
    organisation = models.ForeignKey(
        'accounts.Organisation',
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
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cutlist_projects',
    )
    name = models.CharField(max_length=100, default='Untitled Cutlist')
    state = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.name} ({self.organisation.name})'
