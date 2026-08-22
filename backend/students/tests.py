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
