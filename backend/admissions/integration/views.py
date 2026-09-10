from __future__ import annotations

import logging
import re
import secrets
import string
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction, models
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from admissions.models import PISTApplicant, Program, RollSlip
from admissions.services import (
    RollNumberService,
    TestSchedulingService,
    current_admission_year,
    generate_program_registration_id,
)
from students.models import StudentProfile, Notification, AcademicDocument
from students.services import generate_student_id
from .authentication import APIKeyAuthentication, HasAPIKeyPermission
from .serializers import (
    ApplicationCreateInputSerializer,
    ApplicationCreateOutputSerializer,
    ApplicationStatusOutputSerializer,
    DocumentUploadInputSerializer,
    DocumentUploadOutputSerializer,
    ErrorResponseSerializer,
    NotificationOutputSerializer,
    RollSlipOutputSerializer,
    StudentCreateInputSerializer,
    StudentCreateOutputSerializer,
)

logger = logging.getLogger(__name__)


def generate_unique_username(email: str, full_name: str, requested_username: str = '') -> str:
    """Generate or clean a unique username for a student."""
    user_model = get_user_model()
    candidate = ''

    if requested_username:
        candidate = re.sub(r'[^a-zA-Z0-9_]', '', requested_username).lower()

    if not candidate or len(candidate) < 3:
        email_prefix = email.split('@')[0]
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '', email_prefix).lower()
        candidate = cleaned if len(cleaned) >= 3 else re.sub(r'[^a-zA-Z0-9]', '', full_name.split()[0]).lower() or 'student'

    base = candidate
    counter = 1
    while user_model.objects.filter(username=candidate).exists():
        candidate = f"{base}{counter}"
        counter += 1
    return candidate


