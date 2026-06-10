from django.conf import settings
from django.db import models
from django.db.models import Max


class Project(models.Model):

    class Status(models.TextChoices):
        DRAFT       = 'draft',       'Draft'
        PRELIMINARY = 'preliminary', 'Preliminary'
        QUOTING     = 'quoting',     'Quoting'
        QUOTED      = 'quoted',      'Quoted'
        ORDERED     = 'ordered',     'Ordered'
        SUPPLIED    = 'supplied',    'Supplied'
        ON_HOLD     = 'on_hold',     'On Hold'
        CANCELLED   = 'cancelled',   'Cancelled'
        DISCARDED   = 'discarded',   'Discarded'

    lb_job_number      = models.PositiveIntegerField(unique=True, editable=False)
    merchant_reference = models.CharField(max_length=200, blank=True)
    client_name        = models.CharField(max_length=200, blank=True)
    site_address       = models.TextField(blank=True)
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
    status     = models.CharField(max_length=20, choices=Status, default=Status.DRAFT)
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

    @property
    def display_ref(self):
        """Merchant-facing identifier — their reference, or client name, or Unlabelled."""
        return self.merchant_reference or self.client_name or 'Unlabelled'

    def save(self, *args, **kwargs):
        if not self.lb_job_number:
            last = Project.objects.aggregate(Max('lb_job_number'))['lb_job_number__max'] or 0
            self.lb_job_number = last + 1
        super().save(*args, **kwargs)


class ProjectDocument(models.Model):

    class DocumentType(models.TextChoices):
        DRAWING = 'drawing', 'Drawing'
        DESIGN  = 'design',  'Design File'
        QUOTE   = 'quote',   'Quote'
        OTHER   = 'other',   'Other'

    project       = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    uploaded_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    document_type = models.CharField(max_length=20, choices=DocumentType, default=DocumentType.DRAWING)
    name          = models.CharField(max_length=200, blank=True)
    file          = models.FileField(upload_to='project_docs/%Y/%m/', blank=True)
    external_url  = models.URLField(max_length=500, blank=True, verbose_name='Cloud storage link')
    notes         = models.TextField(blank=True)
    uploaded_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.name or self.get_document_type_display()

    @property
    def display_name(self):
        return self.name or self.get_document_type_display()

    @property
    def filename(self):
        """Basename of the uploaded file (no path prefix)."""
        if self.file:
            from pathlib import PurePosixPath
            return PurePosixPath(self.file.name).name
        return ''

    @property
    def link_url(self):
        if self.file:
            return self.file.url
        return self.external_url
