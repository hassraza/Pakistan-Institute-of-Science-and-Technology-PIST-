from __future__ import annotations

import datetime
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from admissions.models import Campus, Department, PISTApplicant, Program, RollSlip, TestCenter, TestSession
from admissions.services import current_admission_year
from students.models import Notification, StudentProfile


class IntegrationAPIBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.api_key = getattr(settings, 'PIST_EXTERNAL_API_KEY', '') or 'pist-integration-secret-key-2026'

        # Campus & Department
        cls.campus = Campus.objects.create(
            name='Islamabad Main Campus',
            city='Islamabad',
            code='ISB',
            address='Sector H-12, Islamabad',
            is_main_campus=True,
            admissions_open=True,
        )
        cls.department = Department.objects.create(
            campus=cls.campus,
            name='Computer Science',
            code='CS',
        )

        # Programs
        cls.program = Program.objects.create(
            department=cls.department,
            campus=cls.campus,
            name='Bachelor of Science in Computer Science',
            code='BSCS-ISB',
            admissions_open=True,
            eligibility_percentage=60.0,
        )
        cls.closed_program = Program.objects.create(
            department=cls.department,
            campus=cls.campus,
            name='Master of Science in Data Science',
            code='MSDS-ISB',
            admissions_open=False,
            eligibility_percentage=60.0,
        )

        # Test center and session
        cls.test_center = TestCenter.objects.create(
            campus=cls.campus,
            name='Islamabad Main Testing Center',
            address='Academic Block A, Islamabad',
            building='Academic Block A',
            hall='Hall 1',
            capacity=100,
        )
        cls.test_session = TestSession.objects.create(
            test_center=cls.test_center,
            program=cls.program,
            test_date=datetime.date.today() + datetime.timedelta(days=14),
            reporting_time=datetime.time(8, 30),
            start_time=datetime.time(9, 0),
            building='Academic Block A',
            hall='Hall 1',
            available_seats=50,
        )

        # Existing student
        cls.user = get_user_model().objects.create_user(
            username='test_student_01',
            email='student01@example.com',
            password='Password123!',
            first_name='Ahmad',
            last_name='Khan',
        )
        cls.student = StudentProfile.objects.create(
            user=cls.user,
            student_id='PIST-STU-2026-0099',
            full_name='Ahmad Khan',
            email_verified=True,
            cnic='61101-1234567-1',
            phone='03001234567',
            nationality='Pakistani',
        )

    def setUp(self):
        self.client = APIClient()
        self.auth_headers = {'HTTP_X_API_KEY': self.api_key}