def generate_secure_password(length: int = 12) -> str:
    """Generate a high-entropy secure random password."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    reqs = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    remaining = [secrets.choice(chars) for _ in range(length - len(reqs))]
    combined = reqs + remaining
    secrets.SystemRandom().shuffle(combined)
    return ''.join(combined)


def resolve_student(student_identifier: str | int) -> StudentProfile | None:
    """Resolve a StudentProfile from numeric user ID, student_id string, UUID, or CNIC."""
    val = str(student_identifier).strip()
    if not val:
        return None

    # 1. By student_id CharField (e.g. 'PIST-STU-2026-0001')
    student = StudentProfile.objects.select_related('user').filter(student_id__iexact=val).first()
    if student:
        return student

    # 2. By User ID (integer)
    if val.isdigit():
        student = StudentProfile.objects.select_related('user').filter(user_id=int(val)).first()
        if student:
            return student

    # 3. By UUID primary key
    try:
        uuid_obj = uuid.UUID(val)
        student = StudentProfile.objects.select_related('user').filter(id=uuid_obj).first()
        if student:
            return student
    except (ValueError, TypeError):
        pass

    # 4. By CNIC
    student = StudentProfile.objects.select_related('user').filter(cnic=val).first()
    if student:
        return student

    # 5. By user email
    student = StudentProfile.objects.select_related('user').filter(user__email__iexact=val).first()
    return student


def resolve_application(application_identifier: str | int) -> PISTApplicant | None:
    """Resolve an Application/PISTApplicant from numeric ID, application_id string, or UUID."""
    val = str(application_identifier).strip()
    if not val:
        return None

    # 1. If numeric, lookup by application_number
    if val.isdigit():
        app = (
            PISTApplicant.objects.select_related('program', 'campus', 'student', 'student__user', 'roll_slip', 'roll_slip__test_session__test_center')
            .filter(application_number=int(val))
            .first()
        )
        if app:
            return app

    # 2. By application_id CharField (e.g. APP-2026-XXXX)
    app = (
        PISTApplicant.objects.select_related('program', 'campus', 'student', 'student__user', 'roll_slip', 'roll_slip__test_session__test_center')
        .filter(application_id__iexact=val)
        .first()
    )
    if app:
        return app

    # 3. By source_application_id or program_registration_id
    app = (
        PISTApplicant.objects.select_related('program', 'campus', 'student', 'student__user', 'roll_slip', 'roll_slip__test_session__test_center')
        .filter(models.Q(program_registration_id__iexact=val) | models.Q(source_application_id__iexact=val))
        .first()
    )
    if app:
        return app

    # 4. By UUID primary key
    try:
        uuid_obj = uuid.UUID(val)
        app = (
            PISTApplicant.objects.select_related('program', 'campus', 'student', 'student__user', 'roll_slip', 'roll_slip__test_session__test_center')
            .filter(pk=uuid_obj)
            .first()
        )
        if app:
            return app
    except (ValueError, TypeError):
        pass

    return None


class StudentCreateAPIView(APIView):
    """
    Endpoint for PakUniPortal to create a student account in PIST.
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKeyPermission]

    @extend_schema(
        tags=['Integration (PakUniPortal)'],
        summary='Create Student Account',
        description=(
            'Creates a verified student account inside PIST. Supports both minimal PIST payload '
            'and rich PakUniPortal profile payload. Automatically generates unique username and secure password, '
            'links StudentProfile, and creates an initial welcome notification.'
        ),
        request=StudentCreateInputSerializer,
        responses={
            201: OpenApiResponse(
                response=StudentCreateOutputSerializer,
                description='Student account created successfully.',
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={
                            'student_id': 'PIST-STU-2026-0002',
                            'pist_student_id': 'PIST-STU-2026-0002',
                            'username': 'ali_khan',
                            'pist_username': 'ali_khan',
                            'password': 'mX8#kL9@pQ2!',
                            'pist_password': 'mX8#kL9@pQ2!',
                        },
                    )
                ],
            ),
            400: OpenApiResponse(response=ErrorResponseSerializer, description='Validation error (e.g. invalid CNIC, missing fields).'),
            401: OpenApiResponse(response=ErrorResponseSerializer, description='Missing or invalid X-API-KEY header.'),
            409: OpenApiResponse(response=ErrorResponseSerializer, description='Duplicate student account (email or CNIC already registered).'),
        },
    )
    def post(self, request):
        serializer = StudentCreateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        full_name = data['resolved_full_name']
        email = data['resolved_email']
        phone = data['resolved_phone']
        cnic = data['resolved_cnic']

        # Idempotency / Duplicate check:
        # Check if student with this email or CNIC already exists
        user_model = get_user_model()
        existing_by_email = user_model.objects.filter(email__iexact=email).first()
        existing_by_cnic = StudentProfile.objects.select_related('user').filter(cnic=cnic).first()

        if existing_by_email or existing_by_cnic:
            existing_profile = existing_by_cnic or getattr(existing_by_email, 'student_profile', None)
            logger.warning('Duplicate student registration attempted for email=%s, cnic=%s', email, cnic)
            return Response(
                {
                    'detail': 'A student account with this email or CNIC already exists.',
                    'code': 'duplicate',
                    'student_id': existing_profile.student_id if existing_profile else '',
                    'pist_student_id': existing_profile.student_id if existing_profile else '',
                    'username': existing_profile.user.username if existing_profile else (existing_by_email.username if existing_by_email else ''),
                },
                status=status.HTTP_409_CONFLICT,
            )

        username = generate_unique_username(email, full_name, data.get('username', ''))
        password = generate_secure_password(12)

        with transaction.atomic():
            user = user_model.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=full_name.split()[0],
                last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
            )
            student_code = generate_student_id()
            profile = StudentProfile.objects.create(
                user=user,
                student_id=student_code,
                full_name=full_name,
                email_verified=True,
                cnic=cnic,
                phone=phone,
                date_of_birth=data.get('date_of_birth'),
                gender=data.get('gender', ''),
                address=data.get('address', ''),
                nationality=data.get('nationality', 'Pakistani') or 'Pakistani',
            )
            # Create a welcome notification for the student
            Notification.objects.create(
                student=profile,
                title='Welcome to PIST Portal',
                message=(
                    f'Welcome to Pakistan Institute of Science and Technology, {full_name}! '
                    'Your account has been connected via PakUniPortal.'
                ),
            )

        logger.info('Created student account %s (User ID: %s) via integration API.', student_code, user.id)
        return Response(
            {
                'student_id': profile.student_id,
                'pist_student_id': profile.student_id,
                'id': profile.student_id,
                'username': user.username,
                'pist_username': user.username,
                'password': password,
                'pist_password': password,
            },
            status=status.HTTP_201_CREATED,
        )


