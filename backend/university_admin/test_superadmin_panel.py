from datetime import date, time, timedelta
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from admissions.models import Campus, Department, PISTApplicant, Program, TestCenter, TestSession, RollSlip
from students.models import AcademicDocument, Notification, StudentProfile
from students.services import generate_student_id


class SuperadminPanelTests(TestCase):
    def setUp(self):
        self.staff_user = get_user_model().objects.create_user(
            username='superadmin@pist.edu.pk',
            email='superadmin@pist.edu.pk',
            password='AdminPassword123!',
            is_staff=True,
            is_superuser=True,
        )
        self.student_user = get_user_model().objects.create_user(
            username='candidate@gmail.com',
            email='candidate@gmail.com',
            password='CandidatePass123!',
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            student_id=generate_student_id(),
            full_name='Zainab Tariq',
            cnic='35201-9988776-1',
            date_of_birth='2003-05-15',
            phone='03001122334',
        )
        self.campus = Campus.objects.create(code='ISB', name='Islamabad Campus', city='Islamabad', admissions_open=True)
        self.department = Department.objects.create(campus=self.campus, code='CS', name='Department of Computing')
        self.program = Program.objects.create(
            department=self.department,
            campus=self.campus,
            code='BSCS',
            name='BS Computer Science',
            degree_level='Undergraduate',
            admissions_open=True,
        )
        self.applicant = PISTApplicant.objects.create(
            student=self.student_profile,
            campus=self.campus,
            program=self.program,
            full_name='Zainab Tariq',
            cnic='35201-9988776-1',
            email='candidate@gmail.com',
            phone='03001122334',
            matric_marks=920,
            matric_total=1100,
            fsc_marks=980,
            fsc_total=1100,
            status=PISTApplicant.Status.RECEIVED,
            application_status=PISTApplicant.ApplicationStatus.SUBMITTED,
        )
        self.test_center = TestCenter.objects.create(
            campus=self.campus,
            name='PIST Central Auditorium',
            address='Sector H-12, Islamabad',
            building='Academic Block 1',
            hall='Main Auditorium',
            capacity=200,
        )
        self.test_session = TestSession.objects.create(
            test_center=self.test_center,
            program=self.program,
            test_date=timezone.localdate() + timedelta(days=7),
            reporting_time=time(8, 30),
            start_time=time(9, 0),
            building='Academic Block 1',
            hall='Main Auditorium',
            available_seats=50,
            is_active=True,
        )
        self.document = AcademicDocument.objects.create(
            student=self.student_profile,
            document_type=AcademicDocument.DocumentType.MATRIC_RESULT,
            file=SimpleUploadedFile('matric.pdf', b'%PDF-1.7 sample data', content_type='application/pdf'),
            file_name='matric.pdf',
        )

        self.client.force_login(self.staff_user)

    def test_dashboard_view_renders_metrics(self):
        url = reverse('university_admin:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')
        self.assertContains(response, 'Total Applications')
        self.assertContains(response, 'BS Computer Science')
        self.assertContains(response, 'Zainab Tariq')

    def test_applications_queue_filtering_and_bulk_actions(self):
        url = reverse('university_admin:applications')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admissions Applications')
        self.assertContains(response, 'Zainab Tariq')

        # Test bulk accept
        post_response = self.client.post(url, {
            'bulk_action': 'accept',
            'selected_applications': [str(self.applicant.pk)],
        })
        self.assertEqual(post_response.status_code, 302)
        self.applicant.refresh_from_db()
        self.assertEqual(self.applicant.application_status, PISTApplicant.ApplicationStatus.ACCEPTED)
        self.assertEqual(self.applicant.status, PISTApplicant.Status.ADMISSION_CONFIRMED)
        self.assertTrue(Notification.objects.filter(student=self.student_profile, title__icontains='Admission').exists())

    def test_application_accept_action(self):
        url = reverse('university_admin:application_accept_action', kwargs={'application_uuid': self.applicant.pk})
        response = self.client.post(url, {
            'admission_notes': 'Merit confirmed. Welcome to PIST CS class of 2026.',
            'confirm_acceptance': True,
        })
        self.assertEqual(response.status_code, 302)
        self.applicant.refresh_from_db()
        self.assertEqual(self.applicant.application_status, PISTApplicant.ApplicationStatus.ACCEPTED)
        self.assertEqual(self.applicant.status, PISTApplicant.Status.ADMISSION_CONFIRMED)
        notif = Notification.objects.filter(student=self.student_profile, title='Admission Offer Granted!').first()
        self.assertIsNotNone(notif)
        self.assertIn('Welcome to PIST CS class of 2026', notif.message)

    def test_application_reject_action(self):
        url = reverse('university_admin:application_reject_action', kwargs={'application_uuid': self.applicant.pk})
        response = self.client.post(url, {
            'rejection_reason': 'FSc pre-medical background without additional mathematics requirement.',
        })
        self.assertEqual(response.status_code, 302)
        self.applicant.refresh_from_db()
        self.assertEqual(self.applicant.application_status, PISTApplicant.ApplicationStatus.REJECTED)
        self.assertEqual(self.applicant.status, PISTApplicant.Status.REJECTED)
        notif = Notification.objects.filter(student=self.student_profile, title__icontains='Application Status Update').first()
        self.assertIsNotNone(notif)
        self.assertIn('additional mathematics requirement', notif.message)

    def test_application_schedule_action(self):
        url = reverse('university_admin:application_schedule_action', kwargs={'application_uuid': self.applicant.pk})
        response = self.client.post(url, {
            'test_session': str(self.test_session.pk),
        })
        self.assertEqual(response.status_code, 302)
        self.applicant.refresh_from_db()
        self.assertEqual(self.applicant.application_status, PISTApplicant.ApplicationStatus.SCHEDULED)
        self.assertEqual(self.applicant.status, PISTApplicant.Status.ROLL_ISSUED)
        self.assertIsNotNone(self.applicant.roll_number)
        self.assertEqual(self.applicant.test_session, self.test_session)
        notif = Notification.objects.filter(student=self.student_profile, title__icontains='Entry Test Scheduled').first()
        self.assertIsNotNone(notif)
        self.assertIn(self.applicant.roll_number, notif.message)

    def test_students_directory_and_detail(self):
        list_url = reverse('university_admin:students_list')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Students Directory')
        self.assertContains(response, 'Zainab Tariq')

        detail_url = reverse('university_admin:student_detail', kwargs={'student_id': self.student_profile.pk})
        detail_res = self.client.get(detail_url)
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, 'Student Dossier')
        self.assertContains(detail_res, self.student_profile.student_id)

        # Test sending direct notification
        post_res = self.client.post(detail_url, {
            'send_student_note': '1',
            'title': 'Interview Call for Merit Scholarship',
            'message': 'Please report to the scholarship committee on Friday at 11 AM.',
        })
        self.assertEqual(post_res.status_code, 302)
        self.assertTrue(Notification.objects.filter(student=self.student_profile, title='Interview Call for Merit Scholarship').exists())

    def test_documents_queue_and_review(self):
        url = reverse('university_admin:documents_queue')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Document Queue')
        self.assertContains(response, 'matric.pdf')

        review_url = reverse('university_admin:document_review_action', kwargs={'document_id': self.document.pk})
        post_res = self.client.post(review_url, {'action': 'approve'})
        self.assertEqual(post_res.status_code, 302)
        self.document.refresh_from_db()
        self.assertEqual(self.document.verification_status, AcademicDocument.VerificationStatus.VERIFIED)

    def test_programs_and_toggle(self):
        programs_url = reverse('university_admin:programs')
        res = self.client.get(programs_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'BS Computer Science')

        toggle_url = reverse('university_admin:program_toggle', kwargs={'program_id': self.program.pk})
        post_res = self.client.post(toggle_url)
        self.assertEqual(post_res.status_code, 302)
        self.program.refresh_from_db()
        self.assertFalse(self.program.admissions_open)

    def test_test_sessions_management(self):
        sessions_url = reverse('university_admin:test_sessions')
        res = self.client.get(sessions_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Configured Test Sessions')

        # Toggle session active
        toggle_url = reverse('university_admin:test_session_toggle', kwargs={'session_id': self.test_session.pk})
        post_res = self.client.post(toggle_url)
        self.assertEqual(post_res.status_code, 302)
        self.test_session.refresh_from_db()
        self.assertFalse(self.test_session.is_active)

    def test_broadcast_notifications(self):
        url = reverse('university_admin:notifications')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Compose Broadcast')

        # Send broadcast to all students
        post_res = self.client.post(url, {
            'target_audience': 'all',
            'title': 'General Campus Announcement',
            'message': 'Fall 2026 orientation ceremonies will commence next Monday.',
        })
        self.assertEqual(post_res.status_code, 302)
        self.assertTrue(Notification.objects.filter(student=self.student_profile, title='General Campus Announcement').exists())

    def test_institutional_reports(self):
        reports_url = reverse('university_admin:reports')
        res = self.client.get(reports_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Institutional Admissions &amp; Enrollment Reports')
        self.assertContains(res, 'Overall Acceptance Rate')
        self.assertContains(res, 'Admissions Intake by Academic Department')

