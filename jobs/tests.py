import csv
import io

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Organisation, User
from products.models import Product, ProductType
from projects.models import Project
from .models import CladdingArea, Job, Section


class CladdingExportCutsTests(TestCase):

    def setUp(self):
        org = Organisation.objects.create(name='Test Merchant')
        project = Project.objects.create(organisation=org)
        self.job = Job.objects.create(project=project)
        self.section = Section.objects.create(
            job=self.job, label='Oak Option', system_type=Section.SystemType.CLADDING,
        )
        product_type, _ = ProductType.objects.get_or_create(name='Cladding')
        self.product = Product.objects.create(
            name='Weatherboard 180', product_type=product_type, use_as_cladding=True, cover_mm=180,
        )
        self.staff = User.objects.create_user('lb', password='x', role=User.Role.LB_ADMIN)
        self.merchant = User.objects.create_user(
            'm', password='x', role=User.Role.MERCHANT_USER, organisation=org,
        )
        self.url = reverse('jobs:cladding_export_cuts', args=[self.job.pk, self.section.pk])

    def _rows(self, response):
        return list(csv.reader(io.StringIO(response.content.decode())))

    def test_flat_vertical_area_exports_one_row_per_length(self):
        CladdingArea.objects.create(
            section=self.section, area_label='North', orientation=CladdingArea.Orientation.VERTICAL,
            width_m='3.600', low_height_m='2.400', high_height_m='2.400', cladding_product=self.product,
        )
        self.client.force_login(self.staff)
        response = self.client.get(self.url)

        self.assertEqual(response['Content-Type'], 'text/csv')
        rows = self._rows(response)
        self.assertEqual(rows[0], ['Product', 'Mark', 'Length (mm)', 'Quantity'])
        self.assertEqual(rows[1], ['Weatherboard 180', 'North', '2400', '20'])  # 3600/180 = 20 boards

    @override_settings(STORAGES={
        'default':     {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    })
    def test_horizontal_areas_excluded(self):
        CladdingArea.objects.create(
            section=self.section, area_label='South', orientation=CladdingArea.Orientation.HORIZONTAL,
            width_m='3.600', low_height_m='2.400', high_height_m='2.400', cladding_product=self.product,
        )
        self.client.force_login(self.staff)
        response = self.client.get(self.url, follow=True)

        self.assertEqual(response.redirect_chain[-1][0], reverse('jobs:job_detail', args=[self.job.pk]))

    def test_area_missing_product_is_skipped_not_crashed(self):
        CladdingArea.objects.create(
            section=self.section, area_label='East', orientation=CladdingArea.Orientation.VERTICAL,
            width_m='3.600', low_height_m='2.400', high_height_m='2.400', cladding_product=None,
        )
        CladdingArea.objects.create(
            section=self.section, area_label='North', orientation=CladdingArea.Orientation.VERTICAL,
            width_m='3.600', low_height_m='2.400', high_height_m='2.400', cladding_product=self.product,
        )
        self.client.force_login(self.staff)
        response = self.client.get(self.url)

        rows = self._rows(response)
        self.assertEqual(len(rows), 2)  # header + North only

    def test_merchant_without_access_gets_redirected_not_the_file(self):
        other_org = Organisation.objects.create(name='Other Merchant')
        other_user = User.objects.create_user(
            'o', password='x', role=User.Role.MERCHANT_USER, organisation=other_org,
        )
        CladdingArea.objects.create(
            section=self.section, area_label='North', orientation=CladdingArea.Orientation.VERTICAL,
            width_m='3.600', low_height_m='2.400', high_height_m='2.400', cladding_product=self.product,
        )
        self.client.force_login(other_user)
        response = self.client.get(self.url)

        self.assertNotEqual(response.get('Content-Type'), 'text/csv')
