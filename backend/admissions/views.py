from __future__ import annotations

import logging
import uuid as uuid_lib
from io import BytesIO

import qrcode
from django.core.exceptions import ValidationError
from django.db.models import Count, Prefetch, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import ApplicationTrackForm
from .models import Campus, Department, PISTApplicant, Program, RollSlip
from .permissions import HasPISTExternalAPIKey
from .serializers import ExternalApplicationSerializer
from .services import ConflictError, EligibilityError, ApplicationProcessingService, ConfigurationError


logger = logging.getLogger(__name__)


def home(request):
    featured_programs = (
        Program.objects.select_related('department', 'department__campus', 'campus', 'required_qualification')
        .prefetch_related('eligibility_rules__qualification', 'test_requirements__test_type')
        .filter(admissions_open=True)
        .order_by('department__campus__city', 'department__name', 'name')[:6]
    )
    campuses = Campus.objects.filter(is_active=True).annotate(
        department_count=Count('departments', distinct=True),
        program_count=Count('programs', distinct=True),
    )
    departments = Department.objects.filter(is_active=True).prefetch_related('programs').order_by('name')
    department_groups = {
        'Computing and Technology': {'Computer Science', 'Software Engineering', 'Artificial Intelligence', 'Data Science', 'Information Technology', 'Cyber Security'},
        'Engineering': {'Electrical Engineering', 'Mechanical Engineering', 'Civil Engineering', 'Chemical Engineering', 'Biomedical Engineering'},
        'Health Sciences': {'Health and Medical Sciences', 'Pharmacy'},
        'Management and Business': {'Management Sciences', 'Accounting and Finance', 'Economics'},
        'Natural Sciences': {'Mathematics', 'Physics', 'Biotechnology', 'Environmental Sciences'},
        'Social Sciences and Law': {'Psychology', 'Media and Communication', 'Law', 'International Relations'},
    }
    grouped_departments = []
    for label, names in department_groups.items():
        matching = [department for department in departments if department.name.removeprefix('Department of ') in names]
        if matching:
            grouped_departments.append({'label': label, 'departments': matching})
    return render(
        request,
        'admissions/home.html',
        {
            'featured_programs': featured_programs,
            'campuses': campuses,
            'departments': departments,
            'department_groups': grouped_departments,
            'campus_count': campuses.count(),
            'department_count': departments.count(),
            'program_count': Program.objects.count(),
            'open_program_count': Program.objects.filter(admissions_open=True).count(),
            'open_admissions': Program.objects.filter(admissions_open=True).exists(),
        },
    )


def about(request):
    return render(
        request,
        'admissions/info_page.html',
        {
            'page_title': 'About PIST',
            'headline': 'Fictional academic institution for admission ecosystem demonstration',
            'body': 'PIST is a fictional institution created as part of a final year project to demonstrate a realistic university admissions and student management workflow.',
        },
    )


def campuses(request):
    campus_qs = Campus.objects.filter(is_active=True).annotate(
        department_count=Count('departments', distinct=True),
        program_count=Count('departments__programs', distinct=True),
    )
    return render(request, 'admissions/campuses.html', {'campuses': campus_qs})


def campus_detail(request, campus_code):
    campus = get_object_or_404(
        Campus.objects.prefetch_related(
            Prefetch('departments', queryset=Department.objects.filter(is_active=True).prefetch_related('programs'))
        ),
        code=campus_code,
    )
    return render(request, 'admissions/campus_detail.html', {'campus': campus})


def departments(request):
    department_qs = Department.objects.select_related('campus').prefetch_related('programs').filter(is_active=True)
    return render(request, 'admissions/departments.html', {'departments': department_qs})


def department_detail(request, department_slug):
    department = get_object_or_404(Department.objects.select_related('campus').prefetch_related('programs'), slug=department_slug, is_active=True)
    return render(request, 'admissions/department_detail.html', {'department': department})


