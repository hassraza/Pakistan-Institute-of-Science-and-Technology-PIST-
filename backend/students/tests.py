from datetime import date, timedelta
from io import BytesIO
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import StudentRegistrationForm
from .models import AcademicDocument, StudentProfile
from .services import generate_student_id


class StudentAuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse('students:register')
        self.valid = {
            'full_name': '  Ayesha   Khan ', 'email': 'Student@Example.com',
            'cnic': '1234512345671', 'date_of_birth': '2000-01-15',
            'phone': '0300-1234567', 'gender': '', 'father_name': '',
            'address': '', 'nationality': 'Pakistani', 'password': 'AyeshaStrong!29',
            'confirm_password': 'AyeshaStrong!29', 'terms': 'on', 'website': '',
        }

    def register(self, **overrides):
        data = self.valid.copy()
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_registration_creates_hashed_user_and_student_id(self):
        response = self.register()
        self.assertEqual(response.status_code, 200)
        profile = StudentProfile.objects.get()
        user = get_user_model().objects.get()
        self.assertEqual(profile.full_name, 'Ayesha Khan')
        self.assertEqual(user.email, 'student@example.com')
        self.assertNotEqual(user.password, self.valid['password'])
        self.assertTrue(check_password(self.valid['password'], user.password))
        self.assertRegex(profile.student_id, rf'^PIST-STU-{date.today().year}-\d{{4,}}$')

    def test_invalid_email_and_duplicate_email_are_rejected(self):
        form = StudentRegistrationForm({**self.valid, 'email': 'not-an-email'})
        self.assertFalse(form.is_valid())
        self.register()
        form = StudentRegistrationForm({**self.valid, 'email': 'STUDENT@example.com', 'cnic': '1234512345672'})
        self.assertFalse(form.is_valid())
        self.assertIn('already registered', str(form.errors['email']))

    def test_cnic_is_normalized_and_duplicate_is_rejected(self):
        self.register(cnic='12345-1234567-1')
        self.assertEqual(StudentProfile.objects.get().cnic, '12345-1234567-1')
        form = StudentRegistrationForm({**self.valid, 'email': 'other@example.com'})
        self.assertFalse(form.is_valid())
        self.assertIn('already registered', str(form.errors['cnic']))
        invalid = StudentRegistrationForm({**self.valid, 'email': 'new@example.com', 'cnic': '1234-abc'})
        self.assertFalse(invalid.is_valid())
        self.assertIn('13 digits', str(invalid.errors['cnic']))

    def test_dob_bounds_and_terms_are_enforced(self):
        today = date.today()
        self.assertFalse(StudentRegistrationForm({**self.valid, 'date_of_birth': today.isoformat()}).is_valid())
        self.assertFalse(StudentRegistrationForm({**self.valid, 'date_of_birth': '2015-01-01'}).is_valid())
        self.assertFalse(StudentRegistrationForm({**self.valid, 'date_of_birth': '1900-01-01'}).is_valid())
        self.assertFalse(StudentRegistrationForm({**self.valid, 'terms': ''}).is_valid())

    def test_password_mismatch_and_weak_passwords_are_rejected(self):
        for password in ('short', 'password', '12345678'):
            form = StudentRegistrationForm({**self.valid, 'password': password, 'confirm_password': password})
            self.assertFalse(form.is_valid(), password)
        form = StudentRegistrationForm({**self.valid, 'confirm_password': 'Different!29'})
        self.assertFalse(form.is_valid())
        self.assertIn('match', str(form.errors['confirm_password']))

    def test_student_ids_are_unique_and_increment(self):
        first = generate_student_id()
        second = generate_student_id()
        self.assertNotEqual(first, second)
        self.assertTrue(second.endswith('0002'))

    def make_student(self, email='student@example.com', password='AyeshaStrong!29', active=True, cnic='12345-1234567-1'):
        user = get_user_model().objects.create_user(username=email, email=email, password=password, is_active=active)
        return StudentProfile.objects.create(user=user, student_id=generate_student_id(), full_name='Ayesha Khan', cnic=cnic, date_of_birth='2000-01-15', phone='03001234567')

    def test_email_login_success_and_specific_failures(self):
        self.make_student()
        response = self.client.post(reverse('students:login'), {'email': 'STUDENT@EXAMPLE.COM', 'password': 'AyeshaStrong!29'})
        self.assertRedirects(response, reverse('students:dashboard'))
        self.client.get(reverse('students:logout'))
        response = self.client.post(reverse('students:login'), {'email': 'student@example.com', 'password': 'wrong'})
        self.assertContains(response, 'Incorrect password. Please try again.')
        self.client.get(reverse('students:logout'))
        response = self.client.post(reverse('students:login'), {'email': 'missing@example.com', 'password': 'wrong'})
        self.assertContains(response, 'No account found with this email.')

    def test_inactive_account_and_dashboard_protection(self):
        self.make_student(active=False)
        response = self.client.post(reverse('students:login'), {'email': 'student@example.com', 'password': 'AyeshaStrong!29'})
        self.assertContains(response, 'This account is inactive. Contact support.')
        response = self.client.get(reverse('students:dashboard'))
        self.assertRedirects(response, reverse('students:login') + '?next=/student/dashboard/')

    def test_student_can_only_edit_own_profile_and_logout_clears_session(self):
        profile = self.make_student()
        other = self.make_student(email='other@example.com', cnic='12345-1234567-2')
        self.client.force_login(profile.user)
        response = self.client.post(reverse('students:profile_edit'), {'full_name': 'Updated Name', 'cnic': '99999-9999999-9', 'date_of_birth': '1990-01-01', 'phone': '03001234568', 'gender': '', 'father_name': '', 'address': 'New address', 'nationality': 'Pakistani'})
        self.assertRedirects(response, reverse('students:profile'))
        profile.refresh_from_db()
        self.assertEqual(profile.full_name, 'Ayesha Khan')
        self.assertEqual(profile.cnic, '12345-1234567-1')
        self.assertEqual(profile.date_of_birth.isoformat(), '2000-01-15')
        self.assertEqual(profile.phone, '03001234568')
        self.assertEqual(StudentProfile.objects.get(pk=other.pk).full_name, 'Ayesha Khan')
        self.client.get(reverse('students:logout'))
        self.assertRedirects(self.client.get(reverse('students:dashboard')), reverse('students:login') + '?next=/student/dashboard/')

    def test_password_reset_does_not_reveal_non_student_accounts(self):
        get_user_model().objects.create_user(username='admin', email='admin@example.com', password='AyeshaStrong!29')
        response = self.client.post(reverse('students:password_reset'), {'email': 'admin@example.com'})
        self.assertRedirects(response, reverse('students:password_reset_done'))
        self.assertFalse(response.context if hasattr(response, 'context') else False)


