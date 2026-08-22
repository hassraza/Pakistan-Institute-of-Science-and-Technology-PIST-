from decimal import Decimal
from datetime import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.management import call_command
from io import StringIO
from django.urls import reverse
from rest_framework.test import APIClient

from admissions.models import Campus, Department, PISTApplicant, Program, ProgramEligibility, ProgramTestRequirement, Qualification, TestCenter, TestSession, TestType
from admissions.services import EligibilityService, RollNumberService, TestSchedulingService


class AdmissionsModelTests(TestCase):
    def setUp(self):
        self.campus = Campus.objects.create(
            name='PIST Islamabad Campus',
            city='Islamabad',
            code='ISB',
            address='H-12, Islamabad',
            description='Primary campus',
        )
        self.department = Department.objects.create(
            campus=self.campus,
            name='Department of Computer Science',
            slug='isb-computer-science',
            description='CS department',
        )
        self.program = Program.objects.create(
            department=self.department,
            name='BS Computer Science',
            code='BSCS',
            slug='isb-bscs',
            description='CS program',
            eligibility_percentage=Decimal('60.00'),
            eligibility_text='Minimum 60%',
            required_test_type='USAT',
            admissions_open=True,
            duration='4 Years',
            degree_level='Bachelor',
        )

    def test_campus_department_program_relationship(self):
        self.assertEqual(self.program.department.campus, self.campus)
        self.assertEqual(self.campus.departments.count(), 1)
        self.assertEqual(self.department.programs.count(), 1)

    def test_only_one_main_campus_is_retained(self):
        self.campus.is_main_campus = True
        self.campus.save()
        other = Campus.objects.create(name='Other Campus', city='Lahore', code='OTH', address='Other address', is_main_campus=True)
        self.assertFalse(Campus.objects.get(pk=self.campus.pk).is_main_campus)
        self.assertEqual(Campus.objects.filter(is_main_campus=True).count(), 1)
        self.assertTrue(other.is_main_campus)


    def test_applicant_creation_and_roll_number_uniqueness_constraint(self):
        applicant = PISTApplicant.objects.create(
            full_name='Test Student',
            father_name='Father',
            cnic='12345-1234567-1',
            email='student@example.com',
            phone='03001234567',
            address='Islamabad',
            matric_marks=850,
            matric_total=1100,
            fsc_marks=920,
            fsc_total=1100,
            campus=self.campus,
            program=self.program,
            roll_number='PIST-ISB-BSCS-2026-0001',
            source_application_id='SRC-001',
        )
        self.assertEqual(applicant.matric_percentage.quantize(Decimal('0.01')), Decimal('77.27'))
        with self.assertRaises(Exception):
            PISTApplicant.objects.create(
                full_name='Other Student',
                father_name='Father',
                cnic='12345-1234567-2',
                email='student2@example.com',
                phone='03001234568',
                address='Islamabad',
                matric_marks=850,
                matric_total=1100,
                fsc_marks=920,
                fsc_total=1100,
                campus=self.campus,
                program=self.program,
                roll_number='PIST-ISB-BSCS-2026-0001',
                source_application_id='SRC-002',
            )


class ExternalApplicationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.raise_request_exception = False
        self.campus = Campus.objects.create(
            name='PIST Islamabad Campus',
            city='Islamabad',
            code='ISB',
            address='H-12, Islamabad',
            description='Primary campus',
        )
        self.department = Department.objects.create(
            campus=self.campus,
            name='Department of Computer Science',
            slug='isb-computer-science',
            description='CS department',
        )
        self.program = Program.objects.create(
            department=self.department,
            name='BS Computer Science',
            code='BSCS',
            slug='isb-bscs',
            description='CS program',
            eligibility_percentage=Decimal('60.00'),
            eligibility_text='Minimum 60%',
            required_test_type='USAT',
            admissions_open=True,
            duration='4 Years',
            degree_level='Bachelor',
        )
        self.center = TestCenter.objects.create(
            campus=self.campus,
            name='PIST Islamabad Admission Test Center',
            address='H-12, Islamabad',
            building='Academic Block A',
            hall='Hall A-101',
            capacity=50,
        )
        TestSession.objects.create(
            test_center=self.center,
            program=self.program,
            test_date='2026-09-01',
            reporting_time='08:30:00',
            available_seats=50,
        )
        self.url = reverse('external_apply')

    def _payload(self, **overrides):
        payload = {
            'source_application_id': 'CENTRAL-APP-001',
            'full_name': 'Muhammad Hassan Raza',
            'father_name': 'Father Name',
            'cnic': '00000-0000000-0',
            'email': 'student@example.com',
            'phone': '03000000000',
            'address': 'Islamabad',
            'matric_marks': 850,
            'matric_total': 1100,
            'fsc_marks': 920,
            'fsc_total': 1100,
            'tests': [{'type': 'USAT', 'score': 78}],
            'campus_code': 'ISB',
            'program_code': 'BSCS',
        }
        payload.update(overrides)
        return payload

    def test_missing_api_key_rejected(self):
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertIn(response.status_code, {401, 403})

    def test_invalid_api_key_rejected(self):
        with self.settings(PIST_EXTERNAL_API_KEY='expected-secret'):
            response = self.client.post(self.url, self._payload(), format='json', HTTP_X_PIST_API_KEY='wrong-secret')
        self.assertEqual(response.status_code, 403)

    def test_successful_application(self):
        with self.settings(PIST_EXTERNAL_API_KEY='expected-secret'):
            response = self.client.post(self.url, self._payload(), format='json', HTTP_X_PIST_API_KEY='expected-secret')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['success'])
        self.assertTrue(PISTApplicant.objects.filter(source_application_id='CENTRAL-APP-001').exists())

    def test_duplicate_application_returns_conflict(self):
        with self.settings(PIST_EXTERNAL_API_KEY='expected-secret'):
            self.client.post(self.url, self._payload(), format='json', HTTP_X_PIST_API_KEY='expected-secret')
            response = self.client.post(self.url, self._payload(), format='json', HTTP_X_PIST_API_KEY='expected-secret')
        self.assertEqual(response.status_code, 409)

    def test_eligibility_failure_returns_422(self):
        with self.settings(PIST_EXTERNAL_API_KEY='expected-secret'):
            response = self.client.post(
                self.url,
                self._payload(matric_marks=300, fsc_marks=300),
                format='json',
                HTTP_X_PIST_API_KEY='expected-secret',
            )
        self.assertEqual(response.status_code, 422)