class APIKeyAuthenticationTests(IntegrationAPIBaseTestCase):
    def test_missing_api_key_header_returns_401(self):
        url = reverse('integration:student_create')
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Missing X-API-KEY header', str(response.data))

    def test_invalid_api_key_returns_401(self):
        url = reverse('integration:student_create')
        response = self.client.post(url, {}, format='json', HTTP_X_API_KEY='invalid-secret-key')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Invalid API key', str(response.data))

    def test_valid_api_key_succeeds(self):
        url = reverse('integration:student_notifications', kwargs={'student_id': self.student.student_id})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_case_insensitive_header_name(self):
        url = reverse('integration:student_notifications', kwargs={'student_id': self.student.student_id})
        response = self.client.get(url, headers={'x-api-key': self.api_key})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class StudentCreateAPITests(IntegrationAPIBaseTestCase):
    def test_create_student_standard_payload_success(self):
        url = reverse('integration:student_create')
        payload = {
            'full_name': 'Fatima Zahra',
            'email': 'fatima.zahra@example.com',
            'phone': '03129876543',
            'cnic': '35202-1234567-2',
        }
        response = self.client.post(url, payload, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data

        # Check all returned keys and PakUniPortal aliases
        self.assertIn('student_id', data)
        self.assertIn('pist_student_id', data)
        self.assertIn('id', data)
        self.assertEqual(data['student_id'], data['pist_student_id'])
        self.assertIn('username', data)
        self.assertIn('pist_username', data)
        self.assertIn('password', data)
        self.assertIn('pist_password', data)
        self.assertTrue(data['student_id'].startswith('PIST-STU-'))

        # Check DB
        user = get_user_model().objects.filter(email='fatima.zahra@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, data['username'])
        self.assertTrue(user.check_password(data['password']))

        profile = StudentProfile.objects.filter(user=user).first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.full_name, 'Fatima Zahra')
        self.assertEqual(profile.cnic, '35202-1234567-2')

        # Check welcome notification created
        notification = Notification.objects.filter(student=profile).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, 'Welcome to PIST Portal')

    def test_create_student_pakuniportal_rich_payload_success(self):
        url = reverse('integration:student_create')
        payload = {
            'email': 'usman.ali@example.com',
            'username': 'usmanali',
            'first_name': 'Usman',
            'last_name': 'Ali',
            'date_of_birth': '2003-08-20',
            'gender': 'male',
            'phone_number': '03451122334',
            'address': 'House 12, Street 5, Lahore',
            'city': 'Lahore',
            'province': 'Punjab',
            'country': 'Pakistan',
            'nationality': 'Pakistani',
            'cnic_number': '35201-7654321-1',
            'passport_number': '',
        }
        response = self.client.post(url, payload, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        self.assertEqual(data['username'], 'usmanali')

        profile = StudentProfile.objects.filter(user__email='usman.ali@example.com').first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.full_name, 'Usman Ali')
        self.assertEqual(profile.cnic, '35201-7654321-1')
        self.assertEqual(str(profile.date_of_birth), '2003-08-20')
        self.assertEqual(profile.gender, 'male')
        self.assertEqual(profile.address, 'House 12, Street 5, Lahore')

    def test_create_student_unformatted_cnic_normalized(self):
        url = reverse('integration:student_create')
        payload = {
            'full_name': 'Bilal Tariq',
            'email': 'bilal.tariq@example.com',
            'phone': '03331234567',
            'cnic': '3520112345678',  # 13 digits without dashes
        }
        response = self.client.post(url, payload, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        profile = StudentProfile.objects.filter(user__email='bilal.tariq@example.com').first()
        self.assertEqual(profile.cnic, '35201-1234567-8')

    def test_create_duplicate_student_returns_409(self):
        url = reverse('integration:student_create')
        payload = {
            'full_name': 'Duplicate Student',
            'email': 'student01@example.com',  # already in setUpTestData
            'phone': '03001112233',
            'cnic': '61101-1234567-1',         # already in setUpTestData
        }
        response = self.client.post(url, payload, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['code'], 'duplicate')
        self.assertEqual(response.data['student_id'], self.student.student_id)

    def test_create_student_invalid_cnic_length(self):
        url = reverse('integration:student_create')
        payload = {
            'full_name': 'Invalid CNIC',
            'email': 'invalidcnic@example.com',
            'phone': '03001112233',
            'cnic': '12345',  # invalid
        }
        response = self.client.post(url, payload, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cnic', response.data)


class ApplicationCreateAPITests(IntegrationAPIBaseTestCase):
    def test_create_application_by_numeric_ids_success(self):
        url = reverse('integration:application_create')
        payload = {
            'student_id': self.student.user.id,
            'program_id': self.program.id,
        }
        response = self.client.post(url, payload, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        self.assertEqual(data['status'], 'submitted')
        self.assertEqual(data['application_status'], 'submitted')
        self.assertEqual(data['program_id'], self.program.id)
        self.assertEqual(data['program_name'], self.program.name)
        self.assertIn('application_id', data)
        self.assertIn('pist_application_id', data)
        self.assertEqual(data['application_id'], data['pist_application_id'])

        # Verify DB applicant
        applicant = PISTApplicant.objects.filter(student=self.student, program=self.program).first()
        self.assertIsNotNone(applicant)
        self.assertEqual(applicant.application_status, PISTApplicant.ApplicationStatus.SUBMITTED)

        # Check notification created
        notification = Notification.objects.filter(student=self.student, title='Application Submitted').first()
        self.assertIsNotNone(notification)

    def test_create_application_by_string_student_code_and_program_code(self):
        url = reverse('integration:application_create')
        payload = {
            'student_id': self.student.student_id,  # 'PIST-STU-2026-0099'
            'program_id': self.program.code,        # 'BSCS-ISB'
        }
        response = self.client.post(url, payload, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'submitted')

    def test_create_application_student_not_found(self):
        url = reverse('integration:application_create')
        payload = {
            'student_id': '999999',
            'program_id': self.program.id,
        }
        response = self.client.post(url, payload, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['code'], 'not_found')

    def test_create_application_program_not_found(self):
        url = reverse('integration:application_create')
        payload = {
            'student_id': self.student.student_id,
            'program_id': 'NONEXISTENT_CODE',
        }
        response = self.client.post(url, payload, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['code'], 'not_found')

    def test_create_application_admissions_closed(self):
        url = reverse('integration:application_create')
        payload = {
            'student_id': self.student.student_id,
            'program_id': self.closed_program.code,
        }
        response = self.client.post(url, payload, format='json', **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 'admissions_closed')

    def test_create_duplicate_application_returns_409(self):
        url = reverse('integration:application_create')
        payload = {
            'student_id': self.student.student_id,
            'program_id': self.program.id,
        }
        # First submission
        res1 = self.client.post(url, payload, format='json', **self.auth_headers)
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Duplicate submission
        res2 = self.client.post(url, payload, format='json', **self.auth_headers)
        self.assertEqual(res2.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(res2.data['code'], 'duplicate')
        self.assertIn('already exists', res2.data['detail'])


class ApplicationStatusAPITests(IntegrationAPIBaseTestCase):
    def setUp(self):
        super().setUp()
        self.applicant = PISTApplicant.objects.create(
            student=self.student,
            program=self.program,
            campus=self.campus,
            full_name=self.student.full_name,
            email=self.student.user.email,
            phone=self.student.phone,
            cnic=self.student.cnic,
            application_id='APP-2026-STATUSTEST',
            source_application_id='APP-2026-STATUSTEST',
            application_status=PISTApplicant.ApplicationStatus.UNDER_REVIEW,
        )

    def test_get_application_status_primary_url(self):
        url = reverse('integration:application_status', kwargs={'application_id': self.applicant.application_number})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['application_id'], self.applicant.application_number)
        self.assertEqual(response.data['pist_application_id'], self.applicant.application_number)
        self.assertEqual(response.data['status'], 'under_review')
        self.assertEqual(response.data['application_status'], 'under_review')

    def test_get_application_status_alt_url(self):
        # PakUniPortal default url: /api/integration/applications/{application_id}/
        url = reverse('integration:application_status_alt', kwargs={'application_id': self.applicant.application_number})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'under_review')

    def test_get_application_status_by_code(self):
        url = reverse('integration:application_status', kwargs={'application_id': self.applicant.application_id})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'under_review')

    def test_get_application_status_not_found(self):
        url = reverse('integration:application_status', kwargs={'application_id': '99999999'})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['code'], 'not_found')


