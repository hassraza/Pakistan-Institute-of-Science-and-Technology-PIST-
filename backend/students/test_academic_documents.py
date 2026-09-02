from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import AcademicDocument, StudentProfile
from .services import generate_student_id


class AcademicDocumentTests(TestCase):
    def setUp(self):
        self.student = self.make_student('docs@example.com', '12345-1234567-1')
        self.other = self.make_student('other-docs@example.com', '12345-1234567-2')
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin@pist.edu.pk',
            email='admin@pist.edu.pk',
            password='AdminPass!123',
        )
        self.client.force_login(self.student.user)

    def make_student(self, email, cnic):
        user = get_user_model().objects.create_user(username=email, email=email, password='AyeshaStrong!29')
        return StudentProfile.objects.create(user=user, student_id=generate_student_id(), full_name='Document Student', cnic=cnic, date_of_birth='2000-01-15', phone='03001234567')

    @staticmethod
    def pdf(name='result.pdf', content=b'%PDF-1.7 test document'):
        return SimpleUploadedFile(name, content, content_type='application/pdf')

    @staticmethod
    def image(name='result.png'):
        stream = BytesIO()
        Image.new('RGB', (10, 10), 'green').save(stream, format='PNG')
        return SimpleUploadedFile(name, stream.getvalue(), content_type='image/png')

    def upload(self, document_type='MATRIC', file=None):
        return self.client.post(reverse('students:document_upload'), {'document_type': document_type, 'file': file or self.pdf()})

    def test_document_endpoints_require_login(self):
        self.client.logout()
        response = self.client.get(reverse('students:documents'))
        self.assertRedirects(response, reverse('students:login') + '?next=/student/documents/')
        self.assertEqual(self.client.post(reverse('students:document_upload'), {}).status_code, 302)
        self.client.force_login(self.student.user)
        document = AcademicDocument.objects.create(student=self.student, document_type='MATRIC', file=self.pdf(), file_name='result.pdf')
        self.client.logout()
        self.assertEqual(self.client.get(reverse('students:document_view', kwargs={'doc_id': document.pk})).status_code, 302)
        self.assertEqual(self.client.get(reverse('students:document_replace', kwargs={'doc_id': document.pk})).status_code, 302)
        self.assertEqual(self.client.get(reverse('students:document_delete', kwargs={'doc_id': document.pk})).status_code, 302)

    def test_upload_success_and_dashboard_summary(self):
        response = self.upload()
        self.assertRedirects(response, reverse('students:documents'))
        document = AcademicDocument.objects.get()
        self.assertEqual(document.student, self.student)
        self.assertEqual(document.verification_status, AcademicDocument.VerificationStatus.PENDING)
        self.assertEqual(document.file_name, 'result.pdf')
        self.assertContains(self.client.get(reverse('students:dashboard')), '1 / 5')

    def test_invalid_and_oversized_files_are_rejected(self):
        invalid = self.upload(file=SimpleUploadedFile('result.pdf', b'not a pdf', content_type='application/pdf'))
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(AcademicDocument.objects.count(), 0)
        invalid_extension = self.upload(file=SimpleUploadedFile('result.exe', b'MZ-not-allowed', content_type='application/octet-stream'))
        self.assertEqual(invalid_extension.status_code, 200)
        self.assertEqual(AcademicDocument.objects.count(), 0)
        oversized = self.upload(file=SimpleUploadedFile('large.pdf', b'%PDF' + b'x' * (5 * 1024 * 1024 + 1), content_type='application/pdf'))
        self.assertEqual(oversized.status_code, 200)
        self.assertContains(oversized, 'maximum size of 5 MB')
        self.assertEqual(AcademicDocument.objects.count(), 0)

    def test_cross_student_view_replace_and_delete_are_denied(self):
        self.client.force_login(self.other.user)
        self.upload()
        document = AcademicDocument.objects.get()
        self.client.force_login(self.student.user)
        self.assertEqual(self.client.get(reverse('students:document_view', kwargs={'doc_id': document.pk})).status_code, 404)
        self.assertEqual(self.client.get(reverse('students:document_replace', kwargs={'doc_id': document.pk})).status_code, 404)
        self.assertEqual(self.client.get(reverse('students:document_delete', kwargs={'doc_id': document.pk})).status_code, 404)
        self.assertEqual(AcademicDocument.objects.count(), 1)

    def test_replace_resets_verified_status_and_clears_rejection_reason(self):
        self.upload()
        document = AcademicDocument.objects.get()
        document.verification_status = AcademicDocument.VerificationStatus.REJECTED
        document.rejection_reason = 'Blurry image'
        document.save()
        response = self.client.post(reverse('students:document_replace', kwargs={'doc_id': document.pk}), {'file': self.image('replacement.png')})
        self.assertRedirects(response, reverse('students:documents'))
        document.refresh_from_db()
        self.assertEqual(document.verification_status, AcademicDocument.VerificationStatus.PENDING)
        self.assertEqual(document.file_name, 'replacement.png')
        self.assertEqual(document.rejection_reason, '')

    def test_delete_requires_confirmation_then_removes_document(self):
        self.upload()
        document = AcademicDocument.objects.get()
        confirmation = self.client.get(reverse('students:document_delete', kwargs={'doc_id': document.pk}))
        self.assertContains(confirmation, 'Are you sure')
        self.assertRedirects(self.client.post(reverse('students:document_delete', kwargs={'doc_id': document.pk})), reverse('students:documents'))
        self.assertFalse(AcademicDocument.objects.exists())

    def test_documents_page_shows_clear_status_and_preview_modal(self):
        self.upload()
        response = self.client.get(reverse('students:documents'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Upload Confirmed')
        self.assertContains(response, 'Uploaded — Under Review')
        self.assertContains(response, 'id="doc-preview-modal"')
        self.assertContains(response, 'openDocPreview')

    def test_gated_view_streams_own_file_inline(self):
        self.upload()
        document = AcademicDocument.objects.get()
        response = self.client.get(reverse('students:document_view', kwargs={'doc_id': document.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.7 test document')
        self.assertEqual(response.headers.get('Content-Type'), 'application/pdf')
        self.assertIn('inline', response.headers.get('Content-Disposition', ''))

    def test_admin_can_approve_and_reject_documents(self):
        self.upload()
        document = AcademicDocument.objects.get()
        
        # Staff user logs in to admin
        self.client.force_login(self.admin_user)
        
        # Admin views document
        view_response = self.client.get(reverse('students:document_view', kwargs={'doc_id': document.pk}))
        self.assertEqual(view_response.status_code, 200)
        
        # Admin approves document
        approve_url = reverse('university_admin:document_review_action', kwargs={'document_id': document.pk})
        approve_response = self.client.post(approve_url, {'action': 'approve'})
        self.assertEqual(approve_response.status_code, 302)
        document.refresh_from_db()
        self.assertEqual(document.verification_status, AcademicDocument.VerificationStatus.VERIFIED)
        self.assertEqual(document.reviewed_by, self.admin_user)
        self.assertIsNotNone(document.reviewed_at)

        # Admin rejects document with reason
        reject_response = self.client.post(approve_url, {'action': 'reject', 'rejection_reason': 'Blurry photograph'})
        self.assertEqual(reject_response.status_code, 302)
        document.refresh_from_db()
        self.assertEqual(document.verification_status, AcademicDocument.VerificationStatus.REJECTED)
        self.assertEqual(document.rejection_reason, 'Blurry photograph')

        # Check student portal view reflects rejected status and reason
        self.client.force_login(self.student.user)
        portal_response = self.client.get(reverse('students:documents'))
        self.assertContains(portal_response, 'Needs Re-upload')
        self.assertContains(portal_response, 'Blurry photograph')