class PublicAndAdminTests(TestCase):
    def setUp(self):
        self.campus = Campus.objects.create(
            name='PIST Islamabad Campus',
            city='Islamabad',
            code='ISB',
            address='H-12, Islamabad',
            description='Primary campus',
        )
        self.department = Department.objects.create(
            campus=self.campus,
            name='Department of Computer Science',
            slug='isb-computer-science',
            description='CS department',
        )
        self.program = Program.objects.create(
            department=self.department,
            name='BS Computer Science',
            code='BSCS',
            slug='isb-bscs',
            description='CS program',
            eligibility_percentage=Decimal('60.00'),
            eligibility_text='Minimum 60%',
            required_test_type='USAT',
            admissions_open=True,
            duration='4 Years',
            degree_level='Bachelor',
        )
        self.applicant = PISTApplicant.objects.create(
            full_name='Test Student',
            father_name='Father',
            cnic='12345-1234567-1',
            email='student@example.com',
            phone='03001234567',
            address='Islamabad',
            matric_marks=850,
            matric_total=1100,
            fsc_marks=920,
            fsc_total=1100,
            campus=self.campus,
            program=self.program,
            roll_number='PIST-ISB-BSCS-2026-0001',
            source_application_id='SRC-001',
            status=PISTApplicant.Status.ROLL_ISSUED,
        )
        self.admin_user = get_user_model().objects.create_user(
            username='officer',
            password='password123',
            is_staff=True,
        )

    def test_roll_slip_loads(self):
        response = self.client.get(reverse('admissions:roll_slip', kwargs={'application_uuid': self.applicant.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.applicant.roll_number)

    def test_verification_page_loads(self):
        response = self.client.get(reverse('admissions:verify_application', kwargs={'application_uuid': self.applicant.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Application verified')
        self.assertNotContains(response, self.applicant.cnic)

    def test_invalid_verification_page_loads(self):
        response = self.client.get(reverse('admissions:verify_application', kwargs={'application_uuid': 'not-a-valid-uuid'}))
        self.assertEqual(response.status_code, 404)
        self.assertIn('Invalid Verification', response.content.decode())

    def test_track_page_loads(self):
        response = self.client.get(reverse('admissions:track_application'), {'reference': self.applicant.roll_number})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.applicant.full_name)

    def test_track_invalid_reference_shows_message(self):
        response = self.client.get(reverse('admissions:track_application'), {'reference': 'missing'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No matching application was found')

    def test_homepage_loads(self):
        response = self.client.get(reverse('admissions:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pakistan Institute of Science and Technology')
        self.assertContains(response, 'Admissions Open - Fall 2026')
        self.assertContains(response, 'Top 5 Tech University in Pakistan')

    def test_homepage_shows_database_driven_statistics_and_program_details(self):
        response = self.client.get(reverse('admissions:home'))
        self.assertEqual(response.context['campus_count'], 1)
        self.assertEqual(response.context['department_count'], 1)
        self.assertEqual(response.context['program_count'], 1)
        self.assertEqual(response.context['open_program_count'], 1)
        self.assertContains(response, 'Department of Computer Science')
        self.assertContains(response, 'BS Computer Science')
        self.assertContains(response, 'Admissions Open')

    def test_homepage_shows_closed_program_status(self):
        self.program.admissions_open = False
        self.program.save(update_fields=['admissions_open'])
        response = self.client.get(reverse('admissions:home'))
        self.assertEqual(response.context['program_count'], 1)
        self.assertEqual(response.context['open_program_count'], 0)
        self.assertNotContains(response, 'BS Computer Science')

    def test_campuses_page_loads(self):
        response = self.client.get(reverse('admissions:campuses'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.campus.name)

    def test_campus_detail_loads(self):
        response = self.client.get(reverse('admissions:campus_detail', kwargs={'campus_code': self.campus.code}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.department.name)

    def test_programs_page_loads(self):
        response = self.client.get(reverse('admissions:programs'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.program.name)

    def test_program_detail_loads_with_career_and_procedure(self):
        response = self.client.get(reverse('admissions:program_detail', kwargs={'program_slug': self.program.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Career Opportunities')
        self.assertContains(response, 'Admission Procedure')

    def test_roll_number_service_format(self):
        roll_number = RollNumberService.generate(campus_code=self.campus.code, program_code=self.program.code, year=2026)
        self.assertRegex(roll_number, r'^PIST-ISB-BSCS-2026-\d{4}$')

    def test_roll_number_service_unique_on_retry(self):
        first_roll = 'PIST-ISB-BSCS-2026-1234'
        PISTApplicant.objects.create(
            full_name='Existing Roll',
            father_name='Father',
            cnic='12345-1234567-9',
            email='existing@example.com',
            phone='03001230000',
            address='Islamabad',
            matric_marks=850,
            matric_total=1100,
            fsc_marks=920,
            fsc_total=1100,
            campus=self.campus,
            program=self.program,
            roll_number=first_roll,
            source_application_id='SRC-EXISTING',
        )
        with patch('admissions.services.secrets.randbelow', side_effect=[1234, 5678]):
            generated = RollNumberService.generate(campus_code=self.campus.code, program_code=self.program.code, year=2026)
        self.assertEqual(generated, 'PIST-ISB-BSCS-2026-5678')

    def test_eligibility_service_calculates_percentages(self):
        result = EligibilityService.evaluate(
            program=self.program,
            matric_marks=850,
            matric_total=1100,
            fsc_marks=920,
            fsc_total=1100,
            tests=[{'type': 'USAT', 'score': 78}],
        )
        self.assertTrue(result.eligible)
        self.assertGreater(result.matric_percentage, 77)
        self.assertGreater(result.fsc_percentage, 83)

    def test_test_scheduling_assigns_and_decrements_capacity(self):
        session = TestSession.objects.create(
            test_center=TestCenter.objects.create(
                campus=self.campus,
                name='Demo Test Center',
                address='H-12, Islamabad',
                building='Block B',
                hall='Hall B-201',
                capacity=2,
            ),
            program=self.program,
            test_date='2026-09-01',
            reporting_time='08:30:00',
            available_seats=2,
        )
        applicant = PISTApplicant.objects.create(
            full_name='Scheduler Test',
            father_name='Father',
            cnic='12345-1234567-3',
            email='scheduler@example.com',
            phone='03001230001',
            address='Islamabad',
            matric_marks=850,
            matric_total=1100,
            fsc_marks=920,
            fsc_total=1100,
            campus=self.campus,
            program=self.program,
            roll_number='PIST-ISB-BSCS-2026-9999',
            source_application_id='SRC-SCHED',
        )
        submitted_at = datetime(2026, 8, 22, 9, 0, 0)
        assigned = TestSchedulingService.assign(applicant, submitted_at=submitted_at)
        self.assertEqual(assigned.program, self.program)
        applicant.refresh_from_db()
        self.assertEqual(applicant.status, PISTApplicant.Status.ROLL_ISSUED)

    def test_filter_pagination_preserves_query(self):
        self.client.login(username='officer', password='password123')
        for index in range(30):
            PISTApplicant.objects.create(
                full_name=f'Paginated {index}',
                father_name='Father',
                cnic=f'12345-12345{index:02d}-{index % 10}',
                email=f'paginated{index}@example.com',
                phone='03001230002',
                address='Islamabad',
                matric_marks=850,
                matric_total=1100,
                fsc_marks=920,
                fsc_total=1100,
                campus=self.campus,
                program=self.program,
                roll_number=f'PIST-ISB-BSCS-2026-{2000 + index:04d}',
                source_application_id=f'SRC-PAG-{index}',
                status=PISTApplicant.Status.ROLL_ISSUED,
            )
        response = self.client.get(
            reverse('university_admin:applications'),
            {'campus': self.campus.pk, 'status': PISTApplicant.Status.ROLL_ISSUED, 'page': 2},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'campus=')

    def test_csv_export_respects_filters(self):
        self.client.login(username='officer', password='password123')
        response = self.client.get(
            reverse('university_admin:export_applications', kwargs={'format': 'csv'}),
            {'campus': self.campus.pk, 'status': PISTApplicant.Status.ROLL_ISSUED},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.applicant.full_name, response.content.decode())

    def test_json_export_respects_filters(self):
        self.client.login(username='officer', password='password123')
        response = self.client.get(
            reverse('university_admin:export_applications', kwargs={'format': 'json'}),
            {'campus': self.campus.pk, 'status': PISTApplicant.Status.ROLL_ISSUED},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.applicant.full_name, response.content.decode())

    def test_application_detail_contains_status_form_and_roll_slip_link(self):
        self.client.login(username='officer', password='password123')
        response = self.client.get(reverse('university_admin:application_detail', kwargs={'application_uuid': self.applicant.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Update Status')
        self.assertContains(response, 'Print Roll Slip')

    def test_status_update_rejects_arbitrary_values(self):
        self.client.login(username='officer', password='password123')
        response = self.client.post(
            reverse('university_admin:application_detail', kwargs={'application_uuid': self.applicant.pk}),
            {'status': 'Not A Real Status'},
        )
        self.assertEqual(response.status_code, 200)
        self.applicant.refresh_from_db()
        self.assertEqual(self.applicant.status, PISTApplicant.Status.ROLL_ISSUED)

    def test_django_admin_has_access(self):
        admin_user = get_user_model().objects.create_superuser(username='admin', password='password123')
        self.client.login(username='admin', password='password123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

    def test_status_update_works(self):
        self.client.login(username='officer', password='password123')
        response = self.client.post(
            reverse('university_admin:application_detail', kwargs={'application_uuid': self.applicant.pk}),
            {'status': PISTApplicant.Status.SELECTED},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.applicant.refresh_from_db()
        self.assertEqual(self.applicant.status, PISTApplicant.Status.SELECTED)


class AcademicSeedTests(TestCase):
    def run_seed(self):
        output = StringIO()
        call_command('seed_pist', stdout=output)
        return output.getvalue()

    def test_seed_creates_full_academic_structure_and_is_idempotent(self):
        self.run_seed()
        models = (Campus, Department, Program, Qualification, TestType, ProgramEligibility, ProgramTestRequirement)
        counts = {model.__name__: model.objects.count() for model in models}
        self.assertEqual(Campus.objects.get(code='ISB').name, 'Pakistan Institute of Science and Technology — Islamabad Main Campus')
        self.assertTrue(Campus.objects.get(code='ISB').is_main_campus)
        self.assertEqual(Campus.objects.filter(is_main_campus=True).count(), 1)
        self.assertEqual(Department.objects.count(), 24)
        self.assertEqual(Program.objects.filter(campus__code='ISB').count(), 41)
        self.assertEqual(Program.objects.count(), 55)
        for campus_code in ('ISB', 'LHR', 'KHI'):
            self.assertTrue(Program.objects.filter(name='Bachelor of Science in Computer Science', campus__code=campus_code).exists())
        self.assertEqual(Program.objects.filter(eligibility_rules__isnull=True).count(), 0)
        self.assertEqual(Program.objects.filter(test_requirements__isnull=True).count(), 0)
        self.assertTrue(Program.objects.filter(admissions_open=True).exists())
        self.assertTrue(Program.objects.filter(admissions_open=False).exists())
        self.run_seed()
        self.assertEqual(counts, {model.__name__: model.objects.count() for model in models})
