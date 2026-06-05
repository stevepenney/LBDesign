from django.conf import settings
from django.db import models
from django.db.models import Max


class Project(models.Model):

    class Status(models.TextChoices):
        PRELIMINARY = 'preliminary', 'Preliminary'
        QUOTING     = 'quoting',     'Quoting'
        QUOTED      = 'quoted',      'Quoted'
        ORDERED     = 'ordered',     'Ordered'
        SUPPLIED    = 'supplied',    'Supplied'
        ON_HOLD     = 'on_hold',     'On Hold'
        CANCELLED   = 'cancelled',   'Cancelled'

    lb_job_number      = models.PositiveIntegerField(unique=True, editable=False)
    merchant_reference = models.CharField(max_length=200, blank=True)
    client_name        = models.CharField(max_length=200)
    site_address       = models.TextField()
    organisation       = models.ForeignKey(
        'accounts.Organisation',
        on_delete=models.PROTECT,
        related_name='projects',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_projects',
    )
    status     = models.CharField(max_length=20, choices=Status, default=Status.PRELIMINARY)
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-lb_job_number']

    def __str__(self):
        return f'{self.lb_ref} — {self.client_name}'

    @property
    def lb_ref(self):
        return f'LB-{self.lb_job_number:06d}'

    def save(self, *args, **kwargs):
        if not self.lb_job_number:
            last = Project.objects.aggregate(Max('lb_job_number'))['lb_job_number__max'] or 0
            self.lb_job_number = last + 1
        super().save(*args, **kwargs)
