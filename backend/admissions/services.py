from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta, time

from django.db import IntegrityError, transaction
from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from .models import ApplicantTestScore, Campus, PISTApplicant, Program, ProgramTestRequirement, RegistrationIdSequence, RollNumberSequence, RollSlip, TestCenter, TestSession
from students.models import AcademicDocument, StudentProfile


class ConflictError(APIException):
    status_code = 409
    default_detail = 'A duplicate application was detected.'


class EligibilityError(APIException):
    status_code = 422
    default_detail = 'Applicant does not meet the minimum eligibility requirement.'


class ConfigurationError(APIException):
    status_code = 500
    default_detail = 'Admission configuration is incomplete.'


def current_admission_year():
    return settings.PIST_ADMISSION_YEAR or timezone.localdate().year


def registration_id_scope(program):
    return program.department.code or program.code.split('-')[0], str(current_admission_year())[-2:]


def generate_program_registration_id(program):
    """Allocate a department/year ID inside the application transaction with retry safety."""
    import time
    from django.db import OperationalError
    department_code, year_yy = registration_id_scope(program)
    for attempt in range(5):
        try:
            with transaction.atomic():
                sequence, _ = RegistrationIdSequence.objects.select_for_update().get_or_create(
                    department_code=department_code,
                    admission_year_yy=year_yy,
                )
                sequence.last_number += 1
                sequence.save(update_fields=['last_number'])
                return f'{department_code}{year_yy}-{sequence.last_number:04d}'
        except (IntegrityError, OperationalError):
            if attempt == 4:
                raise
            time.sleep(0.05)


def registration_blockers(*, student: StudentProfile, program: Program, qualification=None, percentage=None):
    blockers = []
    today = timezone.localdate()
    if not program.admissions_open or (program.application_deadline and today > program.application_deadline):
        blockers.append('Admissions are closed for this program.')
    if not all((student.full_name, student.cnic, student.date_of_birth, student.phone, student.address)):
        blockers.append('Complete your student profile, including your address, before applying.')
    required_documents = {value for value, _label in AcademicDocument.DocumentType.choices}
    uploaded_documents = set(student.academic_documents.values_list('document_type', flat=True))
    if not required_documents.issubset(uploaded_documents):
        blockers.append('Upload all five required academic documents before applying.')
    if hasattr(student, 'intermediate_record'):
        academic_result = check_program_eligibility(student, program, include_test=False)
        blockers.extend(academic_result.reasons)
    else:
        rules = list(program.eligibility_rules.select_related('qualification'))
        if qualification is None or percentage is None:
            blockers.append('Enter your qualifying examination and percentage before applying.')
        elif not any(rule.qualification_id == qualification.id and percentage >= rule.minimum_percentage for rule in rules):
            requirement = ', '.join(rule.qualification.name for rule in rules) or program.eligibility_text
            minimum = max((rule.minimum_percentage for rule in rules), default=program.eligibility_percentage)
            blockers.append(f'This program requires a minimum of {minimum}% in {requirement}; your recorded result does not meet this requirement.')
    if PISTApplicant.objects.filter(student=student, program=program).exclude(application_status=PISTApplicant.ApplicationStatus.WITHDRAWN).exists():
        blockers.append('You already have an active application for this program.')
    return blockers


@dataclass
class EligibilityResult:
    eligible: bool
    matric_percentage: float
    fsc_percentage: float
    required_percentage: float
    errors: dict


@dataclass
class StudentEligibilityResult:
    is_eligible: bool
    reasons: list[str]
    checked_qualification: object | None = None
    checked_test: bool = False


def check_program_eligibility(student, program, *, include_test=True):
    """Evaluate a program against the student's stored academic records and scores."""
    reasons = []
    intermediate = getattr(student, 'intermediate_record', None)
    rules = list(program.eligibility_rules.select_related('qualification'))
    matching_rules = [rule for rule in rules if rule.qualification.qualification_group_code == intermediate.group] if intermediate and rules else []
    checked_qualification = matching_rules[0].qualification if matching_rules else None
    qualification_ok = False
    if not intermediate:
        reasons.append('You have not yet entered your Intermediate/FSc academic record. Please complete it before applying.')
    elif not matching_rules:
        required = ', '.join(rule.qualification.name for rule in rules) or 'the required qualification'
        reasons.append(f'Your Intermediate/FSc group does not match this program. Required qualification: {required}.')
    else:
        qualification_ok = any(intermediate.percentage >= rule.minimum_percentage for rule in matching_rules)
        if not qualification_ok:
            minimum = max(rule.minimum_percentage for rule in matching_rules)
            reasons.append(f'Your FSc percentage is {intermediate.percentage:.2f}%. This program requires at least {minimum:.2f}%.')

    requirements = list(program.test_requirements.select_related('test_type')) if include_test else []
    student_test_types = set(student.test_scores.values_list('test_type_id', flat=True))
    alternative_requirements = [requirement for requirement in requirements if requirement.is_alternative]
    required_requirements = [requirement for requirement in requirements if not requirement.is_alternative]
    alternatives_ok = not alternative_requirements or any(item.test_type_id in student_test_types for item in alternative_requirements)
    required_ok = all(item.test_type_id in student_test_types for item in required_requirements)
    checked_test = alternatives_ok and required_ok
    if requirements and not checked_test:
        names = ' or '.join(requirement.test_type.name for requirement in requirements)
        reasons.append(f'This program requires {names}. No matching test score was found on your academic record.')

    return StudentEligibilityResult(
        is_eligible=not reasons and qualification_ok,
        reasons=reasons,
        checked_qualification=checked_qualification,
        checked_test=checked_test,
    )


