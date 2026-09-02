from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .validators import validate_academic_document


def student_document_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f'academic_documents/{instance.student_id}/{instance.id}{extension}'


class StudentProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'
        PREFER_NOT_TO_SAY = 'prefer_not_to_say', 'Prefer not to say'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    full_name = models.CharField(max_length=150)
    email_verified = models.BooleanField(default=False)
    cnic = models.CharField(max_length=15, unique=True, db_index=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True)
    phone = models.CharField(max_length=20)
    father_name = models.CharField(max_length=150, blank=True)
    address = models.TextField(blank=True)
    profile_photo = models.ImageField(upload_to='student_photos/%Y/%m/', blank=True, null=True)
    nationality = models.CharField(max_length=80, blank=True, default='Pakistani')
    student_id = models.CharField(max_length=30, unique=True, editable=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student_id} - {self.full_name}'

    def get_onboarding_progress(self):
        from admissions.models import PISTApplicant

        documents = set(self.academic_documents.values_list('document_type', flat=True))
        required_documents = {value for value, _label in AcademicDocument.DocumentType.choices}
        applications = self.program_applications.exclude(application_status=PISTApplicant.ApplicationStatus.WITHDRAWN)
        application = applications.order_by('-created_at').first()
        completed_profile = all(getattr(self, field) for field in ('full_name', 'cnic', 'date_of_birth', 'phone', 'address'))
        completed = [
            True,
            completed_profile,
            hasattr(self, 'matric_record') or hasattr(self, 'intermediate_record') or self.test_scores.exists(),
            required_documents.issubset(documents),
            application is not None,
            bool(application and application.eligibility_status not in ('', PISTApplicant.EligibilityStatus.PENDING)),
            bool(application and application.roll_number and application.eligibility_status == PISTApplicant.EligibilityStatus.ELIGIBLE),
            bool(application and application.test_session_id),
        ]
        ctas = ('students:profile_edit', 'students:profile_edit', 'students:academic_record', 'students:documents', 'admissions:programs', 'students:academic_record', 'students:registered_programs', 'students:registered_programs')
        labels = ('Account Created', 'Profile Completed', 'Academic Information Added', 'Documents Uploaded', 'Program Registered', 'Eligibility Checked', 'Roll Number Issued', 'Entry Test Scheduled')
        current_found = False
        progress = []
        for index, (label, is_complete, cta) in enumerate(zip(labels, completed, ctas), start=1):
            current = not is_complete and not current_found
            current_found = current_found or current
            progress.append({'number': index, 'label': label, 'complete': is_complete, 'current': current, 'cta': cta})
        return progress


class StudentIdSequence(models.Model):
    year = models.PositiveIntegerField(unique=True)
    last_value = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.year}: {self.last_value}'


class AcademicDocument(models.Model):
    class DocumentType(models.TextChoices):
        MATRIC_RESULT = 'MATRIC', 'Matric Certificate/Result'
        FSC_RESULT = 'FSC', 'FSc/Intermediate Certificate/Result'
        ENTRY_TEST_RESULT = 'ENTRY_TEST', 'Entry Test Result'
        CNIC_BFORM = 'CNIC_BFORM', 'CNIC/B-Form Copy'
        OTHER = 'OTHER', 'Other Supporting Document'

    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='academic_documents')
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    file = models.FileField(upload_to=student_document_upload_path, validators=[validate_academic_document])
    file_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verification_status = models.CharField(max_length=10, choices=VerificationStatus.choices, default=VerificationStatus.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_academic_documents',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-uploaded_at']
        constraints = [
            models.UniqueConstraint(fields=['student', 'document_type'], name='one_document_per_type_per_student'),
        ]

    def __str__(self):
        return f'{self.get_document_type_display()} - {self.student}'

    @property
    def file_extension(self) -> str:
        if self.file_name:
            return Path(self.file_name).suffix.lstrip('.').upper()
        if self.file and self.file.name:
            return Path(self.file.name).suffix.lstrip('.').upper()
        return ''

    @property
    def is_image(self) -> bool:
        return self.file_extension.lower() in {'png', 'jpg', 'jpeg', 'webp'}

    @property
    def is_pdf(self) -> bool:
        return self.file_extension.lower() == 'pdf'

    @property
    def file_size_display(self) -> str:
        try:
            if self.file and hasattr(self.file, 'size') and self.file.storage.exists(self.file.name):
                size = self.file.size
                if size < 1024:
                    return f'{size} B'
                if size < 1024 * 1024:
                    return f'{size / 1024:.1f} KB'
                return f'{size / (1024 * 1024):.1f} MB'
        except Exception:
            pass
        return ''