class ApplicationCreateAPIView(APIView):
    """
    Endpoint for PakUniPortal to submit a student application to PIST.
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKeyPermission]

    @extend_schema(
        tags=['Integration (PakUniPortal)'],
        summary='Submit University Application',
        description=(
            'Submits an application for an existing student to a specific degree program. '
            'Automatically initializes status to submitted, allocates a test session and roll number '
            'if available, and issues a student notification.'
        ),
        request=ApplicationCreateInputSerializer,
        responses={
            201: OpenApiResponse(
                response=ApplicationCreateOutputSerializer,
                description='Application created and submitted successfully.',
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={
                            'application_id': 1,
                            'pist_application_id': 1,
                            'student_id': 'PIST-STU-2026-0001',
                            'program_id': 2,
                            'program_name': 'Bachelor of Science in Computer Science',
                            'program_code': 'BSCS-ISB',
                            'status': 'submitted',
                            'application_status': 'submitted',
                            'application_number': 'APP-2026-F91A2B3C',
                            'roll_number': 'PIST-ISB-CS-2026-0001',
                            'created_at': '2026-09-09T12:00:00Z',
                        },
                    )
                ],
            ),
            400: OpenApiResponse(response=ErrorResponseSerializer, description='Invalid request data or admissions closed.'),
            401: OpenApiResponse(response=ErrorResponseSerializer, description='Missing or invalid X-API-KEY header.'),
            404: OpenApiResponse(response=ErrorResponseSerializer, description='Student or program not found.'),
            409: OpenApiResponse(response=ErrorResponseSerializer, description='Duplicate active application exists.'),
        },
    )
    def post(self, request):
        serializer = ApplicationCreateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        student_id_input = serializer.validated_data['student_id']
        program_id_input = serializer.validated_data['program_id']

        student = resolve_student(student_id_input)
        if not student:
            return Response(
                {'detail': f'Student not found matching identifier "{student_id_input}".', 'code': 'not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Resolve Program by ID (if digits), code, or slug
        program = None
        if str(program_id_input).isdigit():
            program = Program.objects.select_related('department', 'department__campus').filter(id=int(program_id_input)).first()
        if not program:
            program = Program.objects.select_related('department', 'department__campus').filter(code__iexact=str(program_id_input)).first()
        if not program:
            program = Program.objects.select_related('department', 'department__campus').filter(slug__iexact=str(program_id_input)).first()

        if not program:
            return Response(
                {'detail': f'Program not found matching identifier "{program_id_input}".', 'code': 'not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not program.admissions_open:
            return Response(
                {'detail': f'Admissions are currently closed for program {program.name}.', 'code': 'admissions_closed'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check for duplicate active application
        existing_app = PISTApplicant.objects.filter(
            student=student,
            program=program,
        ).exclude(application_status=PISTApplicant.ApplicationStatus.WITHDRAWN).first()

        if existing_app:
            return Response(
                {
                    'detail': 'An active application already exists for this student in the selected program.',
                    'code': 'duplicate',
                    'application_id': existing_app.application_number,
                    'pist_application_id': existing_app.application_number,
                },
                status=status.HTTP_409_CONFLICT,
            )

        campus = program.campus or program.department.campus
        reg_id = generate_program_registration_id(program)
        app_id = f'APP-{current_admission_year()}-{uuid.uuid4().hex[:8].upper()}'

        matric = getattr(student, 'matric_record', None)
        intermediate = getattr(student, 'intermediate_record', None)

        with transaction.atomic():
            applicant = PISTApplicant.objects.create(
                student=student,
                application_id=app_id,
                source_application_id=app_id,
                program_registration_id=reg_id,
                application_status=PISTApplicant.ApplicationStatus.SUBMITTED,
                eligibility_status=PISTApplicant.EligibilityStatus.ELIGIBLE,
                full_name=student.full_name,
                father_name=student.father_name or '',
                cnic=student.cnic,
                email=student.user.email,
                phone=student.phone,
                address=student.address or '',
                matric_marks=matric.obtained_marks if matric else 0,
                matric_total=matric.total_marks if matric else 100,
                fsc_marks=intermediate.obtained_marks if intermediate else 0,
                fsc_total=intermediate.total_marks if intermediate else 100,
                campus=campus,
                program=program,
                status=PISTApplicant.Status.RECEIVED,
            )

            # Attempt automated entry test session allocation and roll number generation
            try:
                TestSchedulingService.assign(applicant, submitted_at=timezone.now())
                RollNumberService.issue_roll_number(applicant)
                applicant.refresh_from_db()
            except Exception as e:
                logger.info('Immediate scheduling not available for application %s: %s', applicant.application_id, e)

            # Create in-portal notification
            Notification.objects.create(
                student=student,
                title='Application Submitted',
                message=(
                    f'Your application for {program.name} ({program.code}) has been successfully received. '
                    f'Application Reference: {applicant.application_id}.'
                ),
            )

        logger.info('Created application %s (App Number: %s) for student %s.', applicant.application_id, applicant.application_number, student.student_id)

        response_payload = {
            'application_id': applicant.application_number,
            'pist_application_id': applicant.application_number,
            'id': applicant.application_number,
            'student_id': student.student_id,
            'program_id': program.id,
            'program_name': program.name,
            'program_code': program.code,
            'status': 'submitted',
            'application_status': 'submitted',
            'application_number': applicant.application_id,
            'roll_number': applicant.roll_number,
            'created_at': applicant.created_at,
        }
        return Response(response_payload, status=status.HTTP_201_CREATED)


class ApplicationStatusAPIView(APIView):
    """
    Endpoint for retrieving the current status of an application.
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKeyPermission]

    STATUS_MAPPING = {
        PISTApplicant.ApplicationStatus.SUBMITTED: 'submitted',
        PISTApplicant.ApplicationStatus.UNDER_REVIEW: 'under_review',
        PISTApplicant.ApplicationStatus.SCHEDULED: 'scheduled',
        PISTApplicant.ApplicationStatus.ACCEPTED: 'accepted',
        PISTApplicant.ApplicationStatus.REJECTED: 'rejected',
        PISTApplicant.ApplicationStatus.WITHDRAWN: 'withdrawn',
    }

    @extend_schema(
        tags=['Integration (PakUniPortal)'],
        summary='Get Application Status',
        description='Returns the current processing status of an application given its numeric or string identifier.',
        responses={
            200: OpenApiResponse(
                response=ApplicationStatusOutputSerializer,
                description='Application status retrieved successfully.',
                examples=[
                    OpenApiExample(
                        'Status Response',
                        value={
                            'application_id': 1,
                            'pist_application_id': 1,
                            'status': 'under_review',
                            'application_status': 'under_review',
                        },
                    )
                ],
            ),
            401: OpenApiResponse(response=ErrorResponseSerializer, description='Missing or invalid X-API-KEY header.'),
            404: OpenApiResponse(response=ErrorResponseSerializer, description='Application not found.'),
        },
    )
    def get(self, request, application_id):
        application = resolve_application(application_id)
        if not application:
            return Response(
                {'detail': f'Application not found for identifier "{application_id}".', 'code': 'not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        mapped_status = self.STATUS_MAPPING.get(application.application_status, application.application_status.lower())
        return Response(
            {
                'application_id': application.application_number or 1,
                'pist_application_id': application.application_number or 1,
                'id': application.application_number or 1,
                'status': mapped_status,
                'application_status': mapped_status,
            },
            status=status.HTTP_200_OK,
        )


class StudentNotificationsAPIView(APIView):
    """
    Endpoint for fetching all notifications belonging to a student.
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKeyPermission]

    @extend_schema(
        tags=['Integration (PakUniPortal)'],
        summary='Get Student Notifications',
        description='Returns all system and admission notifications sent to a specific student account.',
        responses={
            200: OpenApiResponse(
                response=NotificationOutputSerializer(many=True),
                description='List of notifications belonging to the student.',
                examples=[
                    OpenApiExample(
                        'Notifications Response',
                        value=[
                            {
                                'id': 1,
                                'notification_id': 1,
                                'title': 'Welcome to PIST Portal',
                                'message': 'Welcome to Pakistan Institute of Science and Technology!',
                                'body': 'Welcome to Pakistan Institute of Science and Technology!',
                                'type': 'admission',
                                'notification_type': 'admission',
                                'is_read': False,
                                'created_at': '2026-09-09T12:00:00Z',
                            }
                        ],
                    )
                ],
            ),
            401: OpenApiResponse(response=ErrorResponseSerializer, description='Missing or invalid X-API-KEY header.'),
            404: OpenApiResponse(response=ErrorResponseSerializer, description='Student not found.'),
        },
    )
    def get(self, request, student_id):
        student = resolve_student(student_id)
        if not student:
            return Response(
                {'detail': f'Student not found for identifier "{student_id}".', 'code': 'not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        notifications = student.notifications.all().order_by('-created_at')
        serializer = NotificationOutputSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RollSlipAPIView(APIView):
    """
    Endpoint for fetching entry test roll slip details for an application.
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKeyPermission]

    @extend_schema(
        tags=['Integration (PakUniPortal)'],
        summary='Get Roll Slip Information',
        description=(
            'Returns roll number, test date, and examination venue for a given application. '
            'If roll slip has not been generated yet, returns empty roll slip info.'
        ),
        responses={
            200: OpenApiResponse(
                response=RollSlipOutputSerializer,
                description='Roll slip information retrieved successfully.',
                examples=[
                    OpenApiExample(
                        'Roll Slip Response',
                        value={
                            'roll_number': 'PIST-ISB-CS-2026-0001',
                            'rollNumber': 'PIST-ISB-CS-2026-0001',
                            'test_date': '2026-09-20',
                            'venue': 'Academic Block A, Hall 3, Islamabad Campus',
                        },
                    )
                ],
            ),
            401: OpenApiResponse(response=ErrorResponseSerializer, description='Missing or invalid X-API-KEY header.'),
            404: OpenApiResponse(response=ErrorResponseSerializer, description='Application not found.'),
        },
    )
    def get(self, request, application_id):
        application = resolve_application(application_id)
        if not application:
            return Response(
                {'detail': f'Application not found for identifier "{application_id}".', 'code': 'not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        slip = getattr(application, 'roll_slip', None)
        if not slip and application.roll_number:
            slip = RollSlip.objects.filter(roll_number=application.roll_number).first()

        # If not yet generated, return empty roll slip fields with 200 OK so sync services don't crash
        if not slip or not slip.roll_number or not slip.test_date:
            return Response(
                {
                    'roll_number': '',
                    'rollNumber': '',
                    'test_date': '',
                    'venue': '',
                    'slip_url': '',
                    'qr_url': '',
                    'detail': 'Roll slip has not been generated for this application yet.',
                },
                status=status.HTTP_200_OK,
            )

        slip_path = f"/admissions/roll-slip/{application.id}/"
        qr_path = f"/admissions/roll-slip/{application.id}/qr.png"
        slip_url = request.build_absolute_uri(slip_path)
        qr_url = request.build_absolute_uri(qr_path)

        serializer = RollSlipOutputSerializer({
            'roll_number': slip.roll_number,
            'rollNumber': slip.roll_number,
            'test_date': str(slip.test_date) if slip.test_date else '',
            'venue': slip.venue or '',
            'slip_url': slip_url,
            'qr_url': qr_url,
        })
        return Response(serializer.data, status=status.HTTP_200_OK)


class DocumentUploadAPIView(APIView):
    """
    Endpoint for uploading student documents from external portals (e.g. PakUniPortal Vault).
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKeyPermission]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=['Integration (PakUniPortal)'],
        summary='Upload Student Document',
        description='Uploads an academic document or profile photo for a student from an external portal.',
        request=DocumentUploadInputSerializer,
        responses={
            201: OpenApiResponse(response=DocumentUploadOutputSerializer, description='Document uploaded successfully.'),
            400: OpenApiResponse(response=ErrorResponseSerializer, description='Invalid payload or unsupported document type.'),
            401: OpenApiResponse(response=ErrorResponseSerializer, description='Missing or invalid API key.'),
            404: OpenApiResponse(response=ErrorResponseSerializer, description='Student not found.'),
        },
    )
    def post(self, request):
        serializer = DocumentUploadInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'detail': serializer.errors, 'code': 'invalid_input'}, status=status.HTTP_400_BAD_REQUEST)

        student_identifier = serializer.validated_data['student_id']
        raw_doc_type = serializer.validated_data['document_type'].strip().upper()
        uploaded_file = serializer.validated_data['file']

        student = resolve_student(student_identifier)
        if not student:
            app = resolve_application(student_identifier)
            if app and app.student:
                student = app.student

        if not student:
            return Response(
                {'detail': f'Student not found for identifier "{student_identifier}".', 'code': 'not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        type_mapping = {
            'CNIC': AcademicDocument.DocumentType.CNIC_BFORM,
            'CNIC_FRONT': AcademicDocument.DocumentType.CNIC_BFORM,
            'CNIC_BACK': AcademicDocument.DocumentType.CNIC_BFORM,
            'CNIC_BFORM': AcademicDocument.DocumentType.CNIC_BFORM,
            'MATRIC': AcademicDocument.DocumentType.MATRIC_RESULT,
            'MATRIC_RESULT': AcademicDocument.DocumentType.MATRIC_RESULT,
            'MATRIC_MARKSHEET': AcademicDocument.DocumentType.MATRIC_RESULT,
            'FSC': AcademicDocument.DocumentType.FSC_RESULT,
            'FSC_RESULT': AcademicDocument.DocumentType.FSC_RESULT,
            'INTER_RESULT': AcademicDocument.DocumentType.FSC_RESULT,
            'INTERMEDIATE': AcademicDocument.DocumentType.FSC_RESULT,
            'ENTRY_TEST': AcademicDocument.DocumentType.ENTRY_TEST_RESULT,
            'ENTRY_TEST_RESULT': AcademicDocument.DocumentType.ENTRY_TEST_RESULT,
            'PHOTO': 'PHOTO',
            'PROFILE_PHOTO': 'PHOTO',
            'PICTURE': 'PHOTO',
            'OTHER': AcademicDocument.DocumentType.OTHER,
        }

        mapped_type = type_mapping.get(raw_doc_type, AcademicDocument.DocumentType.OTHER)

        try:
            if mapped_type == 'PHOTO':
                student.profile_photo = uploaded_file
                student.save(update_fields=['profile_photo', 'updated_at'])
                return Response({
                    'success': True,
                    'document_id': str(student.id),
                    'document_type': 'PHOTO',
                    'file_name': uploaded_file.name,
                    'message': 'Profile photo updated successfully.',
                }, status=status.HTTP_201_CREATED)

            doc, _created = AcademicDocument.objects.update_or_create(
                student=student,
                document_type=mapped_type,
                defaults={
                    'file': uploaded_file,
                    'file_name': uploaded_file.name,
                    'verification_status': AcademicDocument.VerificationStatus.VERIFIED,
                },
            )
            return Response({
                'success': True,
                'document_id': str(doc.id),
                'document_type': doc.document_type,
                'file_name': doc.file_name,
                'message': f'{doc.get_document_type_display()} uploaded successfully.',
            }, status=status.HTTP_201_CREATED)
        except Exception as exc:
            logger.exception('Document upload failed for student %s: %s', student.student_id, exc)
            return Response({'detail': str(exc), 'code': 'upload_failed'}, status=status.HTTP_400_BAD_REQUEST)

