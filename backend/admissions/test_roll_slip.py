from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.urls import reverse

from admissions.models import Campus, Department, PISTApplicant, Program, RollSlip, TestCenter, TestSession
from admissions.services import RollNumberService
from students.models import StudentProfile


class RollSlipWorkflowTests(TestCase):
    def setUp(self):
        self.campus = Campus.objects.create(name='PIST Islamabad Main Campus', city='Islamabad', code='ISB', address='H-12')
        self.department = Department.objects.create(campus=self.campus, code='CS', name='Department of Computer Science', slug='cs')
        self.program = Program.objects.create(department=self.department, campus=self.campus, name='Bachelor of Science in Computer Science', code='BSCS-ISB', slug='bscs-isb')
        self.center = TestCenter.objects.create(campus=self.campus, name='PIST Islamabad Main Campus Test Center', address='H-12', building='Academic Block A', hall='Hall 3', capacity=20)
        self.session = TestSession.objects.create(test_center=self.center, program=self.program, test_date=date(2026, 9, 10), reporting_time=time(8, 30), start_time=time(9, 0), building='Academic Block A', hall='Hall 3', available_seats=20)
        self.student = self.make_student('a@example.com', '12345-1234567-1', 'Student A')
        self.other = self.make_student('b@example.com', '12345-1234567-2', 'Student B')
        self.application = PISTApplicant.objects.create(
            student=self.student, application_id='APP-2026-AAA', program_registration_id='CS26-0001',
            eligibility_status=PISTApplicant.EligibilityStatus.ELIGIBLE,
            application_status=PISTApplicant.ApplicationStatus.SCHEDULED,
            full_name=self.student.full_name, father_name='Father A', cnic=self.student.cnic,
            email=self.student.user.email, phone=self.student.phone, address='Private Address',
            matric_marks=800, matric_total=1000, fsc_marks=800, fsc_total=1000,
            campus=self.campus, program=self.program, source_application_id='APP-2026-AAA',
            test_session=self.session, test_date=self.session.test_date, reporting_time=self.session.reporting_time,
            test_venue=self.center.name, test_building=self.session.building, test_hall=self.session.hall,
        )

    def make_student(self, email, cnic, name):
        user = get_user_model().objects.create_user(username=email, email=email, password='AyeshaStrong!29')
        return StudentProfile.objects.create(user=user, student_id=f'PIST-STU-{email[0].upper()}', full_name=name, cnic=cnic, date_of_birth='2000-01-15', phone='03001234567', address='Islamabad')

    def test_roll_number_requires_eligibility_and_session(self):
        self.application.test_session = None
        self.application.save(update_fields=['test_session'])
        with self.assertRaises(Exception):
            RollNumberService.issue_roll_number(self.application)
        self.application.test_session = self.session
        self.application.eligibility_status = PISTApplicant.EligibilityStatus.NOT_ELIGIBLE
        self.application.save(update_fields=['eligibility_status', 'test_session'])
        with self.assertRaises(Exception):
            RollNumberService.issue_roll_number(self.application)

    def test_roll_number_is_issued_once_with_scope_format(self):
        self.application.eligibility_status = PISTApplicant.EligibilityStatus.ELIGIBLE
        self.application.save(update_fields=['eligibility_status'])
        slip = RollNumberService.issue_roll_number(self.application)
        self.assertRegex(slip.roll_number, r'^PIST-ISB-CS-2026-0001$')
        self.assertEqual(RollNumberService.issue_roll_number(self.application).pk, slip.pk)
        self.application.refresh_from_db()
        self.assertEqual(self.application.roll_number, slip.roll_number)

    def test_schedule_values_and_qr_token_are_persisted(self):
        self.application.eligibility_status = PISTApplicant.EligibilityStatus.ELIGIBLE
        self.application.save(update_fields=['eligibility_status'])
        slip = RollNumberService.issue_roll_number(self.application)
        self.assertEqual(slip.test_session.start_time, time(9, 0))
        self.assertEqual(slip.test_session.building, 'Academic Block A')
        self.assertEqual(slip.test_session.hall, 'Hall 3')
        self.assertNotEqual(str(slip.qr_token), str(self.application.pk))

    def test_owner_can_view_roll_slip_and_other_student_is_forbidden(self):
        self.application.eligibility_status = PISTApplicant.EligibilityStatus.ELIGIBLE
        self.application.save(update_fields=['eligibility_status'])
        RollNumberService.issue_roll_number(self.application)
        url = reverse('admissions:roll_slip', kwargs={'application_uuid': self.application.pk})
        self.client.force_login(self.student.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Program Reg ID')
        self.assertContains(response, self.application.roll_number)
        self.assertContains(response, 'Pakistan Institute of Science and Technology')
        self.assertContains(response, 'Admission Entry Test Roll Number Slip')
        self.assertContains(response, 'Candidate & Program Information')
        self.assertContains(response, 'Academic Block A')
        self.assertContains(response, 'Hall 3')
        self.assertContains(response, "Candidate's Signature")
        self.assertContains(response, 'data:image/png;base64,')
        self.client.force_login(self.other.user)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_anonymous_roll_slip_redirects_to_student_login(self):
        url = reverse('admissions:roll_slip', kwargs={'application_uuid': self.application.pk})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('students:login') + f'?next=/admissions/roll-slip/{self.application.pk}/')

    def test_staff_can_view_roll_slip(self):
        self.application.eligibility_status = PISTApplicant.EligibilityStatus.ELIGIBLE
        self.application.save(update_fields=['eligibility_status'])
        RollNumberService.issue_roll_number(self.application)
        staff = get_user_model().objects.create_user(username='staff', password='staff-password', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse('admissions:roll_slip', kwargs={'application_uuid': self.application.pk})).status_code, 200)

    def test_qr_verification_is_limited_and_invalid_tokens_are_safe(self):
        self.application.eligibility_status = PISTApplicant.EligibilityStatus.ELIGIBLE
        self.application.save(update_fields=['eligibility_status'])
        slip = RollNumberService.issue_roll_number(self.application)
        response = self.client.get(reverse('admissions:verify_roll_slip', kwargs={'qr_token': slip.qr_token}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Application Verified')
        self.assertContains(response, self.application.full_name)
        self.assertContains(response, slip.roll_number)
        self.assertNotContains(response, self.application.cnic)
        self.assertNotContains(response, self.application.email)
        self.assertNotContains(response, '800 / 1000')
        self.assertNotContains(response, 'Private Address')
        invalid = self.client.get('/admissions/verify/00000000-0000-0000-0000-000000000000/')
        self.assertEqual(invalid.status_code, 404)
        self.assertNotIn(b'Traceback', invalid.content)
