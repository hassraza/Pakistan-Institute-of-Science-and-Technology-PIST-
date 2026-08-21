from __future__ import annotations

import logging
import uuid as uuid_lib

from django.core.exceptions import ValidationError
from django.db.models import Count, Prefetch, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import ApplicationTrackForm
from .models import Campus, Department, PISTApplicant, Program
from .permissions import HasPISTExternalAPIKey
from .serializers import ExternalApplicationSerializer
from .services import ConflictError, EligibilityError, ApplicationProcessingService, ConfigurationError


logger = logging.getLogger(__name__)


def home(request):
    featured_programs = (
        Program.objects.select_related('department', 'department__campus')
        .filter(admissions_open=True)
        .order_by('department__campus__city', 'department__name', 'name')[:6]
    )
    campuses = Campus.objects.filter(is_active=True).annotate(department_count=Count('departments', distinct=True))
    return render(
        request,
        'admissions/home.html',
        {
            'featured_programs': featured_programs,
            'campuses': campuses,
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


def programs(request):
    program_qs = Program.objects.select_related('department', 'department__campus')
    campus_code = request.GET.get('campus')
    if campus_code:
        program_qs = program_qs.filter(department__campus__code=campus_code)
    return render(request, 'admissions/programs.html', {'programs': program_qs, 'campus_code': campus_code})


def program_detail(request, program_slug):
    program = get_object_or_404(Program.objects.select_related('department', 'department__campus'), slug=program_slug)
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
            'career_opportunities': career_opportunities.get(program.department.name.replace('Department of ', ''), 'Career outcomes aligned with the program and sector demand.'),
            'procedure_steps': [
                'Review the eligibility criteria',
                'Complete the external application',
                'PIST validates eligibility and test requirements',
                'Roll number and test session are assigned',
                'Download the roll slip and appear in the entry test',
            ],
        },
    )


def admission_procedure(request):
    steps = [
        'Create Profile',
        'Enter Academic Information',
        'Search Universities',
        'Select PIST',
        'Select Campus / Department / Program',
        'Submit Application',
        'Central Portal Sends Application to PIST',
        'PIST Validates Eligibility',
        'PIST Generates Roll Number',
        'Entry Test Is Scheduled',
        'Digital Roll Slip Generated',
        'Candidate Appears in Entry Test',
        'Application Moves Through Admission Process',
        'Merit List',
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
                Q(roll_number=reference) | Q(source_application_id=reference)
            ).first()
    return render(request, 'admissions/track_application.html', {'form': form, 'application': application})


def roll_slip(request, application_uuid):
    applicant = get_object_or_404(
        PISTApplicant.objects.select_related('campus', 'program__department'),
        pk=application_uuid,
    )
    verification_url = request.build_absolute_uri(f'/verify/{applicant.pk}/')
    return render(request, 'admissions/roll_slip.html', {'application': applicant, 'verification_url': verification_url})


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


def research(request):
    return render(
        request,
        'admissions/info_page.html',
        {
            'page_title': 'Research',
            'headline': 'Applied research and academic inquiry',
            'body': 'PIST research content is intentionally concise in this FYP demo while preserving the structure expected from a serious university website.',
        },
    )


def student_life(request):
    return render(
        request,
        'admissions/info_page.html',
        {
            'page_title': 'Student Life',
            'headline': 'Student support, co-curricular activity, and campus services',
            'body': 'This section illustrates how a university can present student services, societies, and support pathways in a credible institutional format.',
        },
    )


def contact(request):
    return render(
        request,
        'admissions/info_page.html',
        {
            'page_title': 'Contact PIST',
            'headline': 'Admission Office and campus contact information',
            'body': 'Use this page to surface campus-specific contact details, office timings, and admission support contacts from the database.',
        },
    )


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

        application = (
            PISTApplicant.objects.select_related('campus', 'program__department')
            .filter(Q(pk=reference) | Q(roll_number=reference) | Q(source_application_id=reference))
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
