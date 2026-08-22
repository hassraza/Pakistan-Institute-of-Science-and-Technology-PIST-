from datetime import date, timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from admissions.models import Program, ProgramEligibility, ProgramTestRequirement, Qualification, Campus, Department, TestType
from admissions.services import check_program_eligibility
from .models import IntermediateRecord, MatricRecord, StudentTestScore, StudentProfile


class AcademicRecordTests(TestCase):
    def setUp(self):
        self.student = self.make_student('academic@example.com', '12345-1234567-1')
        self.other = self.make_student('other-academic@example.com', '12345-1234567-2')
        self.client.force_login(self.student.user)
        self.campus = Campus.objects.create(name='PIST Islamabad Campus', city='Islamabad', code='ISB', address='H-12')
        self.department = Department.objects.create(campus=self.campus, code='CS', name='Department of Computer Science', slug='cs')
        self.program = Program.objects.create(department=self.department, campus=self.campus, name='Bachelor of Science in Computer Science', code='BSCS-ISB', slug='bscs-isb', admissions_open=True)
        self.qualification = Qualification.objects.create(name='Intermediate in Computer Science (FSc ICS)', qualification_group_code='ICS')
        ProgramEligibility.objects.create(program=self.program, qualification=self.qualification, minimum_percentage=60)
        self.test_type = TestType.objects.create(name='University Sciences Admission Test (USAT)')
        ProgramTestRequirement.objects.create(program=self.program, test_type=self.test_type)

    def make_student(self, email, cnic):
        user = get_user_model().objects.create_user(username=email, email=email, password='AyeshaStrong!29')
        return StudentProfile.objects.create(user=user, student_id=f'PIST-STU-{email[0]}', full_name='Academic Student', cnic=cnic, date_of_birth='2000-01-15', phone='03001234567')

    def test_anonymous_academic_endpoints_require_login(self):
        self.client.logout()
        for url in (
            reverse('students:academic_record'), reverse('students:matric_edit'),
            reverse('students:intermediate_edit'), reverse('students:test_score_add'),
        ):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_matric_and_intermediate_records_calculate_percentages(self):
        response = self.client.post(reverse('students:matric_edit'), {'board': 'Federal Board', 'group': 'Science', 'passing_year': 2020, 'obtained_marks': 570, 'total_marks': 950, 'percentage': 1})
        self.assertRedirects(response, reverse('students:academic_record'))
        matric = MatricRecord.objects.get(student=self.student)
        self.assertEqual(str(matric.percentage), '60.00')
        self.client.post(reverse('students:intermediate_edit'), {'board': 'Federal Board', 'group': 'ICS', 'passing_year': 2022, 'obtained_marks': 700, 'total_marks': 1000})
        self.assertEqual(str(IntermediateRecord.objects.get(student=self.student).percentage), '70.00')

    def test_marks_over_total_are_rejected(self):
        response = self.client.post(reverse('students:matric_edit'), {'board': 'Federal Board', 'group': 'Science', 'passing_year': 2020, 'obtained_marks': 1001, 'total_marks': 950})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MatricRecord.objects.exists())
        self.assertContains(response, 'cannot exceed')

    def test_records_are_owned_by_request_student(self):
        record = MatricRecord.objects.create(student=self.other, board='Other Board', group='Science', passing_year=2020, obtained_marks=500, total_marks=1000)
        self.assertEqual(self.client.get(reverse('students:academic_record')).status_code, 200)
        self.assertNotContains(self.client.get(reverse('students:academic_record')), 'Other Board')
        self.assertNotIn(record.pk, MatricRecord.objects.filter(student=self.student).values_list('pk', flat=True))

    def test_test_score_crud_and_server_percentage(self):
        response = self.client.post(reverse('students:test_score_add'), {'test_type': self.test_type.pk, 'score': '72', 'total_score': '100', 'test_date': '2026-08-01'})
        self.assertRedirects(response, reverse('students:academic_record'))
        score = StudentTestScore.objects.get(student=self.student)
        self.assertEqual(str(score.percentage), '72.00')
        response = self.client.post(reverse('students:test_score_edit', kwargs={'score_id': score.pk}), {'test_type': self.test_type.pk, 'score': '80', 'total_score': '100', 'test_date': '2026-08-01'})
        self.assertRedirects(response, reverse('students:academic_record'))
        score.refresh_from_db()
        self.assertEqual(str(score.percentage), '80.00')
        self.assertEqual(self.client.get(reverse('students:test_score_delete', kwargs={'score_id': score.pk})).status_code, 200)
        self.assertRedirects(self.client.post(reverse('students:test_score_delete', kwargs={'score_id': score.pk})), reverse('students:academic_record'))
        self.assertFalse(StudentTestScore.objects.exists())

    def test_cross_student_test_score_access_is_denied(self):
        score = StudentTestScore.objects.create(student=self.other, test_type=self.test_type, score=70, total_score=100, test_date='2026-08-01')
        for url in (
            reverse('students:test_score_edit', kwargs={'score_id': score.pk}),
            reverse('students:test_score_delete', kwargs={'score_id': score.pk}),
            reverse('students:test_certificate_view', kwargs={'score_id': score.pk}),
        ):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_eligibility_reports_real_percentage_shortfall_and_missing_test(self):
        IntermediateRecord.objects.create(student=self.student, board='Federal Board', group='ICS', passing_year=2022, obtained_marks=570, total_marks=1000)
        result = check_program_eligibility(self.student, self.program)
        self.assertFalse(result.is_eligible)
        self.assertTrue(any('57.00%' in reason and '60' in reason for reason in result.reasons))
        self.student.intermediate_record.obtained_marks = 700
        self.student.intermediate_record.save()
        result = check_program_eligibility(self.student, self.program)
        self.assertFalse(result.is_eligible)
        self.assertTrue(any('University Sciences Admission Test' in reason for reason in result.reasons))
        StudentTestScore.objects.create(student=self.student, test_type=self.test_type, score=70, total_score=100, test_date='2026-08-01')
        self.assertTrue(check_program_eligibility(self.student, self.program).is_eligible)

    def test_missing_intermediate_record_has_distinct_reason(self):
        result = check_program_eligibility(self.student, self.program)
        self.assertFalse(result.is_eligible)
        self.assertTrue(any('not yet entered your Intermediate/FSc' in reason for reason in result.reasons))