def programs(request):
    program_qs = Program.objects.select_related('department', 'department__campus', 'campus', 'required_qualification').prefetch_related('eligibility_rules__qualification', 'test_requirements__test_type')
    
    campus_code = request.GET.get('campus', '')
    department_code = request.GET.get('department', '')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '').strip()
    
    if campus_code:
        program_qs = program_qs.filter(campus__code=campus_code)
    if department_code:
        program_qs = program_qs.filter(department__code=department_code)
    if status_filter == 'open':
        program_qs = program_qs.filter(admissions_open=True)
    elif status_filter == 'closed':
        program_qs = program_qs.filter(admissions_open=False)
    if search_query:
        program_qs = program_qs.filter(name__icontains=search_query)
        
    active_campuses = Campus.objects.filter(is_active=True).order_by('name')
    active_departments = Department.objects.filter(is_active=True).order_by('name')
    if campus_code:
        active_departments = active_departments.filter(campus__code=campus_code)
        
    context = {
        'programs': program_qs,
        'campus_code': campus_code,
        'department_code': department_code,
        'status_filter': status_filter,
        'search_query': search_query,
        'active_campuses': active_campuses,
        'active_departments': active_departments,
    }
    return render(request, 'admissions/programs.html', context)


def program_detail(request, program_slug):
    program = get_object_or_404(Program.objects.select_related('department', 'department__campus', 'campus', 'required_qualification').prefetch_related('eligibility_rules__qualification', 'test_requirements__test_type'), slug=program_slug)
    career_opportunities = {
        'Computer Science': 'Software houses, fintech, product engineering, cloud operations, and graduate studies.',
        'Electrical & Mechanical Engineering': 'Industrial automation, utilities, manufacturing, maintenance, and design roles.',
        'Health & Medical Sciences': 'Hospitals, laboratories, community health, pharmaceutical practice, and higher study.',
        'Management Sciences': 'Banks, consulting firms, corporate operations, finance, and entrepreneurship.',
    }
    return render(
        request,
        'admissions/program_detail.html',
        {
            'program': program,
            'student_application': (
                PISTApplicant.objects.filter(
                    student=request.user.student_profile,
                    program=program,
                ).exclude(application_status=PISTApplicant.ApplicationStatus.WITHDRAWN).first()
                if request.user.is_authenticated and hasattr(request.user, 'student_profile') else None
            ),
            'career_opportunities': program.career_opportunities or career_opportunities.get(program.department.name.replace('Department of ', ''), 'Career outcomes aligned with the program and sector demand.'),
            'procedure_steps': [
                'Create a student account and complete your profile',
                'Add academic information and upload documents',
                'Check eligibility and apply through the Student Portal',
                'Receive an Application ID while the application is processed',
                'Download the roll slip after the roll number and test schedule are issued',
            ],
        },
    )


def admission_procedure(request):
    steps = [
        'Create Student Account',
        'Complete Profile',
        'Add Academic Information',
        'Upload Academic Documents',
        'Explore Programs',
        'Check Eligibility',
        'Apply for Program',
        'Receive Application ID',
        'Application is processed',
        'Receive Roll Number and Test Schedule',
        'Download Roll Slip',
    ]
    return render(request, 'admissions/admission_procedure.html', {'steps': steps})


def track_application(request):
    form = ApplicationTrackForm(request.GET or None)
    application = None
    if form.is_valid():
        reference = form.cleaned_data['reference'].strip()
        try:
            application = PISTApplicant.objects.select_related('campus', 'program__department').get(pk=reference)
        except (PISTApplicant.DoesNotExist, ValidationError, ValueError, TypeError):
            application = PISTApplicant.objects.select_related('campus', 'program__department').filter(
                Q(application_id__iexact=reference)
                | Q(program_registration_id__iexact=reference)
                | Q(roll_number__iexact=reference)
                | Q(source_application_id__iexact=reference)
            ).first()
    return render(request, 'admissions/track_application.html', {'form': form, 'application': application})