class StudentNotificationsAPITests(IntegrationAPIBaseTestCase):
    def setUp(self):
        super().setUp()
        self.n1 = Notification.objects.create(
            student=self.student,
            title='Notification 1',
            message='First test message',
        )
        self.n2 = Notification.objects.create(
            student=self.student,
            title='Notification 2',
            message='Second test message',
        )

    def test_get_notifications_primary_url(self):
        url = reverse('integration:student_notifications', kwargs={'student_id': self.student.student_id})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        item = data[0]
        self.assertIn('id', item)
        self.assertIn('notification_id', item)
        self.assertIn('title', item)
        self.assertIn('message', item)
        self.assertIn('body', item)
        self.assertIn('type', item)
        self.assertIn('notification_type', item)

    def test_get_notifications_alt_url(self):
        # PakUniPortal default url: /api/integration/students/{student_id}/notifications/
        url = reverse('integration:student_notifications_alt', kwargs={'student_id': self.student.student_id})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_notifications_student_not_found(self):
        url = reverse('integration:student_notifications', kwargs={'student_id': '999999'})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['code'], 'not_found')


class RollSlipAPITests(IntegrationAPIBaseTestCase):
    def setUp(self):
        super().setUp()
        self.applicant = PISTApplicant.objects.create(
            student=self.student,
            program=self.program,
            campus=self.campus,
            full_name=self.student.full_name,
            email=self.student.user.email,
            phone=self.student.phone,
            cnic=self.student.cnic,
            application_id='APP-2026-ROLLTEST',
            source_application_id='APP-2026-ROLLTEST',
            application_status=PISTApplicant.ApplicationStatus.SCHEDULED,
            roll_number='PIST-ISB-CS-2026-9999',
            test_session=self.test_session,
            test_date=self.test_session.test_date,
            test_venue='Academic Block A, Hall 1, Islamabad Campus',
        )
        self.roll_slip = RollSlip.objects.create(
            application=self.applicant,
            roll_number='PIST-ISB-CS-2026-9999',
            test_session=self.test_session,
        )

    def test_get_roll_slip_primary_url(self):
        url = reverse('integration:roll_slip', kwargs={'application_id': self.applicant.application_number})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['roll_number'], 'PIST-ISB-CS-2026-9999')
        self.assertEqual(data['rollNumber'], 'PIST-ISB-CS-2026-9999')
        self.assertEqual(data['test_date'], str(self.test_session.test_date))
        self.assertIn('Academic Block A', data['venue'])

    def test_get_roll_slip_alt_url(self):
        # PakUniPortal default url: /api/integration/applications/{application_id}/roll-slip/
        url = reverse('integration:roll_slip_alt', kwargs={'application_id': self.applicant.application_number})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['roll_number'], 'PIST-ISB-CS-2026-9999')

    def test_get_roll_slip_not_issued_yet_returns_empty_roll_info(self):
        unscheduled_app = PISTApplicant.objects.create(
            student=self.student,
            program=self.closed_program,
            campus=self.campus,
            full_name=self.student.full_name,
            email=self.student.user.email,
            phone=self.student.phone,
            cnic=self.student.cnic,
            application_id='APP-2026-UNSCHEDULED',
            source_application_id='APP-2026-UNSCHEDULED',
            application_status=PISTApplicant.ApplicationStatus.SUBMITTED,
        )
        url = reverse('integration:roll_slip', kwargs={'application_id': unscheduled_app.application_number})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['roll_number'], '')
        self.assertIn('not been generated', response.data['detail'])

    def test_get_roll_slip_application_not_found_returns_404(self):
        url = reverse('integration:roll_slip', kwargs={'application_id': '999999'})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['code'], 'not_found')


