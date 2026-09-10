import io
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from admissions.models import Campus, Department, Program, PISTApplicant, RollSlip
from students.models import StudentProfile, AcademicDocument


@override_settings(PIST_EXTERNAL_API_KEY='test-secret-key-2026')
class PISTIntegrationAPITests(TestCase):
    def setUp(self):
        self.api_key = 'test-secret-key-2026'
        self.headers = {'HTTP_X_API_KEY': self.api_key}

        self.campus = Campus.objects.create(name='PIST Main', city='Islamabad', code='ISB', address='H-12')
        self.dept = Department.objects.create(campus=self.campus, code='CS', name='Computer Science', slug='cs')
        self.prog = Program.objects.create(
            department=self.dept, campus=self.campus, name='BS Computer Science', code='BSCS-ISB', slug='bscs-isb'
        )

    def test_student_create_and_duplicate(self):
        url = reverse('integration:student_create')
        payload = {
            'first_name': 'Ali',
            'last_name': 'Khan',
            'email': 'ali@gmail.com',
            'phone': '03001234567',
            'cnic': '12345-1234567-1',
            'city': 'Islamabad',
            'gender': 'male',
        }
        res = self.client.post(url, payload, content_type='application/json', **self.headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn('student_id', data)
        self.assertIn('username', data)
        self.assertIn('password', data)

        # Duplicate call returns 409 with existing info
        res2 = self.client.post(url, payload, content_type='application/json', **self.headers)
        self.assertEqual(res2.status_code, 409)

    def test_document_upload_photo_and_academic(self):
        # Create student first
        student_res = self.client.post(
            reverse('integration:student_create'),
            {
                'full_name': 'Sara Ahmed',
                'email': 'sara@gmail.com',
                'phone': '03009876543',
                'cnic': '42101-1234567-3',
            },
            content_type='application/json',
            **self.headers,
        )
        self.assertEqual(student_res.status_code, 201)
        student_id = student_res.json()['student_id']

        # 1. Upload Profile Photo
        img_buffer = io.BytesIO()
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(img_buffer, format='JPEG')
        img_buffer.seek(0)
        photo_file = SimpleUploadedFile('photo.jpg', img_buffer.read(), content_type='image/jpeg')

        upload_url = reverse('integration:document_upload')
        photo_res = self.client.post(
            upload_url,
            {
                'student_id': student_id,
                'document_type': 'PHOTO',
                'file': photo_file,
            },
            **self.headers,
        )
        self.assertEqual(photo_res.status_code, 201)
        self.assertTrue(photo_res.json()['success'])

        # 2. Upload Academic Document (PDF)
        pdf_content = b'%PDF-1.4 test pdf content'
        pdf_file = SimpleUploadedFile('matric.pdf', pdf_content, content_type='application/pdf')

        doc_res = self.client.post(
            upload_url,
            {
                'student_id': student_id,
                'document_type': 'MATRIC',
                'file': pdf_file,
            },
            **self.headers,
        )
        self.assertEqual(doc_res.status_code, 201)
        self.assertTrue(doc_res.json()['success'])

        # Verify in DB
        profile = StudentProfile.objects.get(student_id=student_id)
        self.assertTrue(bool(profile.profile_photo))
        self.assertTrue(profile.academic_documents.filter(document_type=AcademicDocument.DocumentType.MATRIC_RESULT).exists())

    def test_roll_slip_api_returns_slip_url(self):
        user = get_user_model().objects.create_user(username='slipuser', email='slip@example.com')
        profile = StudentProfile.objects.create(
            user=user, full_name='Slip Student', cnic='12345-9876543-1', phone='03001122334', student_id='PIST-STU-9999'
        )
        app = PISTApplicant.objects.create(
            student=profile, application_id='APP-9999', full_name=profile.full_name,
            cnic=profile.cnic, email=user.email, phone=profile.phone,
            campus=self.campus, program=self.prog, roll_number='PIST-CS-9999',
            test_date='2026-09-30', test_venue='Hall A',
        )
        RollSlip.objects.create(application=app, roll_number='PIST-CS-9999')

        url = reverse('integration:roll_slip', kwargs={'application_id': 'APP-9999'})
        res = self.client.get(url, **self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['roll_number'], 'PIST-CS-9999')
        self.assertIn('slip_url', data)
        self.assertIn(f'/admissions/roll-slip/{app.id}/', data['slip_url'])
