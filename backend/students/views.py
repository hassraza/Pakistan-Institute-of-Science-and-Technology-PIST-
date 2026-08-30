from __future__ import annotations

import hashlib
import uuid
from datetime import date

from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetCompleteView, PasswordResetDoneView, PasswordResetView
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, OperationalError, transaction
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from admissions.models import PISTApplicant, Program
from admissions.services import RollNumberService, TestSchedulingService, check_program_eligibility, current_admission_year, generate_program_registration_id, registration_blockers

from .forms import AcademicDocumentForm, AcademicDocumentReplaceForm, IntermediateRecordForm, MatricRecordForm, ProgramApplicationForm, StudentPasswordChangeForm, StudentPasswordResetForm, StudentProfileForm, StudentRegistrationForm, StudentTestScoreForm
from .models import AcademicDocument, IntermediateRecord, MatricRecord, StudentProfile, StudentTestScore
from .services import generate_student_id

# StudentProfile is a OneToOneField over Django's User.
# Applications are scoped by student relationship.


def student_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('students:login')}?next={request.get_full_path()}")
        try:
            profile = request.user.student_profile
        except (AttributeError, ObjectDoesNotExist):
            profile = None
        if not profile:
            if request.user.is_staff or request.user.is_superuser:
                messages.info(request, 'You are currently logged in with an Admin/Staff account. The Student Portal requires a student account.')
                return redirect('university_admin:dashboard')
            messages.error(request, 'No student profile found for this account. Please register as a student.')
            logout(request)
            return redirect('students:register')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def _redirect_if_authenticated(request):
    if request.user.is_authenticated:
        try:
            if request.user.student_profile:
                return redirect('students:dashboard')
        except (AttributeError, ObjectDoesNotExist):
            if request.user.is_staff or request.user.is_superuser:
                return redirect('university_admin:dashboard')
            return redirect('students:register')
    return None


def _attempt_key(request, email):
    value = f'{email.lower()}:{request.META.get("REMOTE_ADDR", "unknown")}'
    return 'student-login:' + hashlib.sha256(value.encode()).hexdigest()


def _next_url(request):
    target = request.POST.get('next') or request.GET.get('next')
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()}, require_https=request.is_secure()):
        return target
    return reverse('students:dashboard')


def policy(request, policy_name):
    return render(request, 'students/policy.html', {'policy_name': policy_name})


def _student_age(birth_date):
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def _profile_completion(profile):
    checklist = (bool(profile.profile_photo), bool(profile.phone), bool(profile.address), bool(profile.date_of_birth), bool(profile.cnic))
    return round(sum(checklist) / len(checklist) * 100)


def _student_application(request):
    profile = getattr(request.user, 'student_profile', None)
    if not profile:
        return None
    return PISTApplicant.objects.select_related('campus', 'program__department').filter(
        student=profile,
    ).exclude(application_status=PISTApplicant.ApplicationStatus.WITHDRAWN).order_by('-created_at').first()


def register(request):
    existing = _redirect_if_authenticated(request)
    if existing:
        return existing
    form = StudentRegistrationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.data.get('website'):
            form.add_error(None, 'Registration could not be completed.')
        else:
            throttle_key = f'student-register:{request.META.get("REMOTE_ADDR", "unknown")}'
            if cache.get(throttle_key):
                form.add_error(None, 'Please wait before trying to register again.')
            elif form.is_valid():
                with transaction.atomic():
                    user = get_user_model().objects.create_user(
                        username=form.cleaned_data['email'], email=form.cleaned_data['email'],
                        password=form.cleaned_data['password'],
                    )
                    profile = StudentProfile.objects.create(
                        user=user, student_id=generate_student_id(),
                        **{key: form.cleaned_data.get(key) for key in ('full_name', 'cnic', 'date_of_birth', 'phone', 'gender', 'father_name', 'address', 'nationality', 'profile_photo')},
                    )
                cache.set(throttle_key, True, 30)
                return render(request, 'students/registered.html', {'profile': profile})
    return render(request, 'students/register.html', {'form': form})


def login_view(request):
    existing = _redirect_if_authenticated(request)
    if existing:
        return existing
    next_url = request.GET.get('next', '')
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        key = _attempt_key(request, email)
        attempts = cache.get(key, 0)
        limit = getattr(settings, 'LOGIN_ATTEMPT_LIMIT', 5)
        window = getattr(settings, 'LOGIN_ATTEMPT_WINDOW_MINUTES', 10) * 60
        if attempts >= limit:
            return render(request, 'students/login.html', {'error': 'Too many failed attempts. Please try again later.', 'next': next_url})
        user_record = get_user_model().objects.filter(email__iexact=email).first()
        if user_record and not user_record.is_active:
            error = 'This account is inactive. Contact support.'
        elif not user_record:
            error = 'No account found with this email.'
        else:
            user = authenticate(request, username=user_record.username, password=request.POST.get('password', ''))
            error = None if user else 'Incorrect password. Please try again.'
            if user and hasattr(user, 'student_profile'):
                cache.delete(key)
                login(request, user)
                return redirect(_next_url(request))
            if user:
                error = 'No student account is associated with this email.'
        cache.set(key, attempts + 1, window)
        return render(request, 'students/login.html', {'error': error, 'next': next_url, 'email': email})
    return render(request, 'students/login.html', {'next': next_url})