def roll_slip(request, application_uuid):
    applicant = get_object_or_404(
        PISTApplicant.objects.select_related('campus', 'program__department', 'student', 'test_session'),
        pk=application_uuid,
    )
    if applicant.student_id is None and not request.user.is_authenticated:
        return render(request, 'admissions/roll_slip.html', {'application': applicant, 'roll_slip': None, 'verification_url': request.build_absolute_uri(reverse('admissions:verify_application', kwargs={'application_uuid': applicant.pk}))})
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login

        return redirect_to_login(request.get_full_path(), reverse('students:login'))
    if not (request.user.is_staff or applicant.student_id == getattr(getattr(request.user, 'student_profile', None), 'pk', None)):
        return render(request, 'errors/403.html', status=403)
    if not applicant.roll_number or not applicant.test_session_id:
        return render(request, 'admissions/roll_slip.html', {'application': applicant, 'roll_slip': None, 'verification_url': request.build_absolute_uri(reverse('admissions:verify_application', kwargs={'application_uuid': applicant.pk}))})
    slip, _ = RollSlip.objects.get_or_create(
        application=applicant,
        defaults={'roll_number': applicant.roll_number or '', 'test_session_id': applicant.test_session_id},
    )
    verification_url = request.build_absolute_uri(reverse('admissions:verify_roll_slip', kwargs={'qr_token': slip.qr_token}))
    return render(request, 'admissions/roll_slip.html', {'application': applicant, 'roll_slip': slip, 'verification_url': verification_url})


def roll_slip_qr(request, application_uuid):
    applicant = get_object_or_404(PISTApplicant, pk=application_uuid)
    slip = get_object_or_404(RollSlip, application=applicant)
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login

        return redirect_to_login(request.get_full_path(), reverse('students:login'))
    if not (request.user.is_staff or applicant.student_id == getattr(getattr(request.user, 'student_profile', None), 'pk', None)):
        return render(request, 'errors/403.html', status=403)
    image = qrcode.make(request.build_absolute_uri(reverse('admissions:verify_roll_slip', kwargs={'qr_token': slip.qr_token})))
    output = BytesIO()
    image.save(output, format='PNG')
    return HttpResponse(output.getvalue(), content_type='image/png')


def verify_application(request, application_uuid):
    try:
        application_uuid_obj = uuid_lib.UUID(str(application_uuid))
    except (TypeError, ValueError):
        return render(request, 'admissions/invalid_verification.html', {'reference': application_uuid}, status=404)

    applicant = PISTApplicant.objects.select_related('campus', 'program__department').filter(pk=application_uuid_obj).first()
    if applicant is None:
        return render(request, 'admissions/invalid_verification.html', {'reference': application_uuid}, status=404)

    payload = {
        'success': True,
        'application_uuid': str(applicant.pk),
        'roll_number': applicant.roll_number,
        'full_name': applicant.full_name,
        'campus': applicant.campus.name,
        'program': applicant.program.name,
        'status': applicant.status,
        'test_date': applicant.test_date.isoformat() if applicant.test_date else None,
    }

    if request.headers.get('Accept', '').startswith('application/json'):
        return JsonResponse(payload)

    return render(request, 'admissions/verify_application.html', {'application': applicant, 'verification': payload})


def verify_roll_slip(request, qr_token):
    try:
        token = uuid_lib.UUID(str(qr_token))
    except (TypeError, ValueError):
        return render(request, 'admissions/invalid_verification.html', status=404)
    slip = RollSlip.objects.select_related('application__program', 'application__campus').filter(qr_token=token).first()
    if slip is None:
        return render(request, 'admissions/invalid_verification.html', status=404)
    application = slip.application
    return render(request, 'admissions/verify_roll_slip.html', {'application': application, 'roll_slip': slip})


def research(request):
    return render(request, 'admissions/research.html')


def student_life(request):
    return render(request, 'admissions/student_life.html')


def contact(request):
    campuses = Campus.objects.filter(is_active=True).order_by('name')
    return render(request, 'admissions/contact.html', {'campuses': campuses})


