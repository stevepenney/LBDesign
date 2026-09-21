import io
import tempfile

from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from pypdf import PdfReader, PdfWriter

from accounts.models import Organisation, User
from .models import Project, ProjectDocument

DocType = ProjectDocument.DocumentType


def _pdf_bytes(pages):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DocumentMergeTests(TestCase):

    def setUp(self):
        org = Organisation.objects.create(name='Test Merchant')
        self.project = Project.objects.create(organisation=org, client_name='Smith')
        self.staff = User.objects.create_user('lb', password='x', role=User.Role.LB_ADMIN)
        self.merchant = User.objects.create_user(
            'm', password='x', role=User.Role.MERCHANT_USER, organisation=org,
        )
        self.report = self._doc('report.pdf', 3, DocType.ESTIMATE_REPORT)
        self.drawing = self._doc('elevations.pdf', 2, DocType.REVIT_EXPORT)
        self.url = reverse('projects:document_merge', args=[self.project.pk])

    def _doc(self, filename, pages, doc_type, content=None):
        return ProjectDocument.objects.create(
            project=self.project,
            uploaded_by=self.staff,
            document_type=doc_type,
            file=SimpleUploadedFile(filename, content or _pdf_bytes(pages)),
        )

    @override_settings(STORAGES={
        'default':     {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    })
    def test_merge_form_shown_to_staff_only(self):
        detail = reverse('projects:project_detail', args=[self.project.pk])

        self.client.force_login(self.staff)
        response = self.client.get(detail)
        self.assertContains(response, 'Merge into one PDF')
        self.assertContains(response, '["revit_export", "Revit Export"]')

        self.client.force_login(self.merchant)
        response = self.client.get(detail)
        self.assertNotContains(response, 'Merge into one PDF')
        self.assertNotContains(response, '["revit_export"')

    @override_settings(STORAGES={
        'default':     {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    })
    def test_detail_renders_when_uploader_was_deleted(self):
        self.report.uploaded_by = None
        self.report.save()

        self.client.force_login(self.staff)
        response = self.client.get(reverse('projects:project_detail', args=[self.project.pk]))

        self.assertEqual(response.status_code, 200)

    def test_merge_concatenates_report_then_drawing(self):
        self.client.force_login(self.staff)
        self.client.post(self.url, {'report': self.report.pk, 'drawing': self.drawing.pk})

        merged = self.project.documents.get(document_type=DocType.QUOTE)
        with merged.file.open('rb') as f:
            self.assertEqual(len(PdfReader(f).pages), 5)

    def test_unreadable_pdf_is_reported_not_saved(self):
        bad = self._doc('bad.pdf', 0, DocType.REVIT_EXPORT, content=b'not a pdf')
        self.client.force_login(self.staff)
        response = self.client.post(self.url, {'report': self.report.pk, 'drawing': bad.pk})

        self.assertFalse(self.project.documents.filter(document_type=DocType.QUOTE).exists())
        self.assertIn('not a readable PDF', ' '.join(str(m) for m in get_messages(response.wsgi_request)))

    def test_merchant_cannot_merge(self):
        self.client.force_login(self.merchant)
        self.client.post(self.url, {'report': self.report.pk, 'drawing': self.drawing.pk})

        self.assertFalse(self.project.documents.filter(document_type=DocType.QUOTE).exists())

    def test_wrong_document_type_rejected(self):
        self.client.force_login(self.staff)
        self.client.post(self.url, {'report': self.drawing.pk, 'drawing': self.report.pk})

        self.assertFalse(self.project.documents.filter(document_type=DocType.QUOTE).exists())