@login_required(login_url='students:login')
def logout_view(request):
    logout(request)
    return redirect('students:login')


@student_required
def dashboard(request):
    profile = request.user.student_profile
    application = _student_application(request)
    upcoming_application = PISTApplicant.objects.select_related('program', 'campus', 'test_session', 'test_session__test_center').filter(
        student=request.user.student_profile,
        eligibility_status=PISTApplicant.EligibilityStatus.ELIGIBLE,
        roll_number__isnull=False,
        test_session__isnull=False,
    ).exclude(application_status=PISTApplicant.ApplicationStatus.WITHDRAWN).order_by('test_session__test_date').first()
    document_types = AcademicDocument.DocumentType.choices
    uploaded_document_count = profile.academic_documents.values('document_type').distinct().count()
    registered_programs_count = PISTApplicant.objects.filter(
        student=profile,
    ).exclude(application_status=PISTApplicant.ApplicationStatus.WITHDRAWN).count()
    return render(request, 'students/dashboard.html', {
        'profile': profile,
        'completion': _profile_completion(profile),
        'application': application,
        'upcoming_application': upcoming_application,
        'registered_programs_count': registered_programs_count,
        'uploaded_document_count': uploaded_document_count,
        'document_type_count': len(document_types),
        'onboarding_progress': profile.get_onboarding_progress(),
    })


@student_required
def profile_view(request):
    profile = request.user.student_profile
    return render(request, 'students/profile.html', {'profile': profile, 'age': _student_age(profile.date_of_birth)})


@student_required
def profile_edit(request):
    profile = request.user.student_profile
    form = StudentProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your profile has been updated.')
        return redirect('students:profile')
    return render(request, 'students/profile_edit.html', {'form': form, 'profile': profile})


@student_required
def roll_slip(request):
    application = _student_application(request)
    if not application:
        return render(request, 'students/roll_slip_unavailable.html', {'has_application': False})
    if not application.roll_number or not application.test_session_id:
        return render(request, 'students/roll_slip_unavailable.html', {'application': application, 'has_application': True})
    return redirect('admissions:roll_slip', application_uuid=application.pk)


@student_required
def documents(request):
    student = request.user.student_profile
    uploaded = {document.document_type: document for document in AcademicDocument.objects.filter(student=student)}
    document_rows = [
        {'type': document_type, 'label': label, 'document': uploaded.get(document_type)}
        for document_type, label in AcademicDocument.DocumentType.choices
    ]
    return render(request, 'students/documents.html', {'document_rows': document_rows})


@student_required
def document_upload(request):
    student = request.user.student_profile
    form = AcademicDocumentForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        document_type = form.cleaned_data['document_type']
        document = AcademicDocument.objects.filter(student=student, document_type=document_type).first()
        old_file = document.file if document else None
        if document:
            document.file = form.cleaned_data['file']
            document.file_name = form.cleaned_data['file'].name
            document.verification_status = AcademicDocument.VerificationStatus.PENDING
            document.save()
        else:
            document = form.save(commit=False)
            document.student = student
            document.file_name = form.cleaned_data['file'].name
            document.save()
        if old_file and old_file.name != document.file.name:
            old_file.delete(save=False)
        messages.success(request, 'Document uploaded successfully.')
        return redirect('students:documents')
    return render(request, 'students/document_form.html', {'form': form, 'title': 'Upload academic document'})


def _owned_document(request, doc_id):
    return AcademicDocument.objects.filter(student=request.user.student_profile, pk=doc_id).first()


@student_required
def document_view(request, doc_id):
    document = _owned_document(request, doc_id)
    if not document:
        raise Http404
    return FileResponse(document.file.open('rb'), as_attachment=False, filename=document.file_name)


@student_required
def document_replace(request, doc_id):
    document = _owned_document(request, doc_id)
    if not document:
        raise Http404
    form = AcademicDocumentReplaceForm(request.POST or None, request.FILES or None, instance=document)
    if request.method == 'POST' and form.is_valid():
        old_file = document.file
        document.file = form.cleaned_data['file']
        document.file_name = form.cleaned_data['file'].name
        document.verification_status = AcademicDocument.VerificationStatus.PENDING
        document.save()
        if old_file.name != document.file.name:
            old_file.delete(save=False)
        messages.success(request, 'Document replaced and sent for review again.')
        return redirect('students:documents')
    return render(request, 'students/document_form.html', {'form': form, 'title': 'Replace academic document', 'document': document})


