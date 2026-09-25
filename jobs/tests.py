import csv
import io

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Organisation, User
from cutlist.models import CutlistProject
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
        self.assertEqual(rows[0], ['Product', 'Area', 'Length (mm)', 'Quantity'])
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
        self.product = Product.objects.create(
            name='Weatherboard 180', product_type=product_type, use_as_cladding=True, cover_mm=180,
        )
        self.staff = User.objects.create_user('lb', password='x', role=User.Role.LB_ADMIN)
        self.url = reverse('jobs:cladding_boards_report', args=[self.job.pk, self.section.pk])

    def test_collapses_areas_with_the_same_length_into_one_row(self):
        # North: 3.6m wide -> ceil(3600/180) = 20 boards @ 2400mm.
        # East:  1.8m wide -> ceil(1800/180) = 10 boards @ 2400mm — same length, different Area,
        # so the summary has to collapse these two into one 30-piece row.
        CladdingArea.objects.create(
            section=self.section, area_label='North', orientation=CladdingArea.Orientation.VERTICAL,
            width_m='3.600', low_height_m='2.400', high_height_m='2.400', cladding_product=self.product,
        )
        CladdingArea.objects.create(
            section=self.section, area_label='East', orientation=CladdingArea.Orientation.VERTICAL,
            width_m='1.800', low_height_m='2.400', high_height_m='2.400', cladding_product=self.product,
        )
        self.client.force_login(self.staff)
        response = self.client.get(self.url)

        self.assertNotContains(response, 'North')
        self.assertNotContains(response, 'East')
        group = response.context['product_groups'][0]
        self.assertEqual(group['left'], [{'length_mm': 2400, 'quantity': 30}])
        self.assertEqual(group['right'], [])
        self.assertEqual(group['total_pieces'], 30)
        self.assertEqual(group['total_lm'], 72.0)

    def test_many_lengths_split_into_two_columns(self):
        # 8 areas of increasing width -> 8 distinct board lengths (via distinct widths driving
        # distinct raking boards would be more setup; simplest is 8 flat areas of different
        # heights, each its own row) — enough to cross BOARD_REPORT_SPLIT_ROWS (6).
        for i in range(8):
            height = f'{2.400 + i / 10:.3f}'
            CladdingArea.objects.create(
                section=self.section, area_label=f'Area {i}', orientation=CladdingArea.Orientation.VERTICAL,
                width_m='0.900', low_height_m=height, high_height_m=height, cladding_product=self.product,
            )
        self.client.force_login(self.staff)
        response = self.client.get(self.url)

        group = response.context['product_groups'][0]
        self.assertEqual(len(group['left']), 4)
        self.assertEqual(len(group['right']), 4)

    def test_no_boards_redirects_with_message(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url, follow=True)

        self.assertEqual(response.redirect_chain[-1][0], reverse('jobs:job_detail', args=[self.job.pk]))


@override_settings(STORAGES={
    'default':     {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class EstimateReportTests(TestCase):

    def setUp(self):
        self.org = Organisation.objects.create(name='Test Merchant')
        self.project = Project.objects.create(organisation=self.org)
        self.job = Job.objects.create(project=self.project)
        self.staff = User.objects.create_user('lb', password='x', role=User.Role.LB_ADMIN)
        self.url = reverse('jobs:estimate_report', args=[self.job.pk])

    def test_framing_part_shows_quantities_without_prices(self):
        Section.objects.create(
            job=self.job, label='Unit 1 Midfloor', system_type=Section.SystemType.MIDFLOOR,
            member_schedule={
                'items': [{
                    'label': 'LIB240', 'description': '', 'lineal_metres': 45.5, 'unit': 'lm',
                    'unit_price': 12.5, 'line_total': 568.75,
                }],
                'has_unpriced': False,
            },
            calculated_subtotal='568.75',
        )
        self.client.force_login(self.staff)
        response = self.client.get(self.url)

        self.assertContains(response, 'Member Schedule')
        self.assertContains(response, 'LIB240')
        self.assertContains(response, '45.50')
        self.assertNotContains(response, 'Unit Price')
        self.assertNotContains(response, 'Line Total')
        # $568.75 legitimately appears once, in the overall summary (materials subtotal) — the
        # unit price is what must never surface on the Part's own page.
        self.assertNotContains(response, '$12.50')

    def test_cladding_part_without_cutlist_shows_board_summary(self):
        section = Section.objects.create(
            job=self.job, label='Oak Option', system_type=Section.SystemType.CLADDING,
        )
        product_type, _ = ProductType.objects.get_or_create(name='Cladding')
        product = Product.objects.create(
            name='Weatherboard 180', product_type=product_type, use_as_cladding=True, cover_mm=180,
        )
        CladdingArea.objects.create(
            section=section, area_label='North', orientation=CladdingArea.Orientation.VERTICAL,
            width_m='3.600', low_height_m='2.400', high_height_m='2.400', cladding_product=product,
        )
        self.client.force_login(self.staff)
        response = self.client.get(self.url)

        self.assertContains(response, 'Board Summary')
        self.assertContains(response, '2400')

    def test_cladding_part_with_optimized_cutlist_shows_diagrams_not_board_summary(self):
        section = Section.objects.create(
            job=self.job, label='Oak Option', system_type=Section.SystemType.CLADDING,
        )
        cutlist = CutlistProject.objects.create(
            project=self.project,
            state={'tabs': [{'memberName': 'Weatherboard 180', 'results': {'bins': [], 'kerfWidth': 3}}]},
        )
        section.cladding_cutlist = cutlist
        section.save(update_fields=['cladding_cutlist'])

        self.client.force_login(self.staff)
        response = self.client.get(self.url)

        self.assertNotContains(response, 'Board Summary')
        self.assertContains(response, f'id="diagram-root-{section.pk}"')

    def test_elevations_section_removed(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)

        self.assertNotContains(response, 'Elevations')