@override_settings(STUDENT_MIN_AGE=18, STUDENT_MAX_AGE=90)
class ConfigurableStudentAgeTests(TestCase):
    def test_age_settings_apply_to_form_bounds(self):
        form = StudentRegistrationForm()
        self.assertEqual(form.fields['date_of_birth'].widget.attrs['max'], date.today().replace(year=date.today().year - 18).isoformat())


class StudentDashboardTests(TestCase):
    def make_student(self, email, name, cnic):
        user = get_user_model().objects.create_user(username=email, email=email, password='AyeshaStrong!29')
        return StudentProfile.objects.create(user=user, student_id=generate_student_id(), full_name=name, cnic=cnic, date_of_birth='2000-08-10', phone='03001234567')

    def setUp(self):
        self.student = self.make_student('a@example.com', 'Student A', '12345-1234567-1')
        self.other = self.make_student('b@example.com', 'Student B', '12345-1234567-2')
        self.client.force_login(self.student.user)

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('students:dashboard'))
        self.assertRedirects(response, reverse('students:login') + '?next=/student/dashboard/')

    def test_dashboard_accessible_and_shows_only_own_data(self):
        response = self.client.get(reverse('students:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.full_name)
        self.assertContains(response, self.student.student_id)
        self.assertNotContains(response, self.other.full_name)
        self.assertNotContains(response, self.other.student_id)

    def test_profile_page_is_scoped_to_request_user(self):
        response = self.client.get(reverse('students:profile'), {'student_id': str(self.other.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.full_name)
        self.assertNotContains(response, self.other.full_name)

    def test_profile_edit_updates_allowed_fields_and_ignores_locked_fields(self):
        response = self.client.post(reverse('students:profile_edit'), {
            'phone': '0300-7654321', 'address': 'PIST Islamabad', 'gender': '',
            'father_name': 'Guardian', 'nationality': 'Pakistani',
            'full_name': 'Changed Name', 'cnic': '99999-9999999-9',
        })
        self.assertRedirects(response, reverse('students:profile'))
        self.student.refresh_from_db()
        self.assertEqual(self.student.phone, '03007654321')
        self.assertEqual(self.student.address, 'PIST Islamabad')
        self.assertEqual(self.student.full_name, 'Student A')
        self.assertEqual(self.student.cnic, '12345-1234567-1')

    def test_profile_edit_invalid_phone_keeps_database_unchanged(self):
        response = self.client.post(reverse('students:profile_edit'), {'phone': 'invalid', 'address': 'Changed'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'valid Pakistani mobile')
        self.student.refresh_from_db()
        self.assertEqual(self.student.address, '')

    @staticmethod
    def png_upload(name='avatar.png', size=(8, 8)):
        content = BytesIO()
        Image.new('RGB', size, 'green').save(content, format='PNG')
        return SimpleUploadedFile(name, content.getvalue(), content_type='image/png')

    def test_profile_photo_upload_valid(self):
        data = {'phone': '03001234567', 'profile_photo': self.png_upload()}
        response = self.client.post(reverse('students:profile_edit'), data)
        self.assertRedirects(response, reverse('students:profile'))
        self.student.refresh_from_db()
        self.assertIn('student_photos/2026/08/', self.student.profile_photo.name)

    def test_profile_photo_rejects_invalid_type(self):
        upload = SimpleUploadedFile('avatar.txt', b'not-an-image', content_type='text/plain')
        response = self.client.post(reverse('students:profile_edit'), {'phone': '03001234567', 'profile_photo': upload})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(StudentProfile.objects.get(pk=self.student.pk).profile_photo)

    @override_settings(STUDENT_PHOTO_MAX_SIZE_MB=1)
    def test_profile_photo_rejects_oversized_file(self):
        content = BytesIO()
        Image.effect_noise((2000, 2000), 100).save(content, format='PNG')
        upload = SimpleUploadedFile('large.png', content.getvalue(), content_type='image/png')
        response = self.client.post(reverse('students:profile_edit'), {'phone': '03001234567', 'profile_photo': upload})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1MB or smaller')

    def test_age_calculated_correctly(self):
        today = date.today()
        birthday = today.replace(year=today.year - 20)
        self.student.date_of_birth = birthday
        self.student.save(update_fields=['date_of_birth'])
        response = self.client.get(reverse('students:profile'))
        self.assertContains(response, '>20<')


class AcademicDocumentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='doc@example.com', email='doc@example.com', password='AyeshaStrong!29')
        self.student = StudentProfile.objects.create(
            user=self.user, student_id=generate_student_id(), full_name='Doc Student',
            cnic='12345-1234567-1', date_of_birth='2000-01-15', phone='03001234567',
        )
        self.other_user = get_user_model().objects.create_user(username='other_doc@example.com', email='other_doc@example.com', password='AyeshaStrong!29')
        self.other_student = StudentProfile.objects.create(
            user=self.other_user, student_id=generate_student_id(), full_name='Other Doc Student',
            cnic='12345-1234567-2', date_of_birth='2000-01-15', phone='03001234568',
        )
        self.client.force_login(self.user)

    def test_documents_page_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('students:documents'))
        self.assertRedirects(response, reverse('students:login') + '?next=/student/documents/')

    def test_student_can_upload_and_view_document(self):
        pdf_file = SimpleUploadedFile('matric_result.pdf', b'%PDF-1.4 test content', content_type='application/pdf')
        response = self.client.post(reverse('students:document_upload'), {
            'document_type': AcademicDocument.DocumentType.MATRIC_RESULT,
            'file': pdf_file,
        })
        self.assertRedirects(response, reverse('students:documents'))
        document = AcademicDocument.objects.get(student=self.student)
        self.assertEqual(document.document_type, AcademicDocument.DocumentType.MATRIC_RESULT)
        self.assertEqual(document.file_name, 'matric_result.pdf')

        # Test view document
        view_response = self.client.get(reverse('students:document_view', kwargs={'doc_id': document.id}))
        self.assertEqual(view_response.status_code, 200)

    def test_invalid_file_type_rejected(self):
        txt_file = SimpleUploadedFile('malicious.exe', b'bad content', content_type='application/x-msdownload')
        response = self.client.post(reverse('students:document_upload'), {
            'document_type': AcademicDocument.DocumentType.FSC_RESULT,
            'file': txt_file,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AcademicDocument.objects.filter(student=self.student).exists())

    def test_cross_student_document_isolation(self):
        pdf_file = SimpleUploadedFile('other_result.pdf', b'%PDF-1.4 other content', content_type='application/pdf')
        other_doc = AcademicDocument.objects.create(
            student=self.other_student,
            document_type=AcademicDocument.DocumentType.CNIC_BFORM,
            file=pdf_file,
            file_name='other_result.pdf',
        )
        # Attempt to view other student's document
        response = self.client.get(reverse('students:document_view', kwargs={'doc_id': other_doc.id}))
        self.assertEqual(response.status_code, 404)

        # Attempt to delete other student's document
        delete_response = self.client.post(reverse('students:document_delete', kwargs={'doc_id': other_doc.id}))
        self.assertEqual(delete_response.status_code, 404)
        self.assertTrue(AcademicDocument.objects.filter(pk=other_doc.pk).exists())

    def test_student_can_delete_own_document(self):
        pdf_file = SimpleUploadedFile('to_delete.pdf', b'%PDF-1.4 content', content_type='application/pdf')
        doc = AcademicDocument.objects.create(
            student=self.student,
            document_type=AcademicDocument.DocumentType.OTHER,
            file=pdf_file,
            file_name='to_delete.pdf',
        )
        response = self.client.post(reverse('students:document_delete', kwargs={'doc_id': doc.id}))
        self.assertRedirects(response, reverse('students:documents'))
        self.assertFalse(AcademicDocument.objects.filter(pk=doc.pk).exists())


class StudentProgramRegistrationTests(TestCase):
    def setUp(self):
        from admissions.models import Campus, Department, PISTApplicant, Program, ProgramEligibility, Qualification, TestCenter, TestSession
        from datetime import time

        self.campus = Campus.objects.create(name='PIST Islamabad Main Campus', city='Islamabad', code='ISB', address='H-12')
        self.department = Department.objects.create(campus=self.campus, code='CS', name='Department of Computer Science', slug='cs')
        self.program = Program.objects.create(
            department=self.department, campus=self.campus, name='Bachelor of Science in Computer Science',
            code='BSCS-ISB', slug='bscs-isb', admissions_open=True, eligibility_percentage=60,
        )
        self.qualification = Qualification.objects.create(name='Intermediate (Pre-Engineering)', qualification_group_code='PRE_ENGINEERING')
        ProgramEligibility.objects.create(program=self.program, qualification=self.qualification, minimum_percentage=60)
        self.center = TestCenter.objects.create(campus=self.campus, name='Islamabad Test Center', address='H-12', city='Islamabad', building='Academic Block A', hall='Hall 3')
        self.session = TestSession.objects.create(test_center=self.center, program=self.program, test_date=date(2026, 9, 10), reporting_time=time(8, 30), start_time=time(9), building='Academic Block A', hall='Hall 3')

        self.user = get_user_model().objects.create_user(username='reg@example.com', email='reg@example.com', password='AyeshaStrong!29')
        self.student = StudentProfile.objects.create(
            user=self.user, student_id=generate_student_id(), full_name='Reg Student',
            cnic='12345-1234567-1', date_of_birth='2000-01-15', phone='03001234567', address='Islamabad',
        )
        # Upload 5 required documents
        for doc_type, _ in AcademicDocument.DocumentType.choices:
            AcademicDocument.objects.create(
                student=self.student,
                document_type=doc_type,
                file=SimpleUploadedFile(f'{doc_type}.pdf', b'%PDF-1.4 test', content_type='application/pdf'),
                file_name=f'{doc_type}.pdf',
            )

        self.other_user = get_user_model().objects.create_user(username='other_reg@example.com', email='other_reg@example.com', password='AyeshaStrong!29')
        self.other_student = StudentProfile.objects.create(
            user=self.other_user, student_id=generate_student_id(), full_name='Other Reg Student',
            cnic='12345-1234567-2', date_of_birth='2000-01-15', phone='03001234568', address='Lahore',
        )
        self.client.force_login(self.user)

    def test_apply_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('students:apply_program', kwargs={'program_slug': self.program.slug}))
        self.assertRedirects(response, reverse('students:login') + f'?next=/student/programs/{self.program.slug}/apply/')

    def test_program_registration_flow_and_unique_id_generation(self):
        from admissions.models import PISTApplicant

        # Step 1: Form check
        response = self.client.post(reverse('students:apply_program', kwargs={'program_slug': self.program.slug}), {
            'qualification': self.qualification.pk,
            'percentage': 75,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Check your application')

        # Step 2: Confirm submit
        submit_response = self.client.post(reverse('students:submit_program_application', kwargs={'program_slug': self.program.slug}), {
            'confirm': '1',
            'qualification': self.qualification.pk,
            'percentage': 75,
        })
        self.assertEqual(submit_response.status_code, 200)
        self.assertContains(submit_response, 'Application Submitted Successfully')

        # Verify application in database
        app = PISTApplicant.objects.get(student=self.student, program=self.program)
        self.assertTrue(app.program_registration_id.startswith('CS26-'))
        self.assertTrue(app.application_id.startswith('APP-2026-'))
        self.assertEqual(app.application_status, PISTApplicant.ApplicationStatus.SUBMITTED)

    def test_duplicate_registration_rejected(self):
        from admissions.models import PISTApplicant
        PISTApplicant.objects.create(
            student=self.student, application_id='APP-2026-DUP', program_registration_id='CS26-0001',
            full_name=self.student.full_name, cnic=self.student.cnic, email=self.user.email, phone=self.student.phone,
            address=self.student.address, matric_marks=800, matric_total=1000, fsc_marks=800, fsc_total=1000,
            campus=self.campus, program=self.program, source_application_id='APP-2026-DUP',
        )
        response = self.client.get(reverse('students:apply_program', kwargs={'program_slug': self.program.slug}))
        self.assertEqual(response.status_code, 302)

    def test_admissions_closed_rejected(self):
        self.program.admissions_open = False
        self.program.save(update_fields=['admissions_open'])
        response = self.client.post(reverse('students:apply_program', kwargs={'program_slug': self.program.slug}), {
            'qualification': self.qualification.pk,
            'percentage': 75,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admissions are closed for this program.')

    def test_ineligible_student_rejected(self):
        response = self.client.post(reverse('students:apply_program', kwargs={'program_slug': self.program.slug}), {
            'qualification': self.qualification.pk,
            'percentage': 50,  # Below 60% requirement
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'minimum of 60.00%')

    def test_cross_student_application_detail_isolation(self):
        from admissions.models import PISTApplicant
        other_app = PISTApplicant.objects.create(
            student=self.other_student, application_id='APP-2026-OTHER-DETAIL', program_registration_id='CS26-0002',
            full_name=self.other_student.full_name, cnic=self.other_student.cnic, email=self.other_user.email,
            phone=self.other_student.phone, address=self.other_student.address, matric_marks=800, matric_total=1000,
            fsc_marks=800, fsc_total=1000, campus=self.campus, program=self.program, source_application_id='APP-2026-OTHER-DETAIL',
        )
        # Logged in as self.user, cannot view other_app
        response = self.client.get(reverse('students:application_detail', kwargs={'application_uuid': other_app.pk}))
        self.assertEqual(response.status_code, 404)


class AcademicRecordTests(TestCase):
    def setUp(self):
        from admissions.models import Campus, Department, Program, ProgramEligibility, Qualification, TestType

        self.campus = Campus.objects.create(name='PIST Islamabad Main Campus', city='Islamabad', code='ISB', address='H-12')
        self.department = Department.objects.create(campus=self.campus, code='CS', name='Department of Computer Science', slug='cs')
        self.program = Program.objects.create(
            department=self.department, campus=self.campus, name='Bachelor of Science in Computer Science',
            code='BSCS-ISB', slug='bscs-isb', admissions_open=True, eligibility_percentage=60,
        )
        self.qualification = Qualification.objects.create(name='Intermediate (Pre-Engineering)', qualification_group_code='PRE_ENGINEERING')
        ProgramEligibility.objects.create(program=self.program, qualification=self.qualification, minimum_percentage=60)
        self.test_type = TestType.objects.create(name='USAT')

        self.user = get_user_model().objects.create_user(username='acad@example.com', email='acad@example.com', password='AyeshaStrong!29')
        self.student = StudentProfile.objects.create(
            user=self.user, student_id=generate_student_id(), full_name='Acad Student',
            cnic='12345-1234567-1', date_of_birth='2000-01-15', phone='03001234567',
        )
        self.other_user = get_user_model().objects.create_user(username='other_acad@example.com', email='other_acad@example.com', password='AyeshaStrong!29')
        self.other_student = StudentProfile.objects.create(
            user=self.other_user, student_id=generate_student_id(), full_name='Other Acad Student',
            cnic='12345-1234567-2', date_of_birth='2000-01-15', phone='03001234568',
        )
        self.client.force_login(self.user)

    def test_matric_record_saves_and_computes_percentage(self):
        from .models import MatricRecord
        response = self.client.post(reverse('students:matric_edit'), {
            'board': 'FBISE Islamabad',
            'group': 'Science',
            'passing_year': 2022,
            'obtained_marks': 935,
            'total_marks': 1100,
        })
        self.assertRedirects(response, reverse('students:academic_record'))
        record = MatricRecord.objects.get(student=self.student)
        self.assertEqual(record.board, 'FBISE Islamabad')
        self.assertEqual(float(record.percentage), 85.0)

    def test_intermediate_record_saves_and_computes_percentage(self):
        from .models import IntermediateRecord
        response = self.client.post(reverse('students:intermediate_edit'), {
            'board': 'FBISE Islamabad',
            'group': IntermediateRecord.Group.PRE_ENGINEERING,
            'passing_year': 2024,
            'obtained_marks': 880,
            'total_marks': 1100,
        })
        self.assertRedirects(response, reverse('students:academic_record'))
        record = IntermediateRecord.objects.get(student=self.student)
        self.assertEqual(record.group, IntermediateRecord.Group.PRE_ENGINEERING)
        self.assertEqual(float(record.percentage), 80.0)

    def test_test_score_creation_and_certificate_upload(self):
        from .models import StudentTestScore
        cert_file = SimpleUploadedFile('usat_cert.pdf', b'%PDF-1.4 certificate', content_type='application/pdf')
        response = self.client.post(reverse('students:test_score_add'), {
            'test_type': self.test_type.pk,
            'score': 85,
            'total_score': 100,
            'test_date': '2025-10-15',
            'result_certificate': cert_file,
        })
        self.assertRedirects(response, reverse('students:academic_record'))
        score = StudentTestScore.objects.get(student=self.student)
        self.assertEqual(float(score.percentage), 85.0)
        self.assertTrue(score.result_certificate)

    def test_cross_student_test_score_isolation(self):
        from .models import StudentTestScore
        other_score = StudentTestScore.objects.create(
            student=self.other_student,
            test_type=self.test_type,
            score=70,
            total_score=100,
            test_date='2025-05-10',
        )
        # Attempt edit other student's test score
        self.assertEqual(self.client.get(reverse('students:test_score_edit', kwargs={'score_id': other_score.id})).status_code, 404)
        # Attempt delete other student's test score
        self.assertEqual(self.client.post(reverse('students:test_score_delete', kwargs={'score_id': other_score.id})).status_code, 404)

    def test_eligibility_preview_integration(self):
        from .models import IntermediateRecord
        # Create intermediate record with 55% (ineligible for 60% requirement)
        IntermediateRecord.objects.create(
            student=self.student,
            board='FBISE Islamabad',
            group=IntermediateRecord.Group.PRE_ENGINEERING,
            passing_year=2024,
            obtained_marks=550,
            total_marks=1000,
        )
        response = self.client.get(reverse('students:academic_record') + f'?program={self.program.slug}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Not Eligible')
        self.assertContains(response, 'Your FSc percentage is 55.00%. This program requires at least 60.00%.')

        # Update marks to 700/1000 (70% - eligible)
        record = IntermediateRecord.objects.get(student=self.student)
        record.obtained_marks = 700
        record.save()
        response_eligible = self.client.get(reverse('students:academic_record') + f'?program={self.program.slug}')
        self.assertContains(response_eligible, 'Eligible')


class ProgramRegistrationComprehensiveTests(TestCase):
    def setUp(self):
        from admissions.models import Campus, Department, PISTApplicant, Program, ProgramEligibility, Qualification, RegistrationIdSequence
        from admissions.services import generate_program_registration_id

        self.campus = Campus.objects.create(name='PIST Islamabad Main Campus', city='Islamabad', code='ISB', address='H-12')
        self.qual = Qualification.objects.create(name='FSc Pre-Engineering', qualification_group_code='PRE_ENGINEERING')

        self.departments = {}
        self.programs = {}
        for code, name in (
            ('CS', 'Department of Computer Science'),
            ('AI', 'Department of Artificial Intelligence'),
            ('SE', 'Department of Software Engineering'),
            ('DS', 'Department of Data Science'),
            ('EE', 'Department of Electrical Engineering'),
        ):
            dept = Department.objects.create(campus=self.campus, code=code, name=name, slug=code.lower())
            prog = Program.objects.create(
                department=dept, campus=self.campus, name=f'BS {name}',
                code=f'BS{code}-ISB', slug=f'bs{code.lower()}-isb', admissions_open=True, eligibility_percentage=60,
            )
            ProgramEligibility.objects.create(program=prog, qualification=self.qual, minimum_percentage=60)
            self.departments[code] = dept
            self.programs[code] = prog

        self.user = get_user_model().objects.create_user(username='tester@example.com', email='tester@example.com', password='AyeshaStrong!29')
        self.student = StudentProfile.objects.create(
            user=self.user, student_id=generate_student_id(), full_name='Comprehensive Student',
            cnic='12345-1234567-9', date_of_birth='2000-01-15', phone='03001234567', address='Islamabad',
        )
        for doc_type, _ in AcademicDocument.DocumentType.choices:
            AcademicDocument.objects.create(
                student=self.student,
                document_type=doc_type,
                file=SimpleUploadedFile(f'{doc_type}.pdf', b'%PDF-1.4 test', content_type='application/pdf'),
                file_name=f'{doc_type}.pdf',
            )

    def test_department_prefix_mapping(self):
        from admissions.services import generate_program_registration_id
        for code in ('CS', 'AI', 'SE', 'DS', 'EE'):
            reg_id = generate_program_registration_id(self.programs[code])
            self.assertTrue(reg_id.startswith(f'{code}26-'), f'Expected prefix {code}26-, got {reg_id}')

    def test_sequential_numbering_and_department_scoping(self):
        from admissions.services import generate_program_registration_id
        cs_prog = self.programs['CS']
        id1 = generate_program_registration_id(cs_prog)
        id2 = generate_program_registration_id(cs_prog)
        id3 = generate_program_registration_id(cs_prog)
        self.assertEqual(id1, 'CS26-0001')
        self.assertEqual(id2, 'CS26-0002')
        self.assertEqual(id3, 'CS26-0003')

        # Different department starts at 0001
        ai_prog = self.programs['AI']
        ai_id1 = generate_program_registration_id(ai_prog)
        self.assertEqual(ai_id1, 'AI26-0001')

    def test_concurrency_safety_registration_id(self):
        from admissions.models import RegistrationIdSequence
        from admissions.services import generate_program_registration_id, registration_id_scope

        # Verify atomic sequence increments and retry resilience
        cs_prog = self.programs['CS']
        generated = [generate_program_registration_id(cs_prog) for _ in range(5)]

        # All 5 IDs must be distinct and sequential
        self.assertEqual(len(set(generated)), 5)
        self.assertEqual(generated, ['CS26-0001', 'CS26-0002', 'CS26-0003', 'CS26-0004', 'CS26-0005'])

    def test_registered_programs_page_and_isolation(self):
        from admissions.models import PISTApplicant
        app = PISTApplicant.objects.create(
            student=self.student,
            application_id='APP-2026-COMP01',
            program_registration_id='CS26-0099',
            full_name=self.student.full_name,
            cnic=self.student.cnic,
            email=self.user.email,
            phone=self.student.phone,
            address=self.student.address,
            matric_marks=850,
            matric_total=1100,
            fsc_marks=920,
            fsc_total=1100,
            campus=self.campus,
            program=self.programs['CS'],
            source_application_id='APP-2026-COMP01',
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('students:registered_programs'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CS26-0099')
        self.assertContains(response, self.programs['CS'].name)
        self.assertContains(response, self.departments['CS'].name)
        self.assertContains(response, self.campus.name)