@student_required
def document_delete(request, doc_id):
    document = _owned_document(request, doc_id)
    if not document:
        raise Http404
    if request.method == 'POST':
        document.file.delete(save=False)
        document.delete()
        messages.success(request, 'Document deleted.')
        return redirect('students:documents')
    return render(request, 'students/document_delete.html', {'document': document})


def _owned_record(request, model, record_id=None):
    filters = {'student': request.user.student_profile}
    if record_id is not None:
        filters['pk'] = record_id
    return model.objects.filter(**filters).first()


@student_required
def academic_record(request):
    student = request.user.student_profile
    programs = Program.objects.filter(admissions_open=True).select_related('department', 'campus').order_by('name')
    selected_program = None
    eligibility = None
    program_slug = request.GET.get('program')
    if program_slug:
        selected_program = programs.filter(slug=program_slug).first()
        if selected_program:
            eligibility = check_program_eligibility(student, selected_program)
    return render(request, 'students/academic_record.html', {
        'matric_record': getattr(student, 'matric_record', None),
        'intermediate_record': getattr(student, 'intermediate_record', None),
        'test_scores': student.test_scores.select_related('test_type'),
        'programs': programs,
        'selected_program': selected_program,
        'eligibility': eligibility,
    })


@student_required
def matric_edit(request):
    student = request.user.student_profile
    record = getattr(student, 'matric_record', None)
    form = MatricRecordForm(request.POST or None, instance=record)
    if request.method == 'POST' and form.is_valid():
        record = form.save(commit=False)
        record.student = student
        record.save()
        messages.success(request, 'Matric record saved.')
        return redirect('students:academic_record')
    return render(request, 'students/academic_record_form.html', {'form': form, 'title': 'Matric record'})


@student_required
def intermediate_edit(request):
    student = request.user.student_profile
    record = getattr(student, 'intermediate_record', None)
    form = IntermediateRecordForm(request.POST or None, instance=record)
    if request.method == 'POST' and form.is_valid():
        record = form.save(commit=False)
        record.student = student
        record.save()
        messages.success(request, 'Intermediate record saved.')
        return redirect('students:academic_record')
    return render(request, 'students/academic_record_form.html', {'form': form, 'title': 'Intermediate / FSc record'})


@student_required
def test_score_add(request):
    student = request.user.student_profile
    form = StudentTestScoreForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        score = form.save(commit=False)
        score.student = student
        score.save()
        messages.success(request, 'Test score saved.')
        return redirect('students:academic_record')
    return render(request, 'students/academic_record_form.html', {'form': form, 'title': 'Add test score'})


@student_required
def test_score_edit(request, score_id):
    score = _owned_record(request, StudentTestScore, score_id)
    if not score:
        raise Http404
    form = StudentTestScoreForm(request.POST or None, request.FILES or None, instance=score)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Test score updated.')
        return redirect('students:academic_record')
    return render(request, 'students/academic_record_form.html', {'form': form, 'title': 'Edit test score'})


@student_required
def test_score_delete(request, score_id):
    score = _owned_record(request, StudentTestScore, score_id)
    if not score:
        raise Http404
    if request.method == 'POST':
        if score.result_certificate:
            score.result_certificate.delete(save=False)
        score.delete()
        messages.success(request, 'Test score deleted.')
        return redirect('students:academic_record')
    return render(request, 'students/test_score_delete.html', {'score': score})


@student_required
def test_certificate_view(request, score_id):
    score = _owned_record(request, StudentTestScore, score_id)
    if not score or not score.result_certificate:
        raise Http404
    return FileResponse(score.result_certificate.open('rb'), as_attachment=False, filename=score.result_certificate.name.rsplit('/', 1)[-1])


def _student_program_application(request, program):
    return PISTApplicant.objects.filter(student=request.user.student_profile, program=program).exclude(
        application_status=PISTApplicant.ApplicationStatus.WITHDRAWN,
    ).first()


