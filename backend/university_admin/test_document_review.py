from io import BytesIO
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from admissions.models import Campus, Department, Program, PISTApplicant
from students.models import AcademicDocument, StudentProfile
from students.services import generate_student_id


class UniversityAdminDocumentReviewTests(TestCase):
    def setUp(self):
        self.staff_user = get_user_model().objects.create_user(
            username='officer@pist.edu.pk',
            email='officer@pist.edu.pk',
            password='StaffSecurePass!123',
            is_staff=True,
        )
        self.student_user = get_user_model().objects.create_user(
            username='applicant@example.com',
            email='applicant@example.com',
            password='StudentPass!123',
        )
        self.profile = StudentProfile.objects.create(
            user=self.student_user,
            student_id=generate_student_id(),
            full_name='Ali Ahmed',
            cnic='35201-1234567-1',
            date_of_birth='2002-04-12',
            phone='03001234567',
        )
        self.campus = Campus.objects.create(code='ISB', name='Islamabad Main Campus', city='Islamabad')
        self.department = Department.objects.create(campus=self.campus, code='CS', name='Computer Science')
        self.program = Program.objects.create(department=self.department, code='BSCS', name='BS Computer Science', degree_level='Undergraduate')
        self.applicant = PISTApplicant.objects.create(
            student=self.profile,
            program=self.program,
            campus=self.campus,
            full_name='Ali Ahmed',
            cnic='35201-1234567-1',
            email='applicant@example.com',
            phone='03001234567',
            matric_marks=900,
            matric_total=1100,
            fsc_marks=950,
            fsc_total=1100,
        )
        self.document = AcademicDocument.objects.create(
            student=self.profile,
            document_type=AcademicDocument.DocumentType.MATRIC_RESULT,
            file=SimpleUploadedFile('matric_cert.pdf', b'%PDF-1.7 sample data', content_type='application/pdf'),
            file_name='matric_cert.pdf',
        )
        self.client.force_login(self.staff_user)

    def test_application_detail_displays_uploaded_documents(self):
        url = reverse('university_admin:application_detail', kwargs={'application_uuid': self.applicant.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Uploaded Academic Documents')
        self.assertContains(response, 'Matric Certificate/Result')
        self.assertContains(response, 'matric_cert.pdf')
        self.assertContains(response, 'Pending Review')
        self.assertContains(response, 'Approve Document')
        self.assertContains(response, 'Reject / Request Resubmission')

    def test_document_approval_action(self):
        url = reverse('university_admin:document_review_action', kwargs={'document_id': self.document.pk})
        response = self.client.post(url, {'action': 'approve'})
        self.assertEqual(response.status_code, 302)
        self.document.refresh_from_db()
        self.assertEqual(self.document.verification_status, AcademicDocument.VerificationStatus.VERIFIED)
        self.assertEqual(self.document.reviewed_by, self.staff_user)
        self.assertIsNotNone(self.document.reviewed_at)
        self.assertEqual(self.document.rejection_reason, '')

    def test_document_rejection_action_with_feedback(self):
        url = reverse('university_admin:document_review_action', kwargs={'document_id': self.document.pk})
        response = self.client.post(url, {
            'action': 'reject',
            'rejection_reason': 'The uploaded certificate is blurry and missing the official controller seal.',
        })
        self.assertEqual(response.status_code, 302)
        self.document.refresh_from_db()
        self.assertEqual(self.document.verification_status, AcademicDocument.VerificationStatus.REJECTED)
        self.assertEqual(self.document.reviewed_by, self.staff_user)
        self.assertEqual(
            self.document.rejection_reason,
            'The uploaded certificate is blurry and missing the official controller seal.',
        )

    def test_non_staff_cannot_access_review_endpoint(self):
        self.client.force_login(self.student_user)
        url = reverse('university_admin:document_review_action', kwargs={'document_id': self.document.pk})
        response = self.client.post(url, {'action': 'approve'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/university-admin/login/', response.url)
