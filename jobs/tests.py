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


@override_settings(STORAGES={
    'default':     {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class CladdingBoardsReportTests(TestCase):

    def setUp(self):
        org = Organisation.objects.create(name='Test Merchant')
        project = Project.objects.create(organisation=org)
        self.job = Job.objects.create(project=project)
        self.section = Section.objects.create(
            job=self.job, label='Oak Option', system_type=Section.SystemType.CLADDING,
        )
        product_type, _ = ProductType.objects.get_or_create(name='Cladding')
        product = Product.objects.create(
            name='Weatherboard 180', product_type=product_type, use_as_cladding=True, cover_mm=180,
        )
        # North: 3.6m wide -> ceil(3600/180) = 20 boards @ 2400mm.
        # East:  1.8m wide -> ceil(1800/180) = 10 boards @ 2400mm — same length, different Mark,
        # so the simplified view has to collapse these two into one 30-piece row.
        CladdingArea.objects.create(
            section=self.section, area_label='North', orientation=CladdingArea.Orientation.VERTICAL,
            width_m='3.600', low_height_m='2.400', high_height_m='2.400', cladding_product=product,
        )
        CladdingArea.objects.create(
            section=self.section, area_label='East', orientation=CladdingArea.Orientation.VERTICAL,
            width_m='1.800', low_height_m='2.400', high_height_m='2.400', cladding_product=product,
        )
        self.staff = User.objects.create_user('lb', password='x', role=User.Role.LB_ADMIN)
        self.url = reverse('jobs:cladding_boards_report', args=[self.job.pk, self.section.pk])

    def test_detailed_view_breaks_down_by_mark(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)  # default view

        self.assertContains(response, 'North')
        self.assertContains(response, 'East')
        product_groups = response.context['product_groups']
        self.assertEqual(len(product_groups), 1)
        group = product_groups[0]
        self.assertEqual(group['total_pieces'], 30)
        self.assertEqual(group['total_lm'], 72.0)
        self.assertEqual(
            [(r['mark'], r['length_mm'], r['quantity']) for r in group['rows']],
            [('East', 2400, 10), ('North', 2400, 20)],
        )

    def test_simple_view_collapses_marks_by_length(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url, {'view': 'simple'})

        self.assertNotContains(response, 'North')
        self.assertNotContains(response, 'East')
        group = response.context['product_groups'][0]
        self.assertEqual(group['rows'], [{'mark': None, 'length_mm': 2400, 'quantity': 30, 'show_mark': False}])

    def test_no_boards_redirects_with_message(self):
        self.section.cladding_areas.all().delete()
        self.client.force_login(self.staff)
        response = self.client.get(self.url, follow=True)

        self.assertEqual(response.redirect_chain[-1][0], reverse('jobs:job_detail', args=[self.job.pk]))
