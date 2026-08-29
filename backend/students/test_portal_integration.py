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

    def test_dashboard_register_for_program_cta_and_dynamic_count(self):
        response = self.client.get(reverse('students:dashboard'))
        self.assertNotContains(response, 'Coming soon')
        self.assertContains(response, 'Register for a program')
        self.assertContains(response, reverse('admissions:programs'))
        self.assertEqual(response.context['registered_programs_count'], 0)

        campus = Campus.objects.create(name='PIST Islamabad Main Campus', city='Islamabad', code='ISB', address='H-12')
        department = Department.objects.create(campus=campus, code='CS', name='Department of Computer Science', slug='cs')
        program = Program.objects.create(department=department, campus=campus, name='Bachelor of Science in Computer Science', code='BSCS-ISB', slug='bscs-isb')
        PISTApplicant.objects.create(
            student=self.profile, application_id='APP-2026-COUNT', program_registration_id='CS26-0099',
            full_name=self.profile.full_name, cnic=self.profile.cnic, email=self.user.email, phone=self.profile.phone,
            address=self.profile.address, matric_marks=800, matric_total=1000, fsc_marks=800, fsc_total=1000,
            campus=campus, program=program, source_application_id='APP-2026-COUNT',
        )
        response2 = self.client.get(reverse('students:dashboard'))
        self.assertEqual(response2.context['registered_programs_count'], 1)

    def test_profile_password_change_links(self):
        response = self.client.get(reverse('students:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('students:password_change'))
        self.assertContains(response, 'Change password')

    def test_student_application_scoped_to_student_not_email(self):
        other_user = get_user_model().objects.create_user(username='other_same_email@example.com', email=self.user.email, password='PortalPass!29')
        other = StudentProfile.objects.create(user=other_user, full_name='Other Person', cnic='99999-9999999-9', date_of_birth='1999-01-01', phone='03009999999', address='Karachi', student_id='PIST-STU-OTHER-0099')
        campus = Campus.objects.create(name='PIST Islamabad Main Campus', city='Islamabad', code='ISB', address='H-12')
        department = Department.objects.create(campus=campus, code='CS', name='Department of Computer Science', slug='cs')
        program = Program.objects.create(department=department, campus=campus, name='Bachelor of Science in Computer Science', code='BSCS-ISB', slug='bscs-isb')
        app_other = PISTApplicant.objects.create(
            student=other, application_id='APP-OTHER-EMAIL', program_registration_id='CS26-0088',
            full_name=other.full_name, cnic=other.cnic, email=self.user.email, phone=other.phone, address=other.address,
            matric_marks=800, matric_total=1000, fsc_marks=800, fsc_total=1000, campus=campus, program=program,
            source_application_id='APP-OTHER-EMAIL',
        )
        # Logged-in as self.user, dashboard should not show app_other
        response = self.client.get(reverse('students:dashboard'))
        self.assertIsNone(response.context['application'])
        self.assertEqual(response.context['registered_programs_count'], 0)

    def test_registered_programs_empty_and_populated_states(self):
        response = self.client.get(reverse('students:registered_programs'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No registered programs yet')
        self.assertContains(response, reverse('admissions:programs'))

        campus = Campus.objects.create(name='PIST Islamabad Main Campus', city='Islamabad', code='ISB', address='H-12')
        department = Department.objects.create(campus=campus, code='CS', name='Department of Computer Science', slug='cs')
        program = Program.objects.create(department=department, campus=campus, name='Bachelor of Science in Computer Science', code='BSCS-ISB', slug='bscs-isb')
        PISTApplicant.objects.create(
            student=self.profile, application_id='APP-REG-01', program_registration_id='CS26-0077',
            full_name=self.profile.full_name, cnic=self.profile.cnic, email=self.user.email, phone=self.profile.phone,
            address=self.profile.address, matric_marks=800, matric_total=1000, fsc_marks=800, fsc_total=1000,
            campus=campus, program=program, source_application_id='APP-REG-01',
        )
        response_populated = self.client.get(reverse('students:registered_programs'))
        self.assertContains(response_populated, 'Bachelor of Science in Computer Science')
        self.assertContains(response_populated, 'APP-REG-01')
        self.assertNotContains(response_populated, 'No registered programs yet')

    def test_extra_js_rendered_in_base_student(self):
        self.client.logout()
        response = self.client.get(reverse('students:register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'password-toggle')

        self.client.force_login(self.user)
        academic_resp = self.client.get(reverse('students:matric_edit'))
        self.assertEqual(academic_resp.status_code, 200)
        self.assertContains(academic_resp, 'data-percentage-preview')

    def test_application_confirmation_renders_all_required_ids_and_next_steps(self):
        campus = Campus.objects.create(name='PIST Islamabad Main Campus', city='Islamabad', code='ISB', address='H-12')
        department = Department.objects.create(campus=campus, code='CS', name='Department of Computer Science', slug='cs')
        program = Program.objects.create(department=department, campus=campus, name='Bachelor of Science in Computer Science', code='BSCS-ISB', slug='bscs-isb')
        application = PISTApplicant.objects.create(
            student=self.profile, application_id='APP-2026-CONFIRM01', program_registration_id='CS26-0033',
            full_name=self.profile.full_name, cnic=self.profile.cnic, email=self.user.email, phone=self.profile.phone,
            address=self.profile.address, matric_marks=800, matric_total=1000, fsc_marks=800, fsc_total=1000,
            campus=campus, program=program, source_application_id='APP-2026-CONFIRM01',
        )
        response = self.client.get(reverse('students:application_detail', kwargs={'application_uuid': application.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'APP-2026-CONFIRM01')
        self.assertContains(response, 'CS26-0033')
        self.assertContains(response, 'Bachelor of Science in Computer Science')

    def test_roll_slip_entry_points_and_empty_state(self):
        # When student has an application with NO test scheduled
        campus = Campus.objects.create(name='PIST Islamabad Main Campus', city='Islamabad', code='ISB', address='H-12')
        department = Department.objects.create(campus=campus, code='CS', name='Department of Computer Science', slug='cs')
        program = Program.objects.create(department=department, campus=campus, name='Bachelor of Science in Computer Science', code='BSCS-ISB', slug='bscs-isb')
        application = PISTApplicant.objects.create(
            student=self.profile, application_id='APP-2026-UNSCHEDULED', program_registration_id='CS26-0044',
            full_name=self.profile.full_name, cnic=self.profile.cnic, email=self.user.email, phone=self.profile.phone,
            address=self.profile.address, matric_marks=800, matric_total=1000, fsc_marks=800, fsc_total=1000,
            campus=campus, program=program, source_application_id='APP-2026-UNSCHEDULED',
        )
        # /student/roll-slip/ shows meaningful empty state
        resp = self.client.get(reverse('students:roll_slip'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Your application has been received.')
        self.assertContains(resp, 'Your roll number and entry test details will appear here once your application is processed.')

        # /student/applications/<uuid>/roll-slip/ shows meaningful empty state instead of crashing
        resp_app = self.client.get(reverse('students:application_roll_slip', kwargs={'application_uuid': application.pk}))
        self.assertEqual(resp_app.status_code, 200)
        self.assertContains(resp_app, 'Your application has been received.')
