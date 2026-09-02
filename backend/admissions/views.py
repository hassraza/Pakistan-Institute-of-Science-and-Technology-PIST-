from __future__ import annotations

import json
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
    departments = Department.objects.select_related('campus').filter(is_active=True).prefetch_related('programs').order_by('name')

    department_groups_config = [
        ('Computing and Technology', [
            'Department of Computer Science',
            'Department of Software Engineering',
        ]),
        ('Engineering', [
            'Department of Electrical Engineering',
            'Department of Mechanical Engineering',
            'Department of Civil Engineering',
            'Department of Chemical Engineering',
            'Department of Biomedical Engineering',
        ]),
        ('Health Sciences', [
            'Department of Health and Medical Sciences',
            'Department of Pharmacy',
        ]),
        ('Management and Business', [
            'Department of Management Sciences',
            'Department of Accounting and Finance',
            'Department of Economics',
        ]),
        ('Natural Sciences', [
            'Department of Mathematics',
            'Department of Physics',
            'Department of Biotechnology',
            'Department of Environmental Sciences',
        ]),
        ('Social Sciences and Law', [
            'Department of Psychology',
            'Department of Media and Communication',
            'Department of Law',
            'Department of International Relations',
        ]),
    ]

    dept_by_name = {}
    for d in departments:
        name = d.name.strip()
        dept_by_name.setdefault(name, []).append(d)

    grouped_departments = []
    for label, names in department_groups_config:
        group_items = []
        for name in names:
            campus_depts = dept_by_name.get(name, [])
            if not campus_depts:
                short_name = name.removeprefix('Department of ').strip()
                for k, v in dept_by_name.items():
                    if k.removeprefix('Department of ').strip().lower() == short_name.lower():
                        campus_depts = v
                        break
            if not campus_depts:
                continue

            total_programs = sum(d.programs.count() for d in campus_depts)
            sorted_campus_depts = sorted(campus_depts, key=lambda x: (not x.campus.is_main_campus, x.campus.name))
            
            campuses_info = []
            for d in sorted_campus_depts:
                p_count = d.programs.count()
                campuses_info.append({
                    'campus_code': d.campus.code,
                    'campus_name': d.campus.name,
                    'campus_city': d.campus.city,
                    'is_main': d.campus.is_main_campus,
                    'programs_count': p_count,
                    'slug': d.slug,
                    'url': reverse('admissions:department_detail', kwargs={'department_slug': d.slug}),
                })

            active_campus_offerings = [c for c in campuses_info if c['programs_count'] > 0]
            is_single = (len(campuses_info) == 1) or (len(active_campus_offerings) == 1 and active_campus_offerings[0]['programs_count'] == total_programs)

            group_items.append({
                'name': name,
                'total_programs': total_programs,
                'campuses_count': len(campuses_info),
                'active_campuses_count': len(active_campus_offerings),
                'campuses': campuses_info,
                'campuses_json': json.dumps(campuses_info),
                'is_single_campus': is_single,
                'single_url': active_campus_offerings[0]['url'] if active_campus_offerings else (campuses_info[0]['url'] if campuses_info else '#'),
            })

        if group_items:
            grouped_departments.append({'label': label, 'departments': group_items})

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
    program_qs = Program.objects.select_related(
        'department', 'department__campus', 'campus', 'required_qualification'
    ).prefetch_related('eligibility_rules__qualification', 'test_requirements__test_type')
    
    campus_code = request.GET.get('campus', '').strip()
    department_code = request.GET.get('department', '').strip()
    status_filter = request.GET.get('status', '').strip()
    search_query = request.GET.get('q', '').strip()
    
    if campus_code:
        program_qs = program_qs.filter(Q(campus__code=campus_code) | Q(department__campus__code=campus_code))
    if department_code:
        program_qs = program_qs.filter(department__code=department_code)
    if status_filter == 'open':
        program_qs = program_qs.filter(admissions_open=True)
    elif status_filter == 'closed':
        program_qs = program_qs.filter(admissions_open=False)
    if search_query:
        program_qs = program_qs.filter(
            Q(name__icontains=search_query) |
            Q(department__name__icontains=search_query) |
            Q(department__code__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query)
        )
        
    active_campuses = Campus.objects.filter(is_active=True).order_by('-is_main_campus', 'name')
    active_departments = Department.objects.select_related('campus').filter(is_active=True).order_by('campus__city', 'name')
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
    qs = Program.objects.select_related('department', 'department__campus', 'campus', 'required_qualification').prefetch_related('eligibility_rules__qualification', 'test_requirements__test_type')
    
    # 1. Direct slug or code lookup
    program = qs.filter(Q(slug__iexact=program_slug) | Q(code__iexact=program_slug)).first()
    
    # 2. Intelligent fuzzy/slug normalization fallback
    if not program:
        clean_slug = program_slug.lower().strip()
        # Check if contains program code like bsai, bscs, bsse, bsee, etc.
        for code_part in clean_slug.split('-'):
            if code_part:
                candidate = qs.filter(Q(code__icontains=code_part) | Q(slug__icontains=code_part)).first()
                if candidate:
                    program = candidate
                    break
                    
    # 3. If still not found, search by name keywords
    if not program:
        words = [w for w in program_slug.replace('-', ' ').split() if len(w) > 2 and w not in ('isb', 'lhr', 'khi', 'cs', 'department', 'of', 'in', 'and')]
        if words:
            q_filter = Q()
            for w in words:
                q_filter |= Q(name__icontains=w)
            program = qs.filter(q_filter).first()

    if not program:
        raise Http404(f"No Program matches '{program_slug}'")

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
    import base64
    applicant = get_object_or_404(
        PISTApplicant.objects.select_related('campus', 'program__department', 'student', 'test_session', 'test_session__test_center'),
        pk=application_uuid,
    )
    if applicant.student_id is None and not request.user.is_authenticated:
        verification_url = request.build_absolute_uri(reverse('admissions:verify_application', kwargs={'application_uuid': applicant.pk}))
        qr_image = qrcode.make(verification_url)
        qr_buffer = BytesIO()
        qr_image.save(qr_buffer, format='PNG')
        qr_data_uri = f'data:image/png;base64,{base64.b64encode(qr_buffer.getvalue()).decode("utf-8")}'
        return render(request, 'admissions/roll_slip.html', {
            'application': applicant,
            'roll_slip': None,
            'verification_url': verification_url,
            'qr_data_uri': qr_data_uri,
        })
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login

        return redirect_to_login(request.get_full_path(), reverse('students:login'))
    if not (request.user.is_staff or applicant.student_id == getattr(getattr(request.user, 'student_profile', None), 'pk', None)):
        return render(request, 'errors/403.html', status=403)
    
    slip = None
    if applicant.roll_number and applicant.test_session_id:
        slip, _ = RollSlip.objects.get_or_create(
            application=applicant,
            defaults={'roll_number': applicant.roll_number or '', 'test_session_id': applicant.test_session_id},
        )
    
    if slip:
        verification_url = request.build_absolute_uri(reverse('admissions:verify_roll_slip', kwargs={'qr_token': slip.qr_token}))
    else:
        verification_url = request.build_absolute_uri(reverse('admissions:verify_application', kwargs={'application_uuid': applicant.pk}))
    
    qr_image = qrcode.make(verification_url)
    qr_buffer = BytesIO()
    qr_image.save(qr_buffer, format='PNG')
    qr_data_uri = f'data:image/png;base64,{base64.b64encode(qr_buffer.getvalue()).decode("utf-8")}'

    return render(request, 'admissions/roll_slip.html', {
        'application': applicant,
        'roll_slip': slip,
        'verification_url': verification_url,
        'qr_data_uri': qr_data_uri,
    })


def roll_slip_qr(request, application_uuid):
    applicant = get_object_or_404(PISTApplicant, pk=application_uuid)
    slip = RollSlip.objects.filter(application=applicant).first()
    if slip:
        verification_url = request.build_absolute_uri(reverse('admissions:verify_roll_slip', kwargs={'qr_token': slip.qr_token}))
    else:
        verification_url = request.build_absolute_uri(reverse('admissions:verify_application', kwargs={'application_uuid': applicant.pk}))
    image = qrcode.make(verification_url)
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