class EligibilityService:
    @staticmethod
    def evaluate(*, program: Program, matric_marks: int, matric_total: int, fsc_marks: int, fsc_total: int, tests: list[dict]) -> EligibilityResult:
        matric_percentage = (matric_marks / matric_total) * 100 if matric_total else 0
        fsc_percentage = (fsc_marks / fsc_total) * 100 if fsc_total else 0
        required_percentage = float(program.eligibility_rules.order_by('-minimum_percentage').values_list('minimum_percentage', flat=True).first() or program.eligibility_percentage)
        errors: dict[str, list[str]] = {}

        if matric_percentage < required_percentage:
            errors.setdefault('matric_marks', []).append(f'Minimum eligibility is {required_percentage:.0f}% in Matric.')
        if fsc_percentage < required_percentage:
            errors.setdefault('fsc_marks', []).append(f'Minimum eligibility is {required_percentage:.0f}% in FSc.')

        required_requirements = list(program.test_requirements.values_list('test_type__name', flat=True))
        required_test = program.required_test_type
        provided_types = {score['type'] for score in tests}
        if required_requirements:
            requirement_codes = set()
            for name in required_requirements:
                if '(USAT)' in name:
                    requirement_codes.add('USAT')
                elif '(ECAT)' in name:
                    requirement_codes.add('ECAT')
                elif '(MDCAT)' in name:
                    requirement_codes.add('MDCAT')
                elif '(LAT)' in name:
                    requirement_codes.add('LAT')
                elif name == 'PIST University Entry Test' or name.endswith('(Graduate)'):
                    requirement_codes.add('Other')
            accepted_codes = provided_types
            if not accepted_codes.intersection(requirement_codes):
                errors.setdefault('tests', []).append(f"One of the following tests is required: {' OR '.join(required_requirements)}.")
        elif required_test != 'Other' and required_test not in provided_types:
            errors.setdefault('tests', []).append(f'{required_test} is required for this program.')

        return EligibilityResult(
            eligible=not errors,
            matric_percentage=matric_percentage,
            fsc_percentage=fsc_percentage,
            required_percentage=required_percentage,
            errors=errors,
        )


class RollNumberService:
    @staticmethod
    @transaction.atomic
    def issue_roll_number(application: PISTApplicant) -> RollSlip:
        """Issue one immutable roll slip after eligibility and session assignment."""
        if application.eligibility_status != PISTApplicant.EligibilityStatus.ELIGIBLE:
            raise ConfigurationError('A roll number can only be issued to an eligible application.')
        session = getattr(application, 'test_session', None)
        if session is None:
            raise ConfigurationError('A test session must be assigned before issuing a roll number.')
        existing = RollSlip.objects.filter(application=application).first()
        if existing:
            return existing
        sequence, _ = RollNumberSequence.objects.select_for_update().get_or_create(
            campus=application.campus, program=application.program, year=current_admission_year(),
        )
        sequence.last_number += 1
        sequence.save(update_fields=['last_number'])
        roll_number = f'PIST-{application.campus.code}-{application.program.department.code}-{current_admission_year()}-{sequence.last_number:04d}'
        slip = RollSlip.objects.create(application=application, roll_number=roll_number, test_session=session)
        application.roll_number = roll_number
        application.save(update_fields=['roll_number', 'updated_at'])
        return slip

    @staticmethod
    def generate(*, campus_code: str, program_code: str, year: int | None = None) -> str:
        # Compatibility helper for legacy integrations; portal issuance uses issue_roll_number.
        year = year or timezone.now().year
        for _ in range(100):
            suffix = f'{secrets.randbelow(10000):04d}'
            roll_number = f'PIST-{campus_code}-{program_code}-{year}-{suffix}'
            if not PISTApplicant.objects.filter(roll_number=roll_number).exists():
                return roll_number
        raise ConfigurationError('Unable to generate a unique roll number.')