class MatricRecord(models.Model):
    student = models.OneToOneField(StudentProfile, on_delete=models.CASCADE, related_name='matric_record')
    board = models.CharField(max_length=150)
    group = models.CharField(max_length=100)
    passing_year = models.PositiveSmallIntegerField(validators=[MinValueValidator(1990), MaxValueValidator(2100)])
    obtained_marks = models.PositiveIntegerField()
    total_marks = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    percentage = models.DecimalField(max_digits=5, decimal_places=2, editable=False, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.obtained_marks > self.total_marks:
            raise ValidationError('Obtained marks cannot exceed total marks.')

    def save(self, *args, **kwargs):
        self.full_clean()
        self.percentage = round((self.obtained_marks / self.total_marks) * 100, 2)
        super().save(*args, **kwargs)


class IntermediateRecord(models.Model):
    class Group(models.TextChoices):
        PRE_MEDICAL = 'PRE_MEDICAL', 'Pre-Medical'
        PRE_ENGINEERING = 'PRE_ENGINEERING', 'Pre-Engineering'
        ICS = 'ICS', 'Intermediate in Computer Science (ICS)'
        GENERAL_SCIENCE = 'GENERAL_SCIENCE', 'General Science'
        COMMERCE = 'COMMERCE', 'Intermediate in Commerce (I.Com)'
        HUMANITIES = 'HUMANITIES', 'Humanities / Arts'
        OTHER = 'OTHER', 'Other'

    student = models.OneToOneField(StudentProfile, on_delete=models.CASCADE, related_name='intermediate_record')
    board = models.CharField(max_length=150)
    group = models.CharField(max_length=30, choices=Group.choices)
    passing_year = models.PositiveSmallIntegerField(validators=[MinValueValidator(1990), MaxValueValidator(2100)])
    obtained_marks = models.PositiveIntegerField()
    total_marks = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    percentage = models.DecimalField(max_digits=5, decimal_places=2, editable=False, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.obtained_marks > self.total_marks:
            raise ValidationError('Obtained marks cannot exceed total marks.')

    def save(self, *args, **kwargs):
        self.full_clean()
        self.percentage = round((self.obtained_marks / self.total_marks) * 100, 2)
        super().save(*args, **kwargs)


class StudentTestScore(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='test_scores')
    test_type = models.ForeignKey('admissions.TestType', on_delete=models.PROTECT, related_name='student_scores')
    score = models.DecimalField(max_digits=7, decimal_places=2)
    total_score = models.DecimalField(max_digits=7, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, editable=False, default=0)
    test_date = models.DateField()
    result_certificate = models.FileField(upload_to='test_score_certificates/%Y/', blank=True, null=True, validators=[validate_academic_document])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-test_date', '-created_at']

    def clean(self):
        if self.total_score <= 0:
            raise ValidationError('Total score must be greater than zero.')
        if self.score < 0 or self.score > self.total_score:
            raise ValidationError('Score must be between zero and the total score.')

    def save(self, *args, **kwargs):
        self.full_clean()
        self.percentage = round((self.score / self.total_score) * 100, 2)
        super().save(*args, **kwargs)
