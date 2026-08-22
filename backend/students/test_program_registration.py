from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from admissions.models import Campus, Department, Program, ProgramEligibility, Qualification, TestCenter, TestType, ProgramTestRequirement
from students.models import AcademicDocument, StudentProfile


class ProgramRegistrationTests(TestCase):
    def setUp(self):
        self.campus = Campus.objects.create(name='PIST Islamabad Campus', city='Islamabad', code='ISB', address='H-12')
        self.department = Department.objects.create(campus=self.campus, code='CS', name='Department of Computer Science', slug='cs')
        self.program = Program.objects.create(
            department=self.department, campus=self.campus, name='Bachelor of Science in Computer Science',
            code='BSCS-ISB', slug='bscs-isb', admissions_open=True, application_deadline=timezone.localdate() + timedelta(days=10),
            duration='4 Years', degree_level='Undergraduate', eligibility_percentage=60,
        )
        self.qualification = Qualification.objects.create(name='Intermediate in Computer Science (FSc ICS)')
        ProgramEligibility.objects.create(program=self.program, qualification=self.qualification, minimum_percentage=60)
        self.test_type = TestType.objects.create(name='PIST University Entry Test')
        ProgramTestRequirement.objects.create(program=self.program, test_type=self.test_type)
        self.center = TestCenter.objects.create(campus=self.campus, name='Test Center', address='H-12', building='A', hall='1', capacity=10)
        from admissions.models import TestSession
        TestSession.objects.create(test_center=self.center, program=self.program, test_date=timezone.localdate() + timedelta(days=10), available_seats=10)
        self.student = self.make_student('a@example.com', '12345-1234567-1', 'Student A')
        self.other = self.make_student('b@example.com', '12345-1234567-2', 'Student B')
        self.client.force_login(self.student.user)
        self.upload_required_documents(self.student)

    def make_student(self, email, cnic, name):
        user = get_user_model().objects.create_user(username=email, email=email, password='AyeshaStrong!29')
        return StudentProfile.objects.create(user=user, student_id=f'PIST-STU-{email[0].upper()}-0001', full_name=name, cnic=cnic, date_of_birth='2000-01-15', phone='03001234567', address='Islamabad')

    def upload_required_documents(self, student):
        for document_type, _label in AcademicDocument.DocumentType.choices:
            AcademicDocument.objects.create(student=student, document_type=document_type, file=SimpleUploadedFile(f'{document_type}.pdf', b'%PDF-1.7 test'), file_name=f'{document_type}.pdf')

    def application_data(self):
        return {'qualification': str(self.qualification.pk), 'percentage': '75'}

    def test_anonymous_registration_and_registered_programs_require_login(self):
        self.client.logout()
        response = self.client.get(reverse('students:apply_program', kwargs={'program_slug': self.program.slug}))
        self.assertRedirects(response, reverse('students:login') + f'?next=/student/programs/{self.program.slug}/apply/')
        response = self.client.get(reverse('students:registered_programs'))
        self.assertRedirects(response, reverse('students:login') + '?next=/student/registered-programs/')

    def test_application_review_then_submission_generates_all_identifiers(self):
        review = self.client.post(reverse('students:apply_program', kwargs={'program_slug': self.program.slug}), self.application_data())
        self.assertEqual(review.status_code, 200)
        self.assertContains(review, 'Review before submitting')
        submission = self.client.post(reverse('students:submit_program_application', kwargs={'program_slug': self.program.slug}), {**self.application_data(), 'confirm': '1'})
        self.assertEqual(submission.status_code, 200)
        application = self.student.program_applications.get()
        self.assertEqual(application.application_status, 'SUBMITTED')
        self.assertEqual(application.student, self.student)
        self.assertEqual(application.program, self.program)
        self.assertRegex(application.application_id, r'^APP-2026-[A-F0-9]+$')
        self.assertRegex(application.program_registration_id, r'^CS26-\d{4}$')
        self.assertTrue(application.roll_number)
        self.assertContains(submission, 'Application ID')
        self.assertContains(submission, 'Program Registration ID')
        self.assertContains(submission, 'Roll Number')

    def test_registered_program_and_roll_slip_are_student_scoped(self):
        self.submit_application()
        application = self.student.program_applications.get()
        listing = self.client.get(reverse('students:registered_programs'))
        self.assertContains(listing, application.program_registration_id)
        self.assertContains(listing, application.application_id)
        self.assertContains(listing, application.roll_number)
        self.client.force_login(self.other.user)
        self.assertNotContains(self.client.get(reverse('students:registered_programs')), application.program_registration_id)
        self.assertEqual(self.client.get(reverse('students:application_detail', kwargs={'application_uuid': application.pk})).status_code, 404)
        self.assertEqual(self.client.get(reverse('students:application_roll_slip', kwargs={'application_uuid': application.pk})).status_code, 404)

    def submit_application(self):
        self.client.post(reverse('students:apply_program', kwargs={'program_slug': self.program.slug}), self.application_data())
        return self.client.post(reverse('students:submit_program_application', kwargs={'program_slug': self.program.slug}), {**self.application_data(), 'confirm': '1'})

    def test_duplicate_application_is_rejected(self):
        self.submit_application()
        response = self.client.post(reverse('students:submit_program_application', kwargs={'program_slug': self.program.slug}), {**self.application_data(), 'confirm': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already have an active application')
        self.assertEqual(self.student.program_applications.count(), 1)

    def test_closed_program_is_rejected(self):
        self.program.admissions_open = False
        self.program.save(update_fields=['admissions_open'])
        response = self.client.post(reverse('students:apply_program', kwargs={'program_slug': self.program.slug}), self.application_data())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admissions are closed')
        self.assertFalse(self.student.program_applications.exists())

    def test_missing_documents_and_ineligible_result_are_rejected(self):
        AcademicDocument.objects.filter(student=self.student).delete()
        response = self.client.post(reverse('students:apply_program', kwargs={'program_slug': self.program.slug}), self.application_data())
        self.assertContains(response, 'Upload all five required academic documents')
        self.upload_required_documents(self.student)
        response = self.client.post(reverse('students:apply_program', kwargs={'program_slug': self.program.slug}), {'qualification': str(self.qualification.pk), 'percentage': '40'})
        self.assertContains(response, 'does not meet this requirement')
        self.assertFalse(self.student.program_applications.exists())

    def test_department_registration_ids_have_independent_sequences(self):
        self.submit_application()
        self.assertTrue(self.student.program_applications.get().program_registration_id.endswith('-0001'))
        other_department = Department.objects.create(campus=self.campus, code='AI', name='Department of Artificial Intelligence', slug='ai')
        other_program = Program.objects.create(department=other_department, campus=self.campus, name='Bachelor of Science in Artificial Intelligence', code='BSAI-ISB', slug='bsai-isb', admissions_open=True, application_deadline=timezone.localdate() + timedelta(days=10), degree_level='Undergraduate')
        ProgramEligibility.objects.create(program=other_program, qualification=self.qualification, minimum_percentage=60)
        self.client.force_login(self.other.user)
        self.upload_required_documents(self.other)
        response = self.client.post(reverse('students:apply_program', kwargs={'program_slug': other_program.slug}), self.application_data())
        self.assertContains(response, 'Review before submitting')