@student_required
def apply_program(request, program_slug):
    program = Program.objects.select_related('department', 'campus').prefetch_related('eligibility_rules__qualification').filter(slug=program_slug).first()
    if not program:
        raise Http404
    existing = _student_program_application(request, program)
    if existing:
        return redirect('students:application_detail', application_uuid=existing.pk)
    form = ProgramApplicationForm(program, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        blockers = registration_blockers(
            student=request.user.student_profile,
            program=program,
            qualification=form.cleaned_data['qualification'],
            percentage=form.cleaned_data['percentage'],
        )
        if blockers:
            form.add_error(None, blockers)
        else:
            return render(request, 'students/application_review.html', {
                'form': form,
                'program': program,
                'profile': request.user.student_profile,
                'qualification': form.cleaned_data['qualification'],
                'percentage': form.cleaned_data['percentage'],
            })
    return render(request, 'students/application_form.html', {'form': form, 'program': program})


def _submit_program_application(request, program, form):
    student = request.user.student_profile
    intermediate = getattr(student, 'intermediate_record', None)
    matric = getattr(student, 'matric_record', None)
    academic_qualification = intermediate and program.eligibility_rules.filter(
        qualification__qualification_group_code=intermediate.group,
    ).values_list('qualification', flat=True).first()
    application_id = f'APP-{current_admission_year()}-{uuid.uuid4().hex.upper()}'
    registration_id = generate_program_registration_id(program)
    campus = program.campus or program.department.campus
    application = PISTApplicant.objects.create(
        student=student,
        application_id=application_id,
        program_registration_id=registration_id,
        application_status=PISTApplicant.ApplicationStatus.SUBMITTED,
        eligibility_status=PISTApplicant.EligibilityStatus.ELIGIBLE,
        qualifying_qualification_id=academic_qualification or form.cleaned_data['qualification'].pk,
        qualifying_percentage=intermediate.percentage if intermediate else form.cleaned_data['percentage'],
        full_name=student.full_name,
        father_name=student.father_name,
        cnic=student.cnic,
        email=request.user.email,
        phone=student.phone,
        address=student.address,
        matric_marks=matric.obtained_marks if matric else form.cleaned_data['percentage'],
        matric_total=matric.total_marks if matric else 100,
        fsc_marks=intermediate.obtained_marks if intermediate else form.cleaned_data['percentage'],
        fsc_total=intermediate.total_marks if intermediate else 100,
        campus=campus,
        program=program,
        source_application_id=application_id,
    )
    TestSchedulingService.assign(application, submitted_at=timezone.now())
    RollNumberService.issue_roll_number(application)
    application.refresh_from_db()
    return application


@student_required
def submit_program_application(request, program_slug):
    if request.method != 'POST' or request.POST.get('confirm') != '1':
        return redirect('students:apply_program', program_slug=program_slug)
    program = Program.objects.select_related('department', 'campus').filter(slug=program_slug).first()
    if not program:
        raise Http404
    form = ProgramApplicationForm(program, request.POST)
    if not form.is_valid():
        return render(request, 'students/application_form.html', {'form': form, 'program': program})
    blockers = registration_blockers(student=request.user.student_profile, program=program, qualification=form.cleaned_data['qualification'], percentage=form.cleaned_data['percentage'])
    if blockers:
        form.add_error(None, blockers)
        return render(request, 'students/application_form.html', {'form': form, 'program': program})
    for _attempt in range(3):
        try:
            with transaction.atomic():
                application = _submit_program_application(request, program, form)
            return render(request, 'students/application_confirmation.html', {'application': application})
        except (IntegrityError, OperationalError):
            if _attempt == 2:
                raise
    raise Http404


@student_required
def registered_programs(request):
    applications = PISTApplicant.objects.select_related('program', 'program__department', 'campus').filter(student=request.user.student_profile).exclude(application_status=PISTApplicant.ApplicationStatus.WITHDRAWN).order_by('-created_at')
    return render(request, 'students/registered_programs.html', {'applications': applications})


@student_required
def application_detail(request, application_uuid):
    application = PISTApplicant.objects.select_related('program', 'program__department', 'campus', 'student').filter(student=request.user.student_profile, pk=application_uuid).first()
    if not application:
        raise Http404
    return render(request, 'students/application_detail.html', {'application': application})


@student_required
def application_roll_slip(request, application_uuid):
    application = PISTApplicant.objects.select_related('program', 'program__department', 'campus', 'student').filter(student=request.user.student_profile, pk=application_uuid).first()
    if not application:
        raise Http404
    if not application.roll_number or not application.test_session_id:
        return render(request, 'students/roll_slip_unavailable.html', {'application': application, 'has_application': True})
    return redirect('admissions:roll_slip', application_uuid=application.pk)


@student_required
def password_change(request):
    form = StudentPasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your password has been changed.')
        return redirect('students:dashboard')
    return render(request, 'students/password_change.html', {'form': form})


class StudentPasswordResetView(PasswordResetView):
    form_class = StudentPasswordResetForm
    template_name = 'students/password_reset.html'
    success_url = reverse_lazy('students:password_reset_done')
    email_template_name = 'students/password_reset_email.txt'
    subject_template_name = 'students/password_reset_subject.txt'


class StudentPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'students/password_reset_done.html'


class StudentPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'students/password_reset_confirm.html'
    success_url = reverse_lazy('students:password_reset_complete')


class StudentPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'students/password_reset_complete.html'
