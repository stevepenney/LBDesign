"""
Management command: load_dummy_data

Creates realistic dummy data for development and testing.

Usage:
    python manage.py load_dummy_data          # idempotent — skips existing orgs
    python manage.py load_dummy_data --reset  # drops dummy data and recreates

What it creates:
    5 merchant organisations (NZ-flavoured names)
    2 organisations get 3 users each; the other 3 get 1 user each
    1–5 jobs per organisation, each with 1–3 sections
    Sections use products and roof pitches already in the database
"""

import random
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from accounts.models import Organisation, User
from core.models import RoofPitch
from jobs.calculations import run_subjob_calculation
from jobs.models import Job, Section, FloorRoofArea, AdditionalBeam
from products.models import Product


# ── Dummy data pools ─────────────────────────────────────────────────────────

ORGANISATIONS = [
    {'name': 'Henderson Timber & Hardware Ltd',  'users': 3},
    {'name': 'Pukekohe BuildingMart',            'users': 1},
    {'name': 'Tauranga Frame Supplies Ltd',      'users': 3},
    {'name': 'Rotorua Timber Co.',               'users': 1},
    {'name': 'Manawatu Building Supplies',       'users': 1},
]

# (first_name, last_name) pairs — realistic NZ names
PEOPLE = [
    ('James',    'Walker'),
    ('Sarah',    'Thompson'),
    ('Michael',  'Patel'),
    ('Emma',     'Robinson'),
    ('Daniel',   'Harris'),
    ('Olivia',   'Anderson'),
    ('Liam',     'Wilson'),
    ('Aroha',    'Tuhoe'),
    ('Wiremu',   'Heke'),
    ('Priya',    'Singh'),
    ('Connor',   'Murphy'),
]

# NZ street addresses
ADDRESSES = [
    '14 Rimu Road, Henderson, Auckland 0610',
    '7 Rata Street, Pukekohe, Auckland 2120',
    '32 Matapihi Road, Bethlehem, Tauranga 3110',
    '88 Fenton Street, Rotorua 3010',
    '23 Broadway Avenue, Palmerston North 4414',
    '5 Kawakawa Lane, Te Awamutu 3800',
    '110 Main Road, Katikati 3129',
    '62 Sunset Drive, Papamoa, Tauranga 3118',
    '19 Hillcrest Ave, Hamilton 3216',
    '3 Orewa Rise, Silverdale, Auckland 0992',
    '41 Harbourview Road, Whanganui 4500',
    '8 Glenbrook Crescent, Papakura, Auckland 2110',
    '76 Fairy Springs Road, Rotorua 3015',
    '27 Domain Road, Te Puke 3119',
    '55 Kaimai Way, Matamata 3400',
]

# Client names for jobs
CLIENT_NAMES = [
    'Wilson Construction Ltd',
    'Patel Developments',
    'Harris & Son Builders',
    'Southern Cross Homes',
    'Taonga Build Group',
    'Pacific Edge Developments',
    'Kauri Property Group',
    'Riverstone Construction',
    'Summit Homes NZ',
    'Maraenui Developments Ltd',
    'Blue Ridge Builders',
    'Fern Gully Properties',
]

# Section label templates
MIDFLOOR_LABELS = [
    'Unit {n} Midfloor',
    'Level {n} Floor',
    'Block {n} Midfloor',
    'Dwelling {n} Floor',
]

ROOF_LABELS = [
    'Unit {n} Roof',
    'Block {n} Roof',
    'Dwelling {n} Roof',
    'Main Roof',
]