class ExternalApplicationAPIView(APIView):
    permission_classes = [HasPISTExternalAPIKey]

    def post(self, request):
        serializer = ExternalApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            applicant, session, _eligibility = ApplicationProcessingService.process_external_application(
                validated_data=serializer.validated_data
            )
        except ConflictError as exc:
            logger.warning('Duplicate application received for source_application_id=%s', request.data.get('source_application_id'))
            return Response({'success': False, 'message': str(exc.detail)}, status=exc.status_code)
        except EligibilityError as exc:
            logger.info('Eligibility failure for source_application_id=%s', request.data.get('source_application_id'))
            detail = exc.detail
            if isinstance(detail, dict):
                message = detail.pop('message', 'Applicant does not meet the minimum eligibility requirement.')
                return Response({'success': False, 'message': message, 'errors': detail}, status=exc.status_code)
            return Response({'success': False, 'message': str(detail)}, status=exc.status_code)
        except ConfigurationError as exc:
            logger.exception('Admission configuration error while processing source_application_id=%s', request.data.get('source_application_id'))
            return Response({'success': False, 'message': str(exc.detail)}, status=exc.status_code)

        roll_slip_url = reverse('admissions:roll_slip', kwargs={'application_uuid': applicant.pk})
        response_data = {
            'success': True,
            'message': 'Application successfully received by PIST.',
            'application_uuid': str(applicant.pk),
            'roll_number': applicant.roll_number,
            'status': applicant.status,
            'test_date': applicant.test_date.isoformat() if applicant.test_date else None,
            'reporting_time': applicant.reporting_time.strftime('%I:%M %p') if applicant.reporting_time else None,
            'test_venue': applicant.test_venue,
            'test_building': applicant.test_building,
            'test_hall': applicant.test_hall,
            'roll_slip_url': roll_slip_url,
        }
        logger.info('External application accepted for roll_number=%s', applicant.roll_number)
        return Response(response_data, status=status.HTTP_201_CREATED)


class PublicSiteAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        campuses = Campus.objects.filter(is_active=True).prefetch_related('departments__programs').order_by('city', 'name')
        campus_payload = []
        for campus in campuses:
            campus_payload.append(
                {
                    'name': campus.name,
                    'city': campus.city,
                    'code': campus.code,
                    'address': campus.address,
                    'admissions_open': campus.admissions_open,
                    'departments': [
                        {
                            'name': department.name,
                            'slug': department.slug,
                            'program_count': department.programs.count(),
                        }
                        for department in campus.departments.filter(is_active=True)
                    ],
                }
            )

        programs = (
            Program.objects.select_related('department', 'department__campus')
            .filter(admissions_open=True, department__campus__is_active=True)
            .order_by('department__campus__city', 'department__name', 'name')[:12]
        )
        program_payload = [
            {
                'name': program.name,
                'slug': program.slug,
                'code': program.code,
                'campus_code': program.department.campus.code,
                'campus_name': program.department.campus.name,
                'department': program.department.name,
                'duration': program.duration,
                'required_test_type': program.required_test_type,
                'eligibility_percentage': float(program.eligibility_percentage),
                'admissions_open': program.admissions_open,
            }
            for program in programs
        ]

        return Response(
            {
                'site_name': 'Pakistan Institute of Science and Technology',
                'campus_count': len(campus_payload),
                'admissions_open_count': len(program_payload),
                'campuses': campus_payload,
                'featured_programs': program_payload,
            }
        )


class PublicApplicationLookupAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        reference = request.query_params.get('reference', '').strip()
        if not reference:
            return Response({'success': False, 'message': 'Reference is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            application = PISTApplicant.objects.select_related('campus', 'program__department').get(pk=reference)
        except (PISTApplicant.DoesNotExist, ValidationError, ValueError, TypeError):
            application = (
                PISTApplicant.objects.select_related('campus', 'program__department')
                .filter(
                    Q(application_id__iexact=reference)
                    | Q(program_registration_id__iexact=reference)
                    | Q(roll_number__iexact=reference)
                    | Q(source_application_id__iexact=reference)
                )
                .first()
            )

        if application is None:
            return Response({'success': False, 'message': 'No matching application was found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                'success': True,
                'application_uuid': str(application.pk),
                'full_name': application.full_name,
                'campus': application.campus.name,
                'campus_code': application.campus.code,
                'program': application.program.name,
                'program_code': application.program.code,
                'roll_number': application.roll_number,
                'status': application.status,
                'test_date': application.test_date.isoformat() if application.test_date else None,
                'reporting_time': application.reporting_time.strftime('%I:%M %p') if application.reporting_time else None,
                'test_venue': application.test_venue,
                'test_building': application.test_building,
                'test_hall': application.test_hall,
                'roll_slip_url': reverse('admissions:roll_slip', kwargs={'application_uuid': application.pk}),
                'verification_url': reverse('admissions:verify_application', kwargs={'application_uuid': application.pk}),
            }
        )


def page_not_found(request, exception):
    return render(request, 'errors/404.html', status=404)


def permission_denied(request, exception):
    return render(request, 'errors/403.html', status=403)


def server_error(request):
    return render(request, 'errors/500.html', status=500)
