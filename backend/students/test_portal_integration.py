from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from admissions.models import Campus, Department, PISTApplicant, Program, RollNumberSequence, RollSlip, TestCenter, TestSession
from .models import StudentProfile


class StudentPortalIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='portal@example.com', email='portal@example.com', password='PortalPass!29')
        self.profile = StudentProfile.objects.create(
            user=self.user, full_name='Portal Student', cnic='12345-1234567-1', date_of_birth='2000-01-15',
            phone='03001234567', address='Islamabad', student_id='PIST-STU-PORTAL-0001',
        )
        self.client.force_login(self.user)

    def test_onboarding_progress_is_server_computed(self):
        progress = self.profile.get_onboarding_progress()
        self.assertEqual(len(progress), 8)
        self.assertTrue(progress[0]['complete'])
        self.assertTrue(progress[1]['complete'])
        self.assertTrue(progress[2]['current'])
        response = self.client.get(reverse('students:dashboard'))
        self.assertContains(response, 'Application progress')
        self.assertContains(response, 'Academic Information Added')
        self.assertNotContains(response, 'Entry Test / Roll Slip')

    def test_roll_slip_navigation_appears_only_for_issued_scheduled_application(self):
        campus = Campus.objects.create(name='PIST Islamabad Main Campus', city='Islamabad', code='ISB', address='H-12')
        department = Department.objects.create(campus=campus, code='CS', name='Department of Computer Science', slug='cs')
        program = Program.objects.create(department=department, campus=campus, name='Bachelor of Science in Computer Science', code='BSCS-ISB', slug='bscs-isb')
        center = TestCenter.objects.create(campus=campus, name='Islamabad Test Center', address='H-12', city='Islamabad', building='Academic Block A', hall='Hall 3')
        session = TestSession.objects.create(test_center=center, program=program, test_date=date(2026, 9, 10), reporting_time=time(8, 30), start_time=time(9), building='Academic Block A', hall='Hall 3')
        application = PISTApplicant.objects.create(
            student=self.profile, application_id='APP-2026-PORTAL', program_registration_id='CS26-0001',
            application_status=PISTApplicant.ApplicationStatus.SUBMITTED, eligibility_status=PISTApplicant.EligibilityStatus.ELIGIBLE,
            full_name=self.profile.full_name, father_name='', cnic=self.profile.cnic, email=self.user.email, phone=self.profile.phone,
            address=self.profile.address, matric_marks=800, matric_total=1000, fsc_marks=800, fsc_total=1000,
            campus=campus, program=program, source_application_id='APP-2026-PORTAL', test_session=session,
            roll_number='PIST-ISB-CS-2026-0001', test_date=session.test_date, reporting_time=session.reporting_time,
            test_venue=center.name, test_building=session.building, test_hall=session.hall,
        )
        RollSlip.objects.create(application=application, roll_number=application.roll_number, test_session=session)
        response = self.client.get(reverse('students:dashboard'))
        self.assertContains(response, 'Entry Test / Roll Slip')
        self.assertContains(response, application.roll_number)
        self.assertContains(response, 'Upcoming Entry Test')

    def test_progress_marks_roll_and_schedule_steps_from_real_database_state(self):
        campus = Campus.objects.create(name='PIST Islamabad Main Campus', city='Islamabad', code='ISB', address='H-12')
        department = Department.objects.create(campus=campus, code='CS', name='Department of Computer Science', slug='cs')
        program = Program.objects.create(department=department, campus=campus, name='Bachelor of Science in Computer Science', code='BSCS-ISB', slug='bscs-isb')
        center = TestCenter.objects.create(campus=campus, name='Islamabad Test Center', address='H-12', city='Islamabad', building='Academic Block A', hall='Hall 3')
        session = TestSession.objects.create(test_center=center, program=program, test_date=date(2026, 9, 10), reporting_time=time(8, 30), start_time=time(9), building='Academic Block A', hall='Hall 3')
        application = PISTApplicant.objects.create(
            student=self.profile, application_id='APP-2026-PROGRESS', program_registration_id='CS26-0001', full_name=self.profile.full_name,
            father_name='', cnic=self.profile.cnic, email=self.user.email, phone=self.profile.phone, address=self.profile.address,
            matric_marks=800, matric_total=1000, fsc_marks=800, fsc_total=1000, campus=campus, program=program,
            source_application_id='APP-2026-PROGRESS', roll_number='PIST-ISB-CS-2026-0001', test_session=session,
            eligibility_status=PISTApplicant.EligibilityStatus.ELIGIBLE,
        )
        progress = self.profile.get_onboarding_progress()
        self.assertTrue(progress[4]['complete'])
        self.assertTrue(progress[5]['complete'])
        self.assertTrue(progress[6]['complete'])
        self.assertTrue(progress[7]['complete'])
        self.assertEqual(application.roll_number, 'PIST-ISB-CS-2026-0001')

    def test_cross_student_roll_slip_uses_branded_forbidden_page(self):
        other_user = get_user_model().objects.create_user(username='other@example.com', email='other@example.com', password='PortalPass!29')
        other = StudentProfile.objects.create(user=other_user, full_name='Other Student', cnic='12345-1234567-2', date_of_birth='2000-01-15', phone='03001234567', address='Lahore', student_id='PIST-STU-OTHER-0001')
        campus = Campus.objects.create(name='PIST Islamabad Main Campus', city='Islamabad', code='ISB', address='H-12')
        department = Department.objects.create(campus=campus, code='CS', name='Department of Computer Science', slug='cs')
        program = Program.objects.create(department=department, campus=campus, name='Bachelor of Science in Computer Science', code='BSCS-ISB', slug='bscs-isb')
        application = PISTApplicant.objects.create(
            student=other, application_id='APP-2026-OTHER', program_registration_id='CS26-0001', full_name=other.full_name,
            cnic=other.cnic, email=other_user.email, phone=other.phone, address=other.address, father_name='',
            matric_marks=800, matric_total=1000, fsc_marks=800, fsc_total=1000, campus=campus, program=program,
            source_application_id='APP-2026-OTHER', roll_number='PIST-ISB-CS-2026-0002',
        )
        self.assertEqual(self.client.get(reverse('admissions:roll_slip', kwargs={'application_uuid': application.pk})).status_code, 403)
        response = self.client.get(reverse('admissions:roll_slip', kwargs={'application_uuid': application.pk}))
        self.assertIn(b'Access not available', response.content)