class TestSchedulingService:
    DEFAULT_REPORTING_TIME = time(8, 30)

    @staticmethod
    def assign(applicant: PISTApplicant, *, submitted_at=None):
        submitted_at = submitted_at or timezone.now()
        test_date = submitted_at.date() + timedelta(days=10)

        with transaction.atomic():
            session = (
                TestSession.objects.select_for_update()
                .select_related('test_center', 'program', 'test_center__campus')
                .filter(
                    test_center__campus=applicant.campus,
                    program=applicant.program,
                    test_date=test_date,
                    is_active=True,
                    available_seats__gt=0,
                )
                .order_by('reporting_time', 'id')
                .first()
            )

            if session is None:
                test_center = TestCenter.objects.filter(campus=applicant.campus, is_active=True).order_by('id').first()
                if test_center is None:
                    raise ConfigurationError('No active test center is configured for this campus.')
                session = TestSession.objects.create(
                    test_center=test_center,
                    program=applicant.program,
                    test_date=test_date,
                    reporting_time=TestSchedulingService.DEFAULT_REPORTING_TIME,
                    available_seats=max(1, test_center.capacity),
                    is_active=True,
                )

            if session.available_seats <= 0:
                raise ConfigurationError('No seats are available for the assigned test session.')

            session.available_seats -= 1
            session.save(update_fields=['available_seats'])

            applicant.test_date = session.test_date
            applicant.reporting_time = session.reporting_time
            applicant.test_venue = session.test_center.name
            applicant.test_building = session.test_center.building
            applicant.test_hall = session.test_center.hall
            applicant.status = PISTApplicant.Status.ROLL_ISSUED
            applicant.test_session = session
            applicant.save(update_fields=['test_date', 'reporting_time', 'test_venue', 'test_building', 'test_hall', 'status', 'test_session', 'updated_at'])
            return session


class ApplicationProcessingService:
    @staticmethod
    @transaction.atomic
    def process_external_application(*, validated_data: dict):
        tests = validated_data.pop('tests', [])
        profile_photo_file = validated_data.pop('profile_photo_file', None)
        campus: Campus = validated_data.pop('campus')
        program: Program = validated_data.pop('program')

        if not program.admissions_open or not campus.admissions_open:
            raise ValidationError({'program_code': ['Admissions are currently closed for the selected campus or program.']})

        if PISTApplicant.objects.filter(source_application_id=validated_data['source_application_id'], program=program).exists():
            raise ConflictError('An application with the same source ID already exists for this program.')

        eligibility = EligibilityService.evaluate(
            program=program,
            matric_marks=validated_data['matric_marks'],
            matric_total=validated_data['matric_total'],
            fsc_marks=validated_data['fsc_marks'],
            fsc_total=validated_data['fsc_total'],
            tests=tests,
        )

        if not eligibility.eligible:
            raise EligibilityError({'errors': eligibility.errors, 'message': 'Applicant does not meet the minimum eligibility requirement.'})

        applicant = PISTApplicant.objects.create(
            full_name=validated_data['full_name'],
            father_name=validated_data['father_name'],
            cnic=validated_data['cnic'],
            email=validated_data['email'],
            phone=validated_data['phone'],
            address=validated_data['address'],
            profile_photo=profile_photo_file,
            matric_marks=validated_data['matric_marks'],
            matric_total=validated_data['matric_total'],
            fsc_marks=validated_data['fsc_marks'],
            fsc_total=validated_data['fsc_total'],
            campus=campus,
            program=program,
            source_application_id=validated_data['source_application_id'],
            nationality=validated_data.get('nationality', ''),
            passport_number=validated_data.get('passport_number', ''),
            visa_information=validated_data.get('visa_information', ''),
            international_address=validated_data.get('international_address', ''),
            country=validated_data.get('country', ''),
            status=PISTApplicant.Status.RECEIVED,
            eligibility_status=PISTApplicant.EligibilityStatus.ELIGIBLE,
        )

        for test in tests:
            ApplicantTestScore.objects.create(
                applicant=applicant,
                test_type=test['type'],
                score=test['score'],
                max_score=test.get('max_score', 100),
            )

        applicant.test_type = tests[0]['type'] if tests else ''
        applicant.test_score = tests[0]['score'] if tests else None
        applicant.save(update_fields=['test_type', 'test_score', 'eligibility_status', 'updated_at'])

        session = TestSchedulingService.assign(applicant)
        RollNumberService.issue_roll_number(applicant)
        applicant.refresh_from_db()
        return applicant, session, eligibility