AREA_LABELS = [
    [('Bathroom', 6), ('Kitchen / Living', 28), ('Bedrooms', 32)],
    [('Wet Areas', 8), ('Main Floor', 55)],
    [('Entry / Hallway', 10), ('Living', 40), ('Bedrooms', 35)],
    [('Main Floor', 78)],
    [('Garage', 36), ('Living', 48), ('Bedrooms', 40)],
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _slug(name):
    return name.lower().replace(' ', '_').replace('&', 'and').replace('.', '').replace(',', '')


def _pick(lst, fallback=None):
    """Return a random element from lst, or fallback if lst is empty."""
    return random.choice(lst) if lst else fallback


class Command(BaseCommand):
    help = 'Load dummy organisations, users, jobs, and sections for development.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing dummy organisations and their data before recreating.',
        )

    def handle(self, *args, **options):
        rng = random.Random(42)   # fixed seed → reproducible names/refs
        random.seed(42)

        # Fetch lookup data from DB
        joist_products    = list(Product.objects.filter(use_as_joist_rafter=True,       is_active=True))
        beam_products     = list(Product.objects.filter(use_as_beam=True,               is_active=True))
        boundary_products = list(Product.objects.filter(use_as_boundary_joist=True,     is_active=True))
        trimmer_products  = list(Product.objects.filter(use_as_stair_void_trimmer=True, is_active=True))
        roof_pitches      = list(RoofPitch.objects.all())

        if not joist_products:
            self.stdout.write(self.style.WARNING(
                'No active joist/rafter products found — sections will be created without products. '
                'Add products via the admin before running this command for fully-priced dummy data.'
            ))

        if options['reset']:
            org_names = [o['name'] for o in ORGANISATIONS]
            deleted, _ = Organisation.objects.filter(name__in=org_names).delete()
            self.stdout.write(self.style.WARNING(f'Reset: deleted {deleted} existing dummy objects.'))

        people_pool = list(PEOPLE)
        rng.shuffle(people_pool)
        person_idx = 0

        job_counter = 1

        for org_data in ORGANISATIONS:
            org, created = Organisation.objects.get_or_create(
                name=org_data['name'],
                defaults={'is_merchant': True, 'is_active': True},
            )
            status = 'Created' if created else 'Skipped (exists)'
            self.stdout.write(f'  Org: {org.name} — {status}')

            if not created:
                continue   # don't add duplicate users/jobs to existing orgs

            # ── Users ──────────────────────────────────────────────────────
            users_created = []
            for i in range(org_data['users']):
                person = people_pool[person_idx % len(people_pool)]
                person_idx += 1
                first, last = person
                username = f'{first.lower()}.{last.lower()}{person_idx}'
                user = User.objects.create(
                    username=username,
                    first_name=first,
                    last_name=last,
                    email=f'{username}@example.com',
                    password=make_password('Lumberbank1!'),
                    organisation=org,
                    role=User.Role.MERCHANT_USER,
                    is_active=True,
                )
                users_created.append(user)
                self.stdout.write(f'    User: {user.get_full_name()} ({username})')

            primary_user = users_created[0]

            # ── Jobs ───────────────────────────────────────────────────────
            num_jobs = rng.randint(1, 5)
            for j in range(num_jobs):
                client  = rng.choice(CLIENT_NAMES)
                address = rng.choice(ADDRESSES)
                ref     = f'2026-{job_counter:03d}'
                job_counter += 1
                status_choice = rng.choice([
                    Job.Status.ESTIMATE,
                    Job.Status.ESTIMATE,
                    Job.Status.ESTIMATE,
                    Job.Status.DRAWING_UPLOADED,
                ])

                job = Job.objects.create(
                    organisation=org,
                    created_by=rng.choice(users_created),
                    job_reference=ref,
                    client_name=client,
                    site_address=address,
                    status=status_choice,
                )
                self.stdout.write(f'    Job: {ref} — {client}')

                # ── Sections ──────────────────────────────────────────────
                num_sections = rng.randint(1, 3)
                # Build a mix: prefer midfloor+roof pairs, or solo midfloor
                section_types = rng.choice([
                    ['midfloor'],
                    ['midfloor', 'roof'],
                    ['midfloor', 'midfloor', 'roof'],
                    ['midfloor', 'roof', 'roof'],
                ])[:num_sections]

                unit_num = 1
                for sys_type in section_types:
                    label_template = rng.choice(
                        MIDFLOOR_LABELS if sys_type == 'midfloor' else ROOF_LABELS
                    )
                    label = label_template.format(n=unit_num)
                    if sys_type == 'roof':
                        unit_num += 1

                    inc_bj = sys_type == 'midfloor' and rng.random() > 0.3
                    inc_sv = sys_type == 'midfloor' and rng.random() > 0.6
                    pitch  = _pick(roof_pitches) if sys_type == 'roof' else None

                    section = Section.objects.create(
                        job=job,
                        label=label,
                        system_type=sys_type,
                        include_boundary_joists=inc_bj,
                        boundary_perimeter_lm=round(rng.uniform(18, 60), 1) if inc_bj else None,
                        boundary_joist_product=_pick(boundary_products) if inc_bj and boundary_products else None,
                        include_stair_void_trimmers=inc_sv,
                        stair_void_trimmer_product=_pick(trimmer_products) if inc_sv and trimmer_products else None,
                        roof_pitch=pitch,
                    )

                    # ── Areas ─────────────────────────────────────────────
                    area_set = rng.choice(AREA_LABELS)
                    for area_label, base_m2 in area_set:
                        area_m2 = round(base_m2 * rng.uniform(0.8, 1.2), 1)
                        FloorRoofArea.objects.create(
                            section=section,
                            area_label=area_label,
                            area_m2=area_m2,
                            joist_product=_pick(joist_products),
                            joist_spacing=rng.choice([400, 450, 600]),
                        )

                    # ── Additional beams (optional) ────────────────────────
                    if beam_products and rng.random() > 0.4:
                        num_beams = rng.randint(1, 2)
                        for _ in range(num_beams):
                            AdditionalBeam.objects.create(
                                section=section,
                                product=_pick(beam_products),
                                length_m=round(rng.uniform(3.0, 9.0), 1),
                                quantity=rng.randint(1, 4),
                            )

                    run_subjob_calculation(section)
                    self.stdout.write(
                        f'      Section: {label} ({sys_type}) '
                        f'— ${section.calculated_subtotal or "unpriced"}'
                    )

        self.stdout.write(self.style.SUCCESS('\nDummy data loaded successfully.'))
        self.stdout.write(
            'All users have password: Lumberbank1!\n'
        )