class EndToEndPakUniPortalWorkflowSimulationTests(IntegrationAPIBaseTestCase):
    """
    Full end-to-end integration test simulating PakUniPortal's complete lifecycle:
    PakUniPortal
    ↓
    PIST student creation
    ↓
    PIST student account created
    ↓
    PIST application created
    ↓
    PIST admin changes application status
    ↓
    PakUniPortal can retrieve updated status
    ↓
    PIST generates notification
    ↓
    PakUniPortal retrieves notification
    ↓
    PIST generates roll slip
    ↓
    PakUniPortal retrieves roll slip
    """

    def test_complete_admission_workflow(self):
        # Step 1: PakUniPortal creates student
        student_url = reverse('integration:student_create')
        student_payload = {
            'email': 'zain.malik@example.com',
            'username': 'zainmalik',
            'first_name': 'Zain',
            'last_name': 'Malik',
            'date_of_birth': '2004-03-12',
            'gender': 'male',
            'phone_number': '03019876543',
            'address': 'F-8/3, Islamabad',
            'city': 'Islamabad',
            'province': 'ICT',
            'country': 'Pakistan',
            'nationality': 'Pakistani',
            'cnic_number': '61101-7788990-1',
        }
        res_stu = self.client.post(student_url, student_payload, format='json', **self.auth_headers)
        self.assertEqual(res_stu.status_code, status.HTTP_201_CREATED)
        stu_data = res_stu.data

        # PakUniPortal extracts credentials
        pist_student_id = stu_data['pist_student_id']
        pist_username = stu_data['pist_username']
        pist_password = stu_data['pist_password']

        self.assertTrue(pist_student_id.startswith('PIST-STU-'))
        self.assertEqual(pist_username, 'zainmalik')
        self.assertTrue(len(pist_password) >= 12)

        # Step 2: PakUniPortal submits application for student
        app_url = reverse('integration:application_create')
        app_payload = {
            'student_id': pist_student_id,
            'program_id': self.program.code,  # Uses external_program_id = 'BSCS-ISB'
        }
        res_app = self.client.post(app_url, app_payload, format='json', **self.auth_headers)
        self.assertEqual(res_app.status_code, status.HTTP_201_CREATED)
        app_data = res_app.data

        pist_application_id = app_data['pist_application_id']
        self.assertEqual(app_data['status'], 'submitted')
        self.assertIsNotNone(pist_application_id)

        # Step 3: PakUniPortal checks initial status
        status_url = reverse('integration:application_status_alt', kwargs={'application_id': pist_application_id})
        res_status = self.client.get(status_url, **self.auth_headers)
        self.assertEqual(res_status.status_code, status.HTTP_200_OK)
        self.assertEqual(res_status.data['status'], 'submitted')

        # Step 4: PIST Admin changes application status to UNDER_REVIEW
        applicant = PISTApplicant.objects.get(application_number=pist_application_id)
        applicant.application_status = PISTApplicant.ApplicationStatus.UNDER_REVIEW
        applicant.save(update_fields=['application_status', 'updated_at'])

        # Step 5: PakUniPortal sync service retrieves updated status
        res_status_updated = self.client.get(status_url, **self.auth_headers)
        self.assertEqual(res_status_updated.status_code, status.HTTP_200_OK)
        self.assertEqual(res_status_updated.data['status'], 'under_review')

        # Step 6: PIST generates an admin notification for the student
        Notification.objects.create(
            student=applicant.student,
            title='Application Under Review',
            message='Your admission credentials are currently being reviewed by the CS admissions committee.',
        )

        # Step 7: PakUniPortal retrieves student notifications
        notif_url = reverse('integration:student_notifications_alt', kwargs={'student_id': pist_student_id})
        res_notif = self.client.get(notif_url, **self.auth_headers)
        self.assertEqual(res_notif.status_code, status.HTTP_200_OK)
        notif_list = res_notif.data
        self.assertTrue(len(notif_list) >= 2)
        titles = [n['title'] for n in notif_list]
        self.assertIn('Application Under Review', titles)
        self.assertIn('Welcome to PIST Portal', titles)

        # Step 8: PakUniPortal sync service retrieves roll slip
        roll_url = reverse('integration:roll_slip_alt', kwargs={'application_id': pist_application_id})
        res_roll = self.client.get(roll_url, **self.auth_headers)
        self.assertEqual(res_roll.status_code, status.HTTP_200_OK)
        self.assertIn('roll_number', res_roll.data)
        self.assertIn('venue', res_roll.data)
