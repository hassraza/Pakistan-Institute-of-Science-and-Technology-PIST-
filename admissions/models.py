from __future__ import annotations

from datetime import time
from decimal import Decimal
import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Campus(models.Model):
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=120)
    code = models.CharField(max_length=12, unique=True)
    address = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    admissions_open = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['city', 'name']

    def __str__(self):
        return f'{self.name} ({self.code})'


class Department(models.Model):
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['campus__city', 'name']
        constraints = [
            models.UniqueConstraint(fields=['campus', 'slug'], name='unique_department_slug_per_campus'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f'{self.campus.code}-{self.name}')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} - {self.campus.code}'


class Program(models.Model):
    DEGREE_LEVEL_CHOICES = [
        ('Bachelor', 'Bachelor'),
        ('Master', 'Master'),
        ('PhD', 'PhD'),
    ]

    TEST_TYPE_CHOICES = [
        ('USAT', 'USAT'),
        ('MDCAT', 'MDCAT'),
        ('ECAT', 'ECAT'),
        ('NTS GAT', 'NTS GAT'),
        ('LAT', 'LAT'),
        ('Other', 'Other'),
    ]

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='programs')
    name = models.CharField(max_length=220)
    code = models.CharField(max_length=30)
    slug = models.SlugField(max_length=240)
    description = models.TextField(blank=True)
    eligibility_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('60.00'))
    eligibility_text = models.TextField(blank=True)
    required_test_type = models.CharField(max_length=20, choices=TEST_TYPE_CHOICES, default='USAT')
    admissions_open = models.BooleanField(default=True)
    application_deadline = models.DateField(blank=True, null=True)
    duration = models.CharField(max_length=50, default='4 Years')
    degree_level = models.CharField(max_length=20, choices=DEGREE_LEVEL_CHOICES, default='Bachelor')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['department__campus__city', 'department__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['department', 'code'], name='unique_program_code_per_department'),
            models.UniqueConstraint(fields=['department', 'slug'], name='unique_program_slug_per_department'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f'{self.department.campus.code}-{self.code}')
        super().save(*args, **kwargs)

    @property
    def campus(self):
        return self.department.campus

    def __str__(self):
        return f'{self.name} ({self.department.campus.code})'


class PISTApplicant(models.Model):
    class Status(models.TextChoices):
        RECEIVED = 'Application Received', 'Application Received'
        ROLL_ISSUED = 'Roll No Issued', 'Roll No Issued'
        SHORTLISTED = 'Shortlisted for Entry Test', 'Shortlisted for Entry Test'
        MERIT_LIST_1 = 'Merit List 1 Approved', 'Merit List 1 Approved'
        REJECTED = 'Rejected', 'Rejected'
        ELIGIBILITY_REVIEW = 'Eligibility Review', 'Eligibility Review'
        TEST_SCHEDULED = 'Test Scheduled', 'Test Scheduled'
        TEST_APPEARED = 'Test Appeared', 'Test Appeared'
        MERIT_LIST_2 = 'Merit List 2', 'Merit List 2'
        SELECTED = 'Selected', 'Selected'
        WAITLISTED = 'Waitlisted', 'Waitlisted'
        ADMISSION_CONFIRMED = 'Admission Confirmed', 'Admission Confirmed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=200)
    father_name = models.CharField(max_length=200)
    cnic = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    profile_photo = models.ImageField(upload_to='applicants/photos/', blank=True, null=True)
    matric_marks = models.PositiveIntegerField()
    matric_total = models.PositiveIntegerField()
    fsc_marks = models.PositiveIntegerField()
    fsc_total = models.PositiveIntegerField()
    test_type = models.CharField(max_length=20, choices=Program.TEST_TYPE_CHOICES, blank=True)
    test_score = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    campus = models.ForeignKey(Campus, on_delete=models.PROTECT, related_name='applicants')
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name='applicants')
    roll_number = models.CharField(max_length=60, unique=True, blank=True, null=True)
    test_date = models.DateField(blank=True, null=True)
    reporting_time = models.TimeField(blank=True, null=True)
    test_venue = models.CharField(max_length=200, blank=True)
    test_building = models.CharField(max_length=200, blank=True)
    test_hall = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.RECEIVED)
    source_application_id = models.CharField(max_length=80, db_index=True)
    nationality = models.CharField(max_length=80, blank=True)
    passport_number = models.CharField(max_length=40, blank=True)
    visa_information = models.CharField(max_length=120, blank=True)
    international_address = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['source_application_id', 'program'], name='unique_source_application_per_program'),
        ]
        indexes = [
            models.Index(fields=['cnic']),
            models.Index(fields=['email']),
            models.Index(fields=['roll_number']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'{self.full_name} - {self.program.code}'

    @property
    def matric_percentage(self):
        if not self.matric_total:
            return Decimal('0')
        return (Decimal(self.matric_marks) / Decimal(self.matric_total)) * Decimal('100')

    @property
    def fsc_percentage(self):
        if not self.fsc_total:
            return Decimal('0')
        return (Decimal(self.fsc_marks) / Decimal(self.fsc_total)) * Decimal('100')

    @property
    def application_identifier(self):
        return str(self.pk)


class ApplicantTestScore(models.Model):
    applicant = models.ForeignKey(PISTApplicant, on_delete=models.CASCADE, related_name='test_scores')
    test_type = models.CharField(max_length=20, choices=Program.TEST_TYPE_CHOICES)
    score = models.DecimalField(max_digits=6, decimal_places=2)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    taken_on = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['applicant', 'test_type'], name='unique_applicant_test_type'),
        ]

    def __str__(self):
        return f'{self.applicant.full_name} - {self.test_type}'


class TestCenter(models.Model):
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name='test_centers')
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=255)
    building = models.CharField(max_length=200)
    hall = models.CharField(max_length=200)
    capacity = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['campus__city', 'name']

    def __str__(self):
        return f'{self.name} - {self.campus.code}'


class TestSession(models.Model):
    test_center = models.ForeignKey(TestCenter, on_delete=models.CASCADE, related_name='sessions')
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='test_sessions')
    test_date = models.DateField()
    reporting_time = models.TimeField(default=time(8, 30))
    available_seats = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['test_date', 'reporting_time']
        constraints = [
            models.UniqueConstraint(fields=['test_center', 'program', 'test_date'], name='unique_session_per_center_program_date'),
        ]

    def __str__(self):
        return f'{self.program.code} - {self.test_date} - {self.test_center.name}'

    @property
    def remaining_seats(self):
        return self.available_seats
