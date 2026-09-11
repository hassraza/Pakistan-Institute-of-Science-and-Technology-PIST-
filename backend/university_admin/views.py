from __future__ import annotations

from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from urllib.parse import urlencode

from admissions.models import (
    ApplicantTestScore,
    Campus,
    Department,
    PISTApplicant,
    Program,
    RollSlip,
    TestCenter,
    TestSession,
)
from admissions.services import RollNumberService, current_admission_year
from students.models import AcademicDocument, Notification, StudentProfile

from .filters import ApplicantFilter
from .forms import (
    ApplicationAcceptForm,
    ApplicationRejectForm,
    ApplicationStatusForm,
    BroadcastNotificationForm,
    ProgramSettingsForm,
    ScheduleTestForm,
    StaffLoginForm,
    TestSessionForm,
)
from .services import ApplicantExportService


def staff_required(view_func):
    return login_required(user_passes_test(lambda user: user.is_staff, login_url='university_admin:login')(view_func))


def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('university_admin:dashboard')

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        if user and user.is_staff:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}.')
            return redirect('university_admin:dashboard')
        form.add_error(None, 'Only staff users can access the university admin portal.')

    return render(request, 'university_admin/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('university_admin:login')


# ==============================================================================
# 1. Executive Dashboard
# ==============================================================================

@staff_required
def dashboard(request):
    applicants = PISTApplicant.objects.select_related('campus', 'program__department', 'student')

    stats = {
        'total_applications': applicants.count(),
        'applications_today': applicants.filter(created_at__date=timezone.now().date()).count(),
        'islamabad_applications': applicants.filter(campus__code='ISB').count(),
        'awaiting_review': applicants.filter(
            Q(status=PISTApplicant.Status.RECEIVED) | Q(application_status=PISTApplicant.ApplicationStatus.SUBMITTED)
        ).count(),
        'entry_tests_scheduled': applicants.filter(
            Q(status=PISTApplicant.Status.ROLL_ISSUED) | Q(application_status=PISTApplicant.ApplicationStatus.SCHEDULED)
        ).count(),
        'shortlisted': applicants.filter(status=PISTApplicant.Status.SHORTLISTED).count(),
        'accepted': applicants.filter(
            Q(status__in=[
                PISTApplicant.Status.SELECTED,
                PISTApplicant.Status.ADMISSION_CONFIRMED,
                PISTApplicant.Status.MERIT_LIST_1,
                PISTApplicant.Status.MERIT_LIST_2,
            ]) | Q(application_status=PISTApplicant.ApplicationStatus.ACCEPTED)
        ).count(),
        'rejected': applicants.filter(
            Q(status=PISTApplicant.Status.REJECTED) | Q(application_status=PISTApplicant.ApplicationStatus.REJECTED)
        ).count(),
        'total_students': StudentProfile.objects.count(),
        'pending_documents': AcademicDocument.objects.filter(verification_status=AcademicDocument.VerificationStatus.PENDING).count(),
        'active_programs': Program.objects.filter(admissions_open=True).count(),
        'upcoming_sessions': TestSession.objects.filter(is_active=True, test_date__gte=timezone.now().date()).count(),
    }

    program_stats = (
        Program.objects.select_related('department', 'department__campus')
        .annotate(applicant_count=Count('applicants'))
        .filter(applicant_count__gt=0)
        .order_by('-applicant_count')[:8]
    )

    recent_applicants = applicants.order_by('-created_at')[:10]

    return render(
        request,
        'university_admin/dashboard.html',
        {
            'stats': stats,
            'program_stats': program_stats,
            'recent_applicants': recent_applicants,
            'campuses': Campus.objects.all(),
            'departments': Department.objects.select_related('campus').all(),
            'programs': Program.objects.select_related('department', 'department__campus').all(),
            'test_sessions': TestSession.objects.select_related('test_center', 'program').filter(is_active=True)[:6],
        },
    )


# ==============================================================================
# 2. Applications Management & Bulk Actions
# ==============================================================================

@staff_required
def applications(request):
    applicants = PISTApplicant.objects.select_related('campus', 'program__department', 'student').order_by('-created_at')

    # Handle bulk action POST
    if request.method == 'POST':
        action = request.POST.get('bulk_action')
        selected_ids = request.POST.getlist('selected_applications')

        if not selected_ids:
            messages.warning(request, 'No applications were selected.')
            return redirect(request.get_full_path())

        target_qs = PISTApplicant.objects.filter(pk__in=selected_ids)
        count = target_qs.count()

        if action == 'accept':
            for app in target_qs:
                app.application_status = PISTApplicant.ApplicationStatus.ACCEPTED
                app.status = PISTApplicant.Status.ADMISSION_CONFIRMED
                app.save(update_fields=['application_status', 'status', 'updated_at'])
                if app.student:
                    Notification.objects.create(
                        student=app.student,
                        title='Admission Offered - Congratulations!',
                        message=f'Your application for {app.program.name} at PIST has been accepted.',
                    )
            messages.success(request, f'Successfully accepted {count} selected application(s).')

        elif action == 'reject':
            for app in target_qs:
                app.application_status = PISTApplicant.ApplicationStatus.REJECTED
                app.status = PISTApplicant.Status.REJECTED
                app.save(update_fields=['application_status', 'status', 'updated_at'])
                if app.student:
                    Notification.objects.create(
                        student=app.student,
                        title='Application Status Update',
                        message=f'Your application for {app.program.name} was not accepted during review.',
                    )
            messages.warning(request, f'Marked {count} selected application(s) as Rejected.')

        elif action == 'shortlist':
            for app in target_qs:
                app.status = PISTApplicant.Status.SHORTLISTED
                app.save(update_fields=['status', 'updated_at'])
            messages.success(request, f'Shortlisted {count} application(s) for entry test.')

        elif action == 'review':
            for app in target_qs:
                app.application_status = PISTApplicant.ApplicationStatus.UNDER_REVIEW
                app.status = PISTApplicant.Status.ELIGIBILITY_REVIEW
                app.save(update_fields=['application_status', 'status', 'updated_at'])
            messages.info(request, f'Moved {count} application(s) to Under Review.')

        return redirect(request.get_full_path())

    filtered = ApplicantFilter(request.GET, queryset=applicants)
    paginator = Paginator(filtered.qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'university_admin/applications.html',
        {
            'filter': filtered,
            'page_obj': page_obj,
            'page_query': _pagination_query(request.GET),
            'total_count': filtered.qs.count(),
        },
    )


# ==============================================================================
# 3. Application Dossier & Decision Modals
# ==============================================================================

@staff_required
def application_detail(request, application_uuid):
    applicant = get_object_or_404(
        PISTApplicant.objects.select_related('campus', 'program__department', 'student', 'test_session__test_center').prefetch_related('test_scores'),
        pk=application_uuid,
    )
    status_form = ApplicationStatusForm(instance=applicant)
    accept_form = ApplicationAcceptForm()
    reject_form = ApplicationRejectForm()
    schedule_form = ScheduleTestForm(program=applicant.program)

    # General status update POST
    if request.method == 'POST' and ('update_status' in request.POST or 'status' in request.POST):
        status_form = ApplicationStatusForm(request.POST, instance=applicant)
        if status_form.is_valid():
            status_form.save()
            messages.success(request, 'Application status updated successfully.')
            return redirect('university_admin:application_detail', application_uuid=applicant.pk)

    documents = []
    if applicant.student:
        documents = AcademicDocument.objects.filter(student=applicant.student).order_by('-uploaded_at')

    # Fetch existing roll slip if any
    roll_slip = getattr(applicant, 'roll_slip', None)

    return render(
        request,
        'university_admin/application_detail.html',
        {
            'application': applicant,
            'form': status_form,
            'accept_form': accept_form,
            'reject_form': reject_form,
            'schedule_form': schedule_form,
            'documents': documents,
            'roll_slip': roll_slip,
        },
    )


@staff_required
def application_accept_action(request, application_uuid):
    if request.method != 'POST':
        return redirect('university_admin:application_detail', application_uuid=application_uuid)

    applicant = get_object_or_404(PISTApplicant.objects.select_related('program', 'student'), pk=application_uuid)
    form = ApplicationAcceptForm(request.POST)

    if form.is_valid():
        notes = form.cleaned_data.get('admission_notes', '').strip()
        applicant.application_status = PISTApplicant.ApplicationStatus.ACCEPTED
        applicant.status = PISTApplicant.Status.ADMISSION_CONFIRMED
        applicant.save(update_fields=['application_status', 'status', 'updated_at'])

        if applicant.student:
            msg = f'Congratulations! Your admission to {applicant.program.name} at PIST has been approved.'
            if notes:
                msg += f' Official remarks: {notes}'
            Notification.objects.create(
                student=applicant.student,
                title='Admission Offer Granted!',
                message=msg,
            )

        messages.success(request, f'Application for {applicant.full_name} has been Accepted.')
    else:
        messages.error(request, 'Could not accept application. Please verify the form.')

    return redirect('university_admin:application_detail', application_uuid=applicant.pk)


@staff_required
def application_reject_action(request, application_uuid):
    if request.method != 'POST':
        return redirect('university_admin:application_detail', application_uuid=application_uuid)

    applicant = get_object_or_404(PISTApplicant.objects.select_related('program', 'student'), pk=application_uuid)
    form = ApplicationRejectForm(request.POST)

    if form.is_valid():
        reason = form.cleaned_data['rejection_reason'].strip()
        applicant.application_status = PISTApplicant.ApplicationStatus.REJECTED
        applicant.status = PISTApplicant.Status.REJECTED
        applicant.save(update_fields=['application_status', 'status', 'updated_at'])

        if applicant.student:
            Notification.objects.create(
                student=applicant.student,
                title='Application Status Update - PIST Admissions',
                message=f'Your application for {applicant.program.name} has not been approved. Reason: {reason}',
            )

        messages.warning(request, f'Application for {applicant.full_name} has been Marked as Rejected.')
    else:
        messages.error(request, 'Please provide a valid rejection reason.')

    return redirect('university_admin:application_detail', application_uuid=applicant.pk)


@staff_required
def application_schedule_action(request, application_uuid):
    if request.method != 'POST':
        return redirect('university_admin:application_detail', application_uuid=application_uuid)

    applicant = get_object_or_404(PISTApplicant.objects.select_related('program', 'campus', 'student'), pk=application_uuid)
    form = ScheduleTestForm(request.POST, program=applicant.program)

    if form.is_valid():
        session = form.cleaned_data.get('test_session')
        with transaction.atomic():
            if session:
                if session.available_seats > 0:
                    session.available_seats -= 1
                    session.save(update_fields=['available_seats'])
                applicant.test_session = session
                applicant.test_date = session.test_date
                applicant.reporting_time = session.reporting_time
                applicant.test_venue = session.test_center.name
                applicant.test_building = session.building
                applicant.test_hall = session.hall
            else:
                applicant.test_date = form.cleaned_data.get('custom_test_date') or timezone.localdate()
                applicant.reporting_time = form.cleaned_data.get('custom_reporting_time')
                applicant.test_venue = form.cleaned_data.get('custom_venue') or applicant.campus.name
                applicant.test_building = form.cleaned_data.get('custom_building') or 'Academic Block'
                applicant.test_hall = form.cleaned_data.get('custom_hall') or 'Examination Hall'

                # Ensure test session exists for roll slip relation
                test_center = TestCenter.objects.filter(campus=applicant.campus, is_active=True).first()
                if not test_center:
                    test_center = TestCenter.objects.create(
                        campus=applicant.campus,
                        name=f'{applicant.campus.name} Center',
                        address=applicant.campus.city,
                        building=applicant.test_building,
                        hall=applicant.test_hall,
                        capacity=100,
                    )
                session, _ = TestSession.objects.get_or_create(
                    test_center=test_center,
                    program=applicant.program,
                    test_date=applicant.test_date,
                    defaults={
                        'reporting_time': applicant.reporting_time or timezone.datetime.strptime('08:30', '%H:%M').time(),
                        'building': applicant.test_building,
                        'hall': applicant.test_hall,
                        'available_seats': 50,
                    }
                )
                applicant.test_session = session

            applicant.application_status = PISTApplicant.ApplicationStatus.SCHEDULED
            applicant.status = PISTApplicant.Status.ROLL_ISSUED
            applicant.eligibility_status = PISTApplicant.EligibilityStatus.ELIGIBLE
            applicant.save(update_fields=['test_session', 'test_date', 'reporting_time', 'test_venue', 'test_building', 'test_hall', 'application_status', 'status', 'eligibility_status', 'updated_at'])

            if not applicant.roll_number:
                RollNumberService.issue_roll_number(applicant)

        if applicant.student:
            Notification.objects.create(
                student=applicant.student,
                title='Entry Test Scheduled & Roll Slip Issued',
                message=(
                    f'Your entry test for {applicant.program.name} is scheduled for {applicant.test_date} '
                    f'at {applicant.test_venue}. Your Roll Number is {applicant.roll_number}.'
                ),
            )

        messages.success(request, f'Test scheduled and roll number {applicant.roll_number} assigned to {applicant.full_name}.')
    else:
        messages.error(request, 'Failed to schedule test. Please check the session details.')

    return redirect('university_admin:application_detail', application_uuid=applicant.pk)


# ==============================================================================
# 4. Student Directory & Dossier
# ==============================================================================

@staff_required
def students_list(request):
    q = request.GET.get('q', '').strip()
    students = (
        StudentProfile.objects.select_related('user')
        .prefetch_related('program_applications__program', 'academic_documents')
        .order_by('-created_at')
    )

    if q:
        students = students.filter(
            Q(full_name__icontains=q)
            | Q(student_id__icontains=q)
            | Q(cnic__icontains=q)
            | Q(user__email__icontains=q)
            | Q(phone__icontains=q)
        )

    paginator = Paginator(students, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'university_admin/students.html',
        {
            'page_obj': page_obj,
            'search_query': q,
            'total_students': students.count(),
        },
    )


@staff_required
def student_detail(request, student_id):
    student = get_object_or_404(
        StudentProfile.objects.select_related('user').prefetch_related('test_scores'),
        pk=student_id,
    )
    applications = student.program_applications.select_related('program', 'campus').order_by('-created_at')
    documents = student.academic_documents.all().order_by('-uploaded_at')
    notifications = student.notifications.all().order_by('-created_at')[:15]

    # Quick message form
    if request.method == 'POST' and 'send_student_note' in request.POST:
        note_title = request.POST.get('title', '').strip()
        note_msg = request.POST.get('message', '').strip()
        if note_title and note_msg:
            Notification.objects.create(student=student, title=note_title, message=note_msg)
            messages.success(request, f'Notification successfully sent to {student.full_name}.')
            return redirect('university_admin:student_detail', student_id=student.pk)
        messages.error(request, 'Title and message cannot be blank.')

    return render(
        request,
        'university_admin/student_detail.html',
        {
            'student': student,
            'applications': applications,
            'documents': documents,
            'notifications': notifications,
        },
    )


# ==============================================================================
# 5. Document Verification Queue
# ==============================================================================

@staff_required
def documents_queue(request):
    status_filter = request.GET.get('status', 'PENDING')
    doc_type_filter = request.GET.get('type', '')
    q = request.GET.get('q', '').strip()

    documents = (
        AcademicDocument.objects.select_related('student', 'reviewed_by')
        .order_by('-uploaded_at')
    )

    if status_filter and status_filter != 'ALL':
        documents = documents.filter(verification_status=status_filter)

    if doc_type_filter:
        documents = documents.filter(document_type=doc_type_filter)

    if q:
        documents = documents.filter(
            Q(student__full_name__icontains=q)
            | Q(student__cnic__icontains=q)
            | Q(student__student_id__icontains=q)
            | Q(file_name__icontains=q)
        )

    pending_count = AcademicDocument.objects.filter(verification_status=AcademicDocument.VerificationStatus.PENDING).count()
    verified_count = AcademicDocument.objects.filter(verification_status=AcademicDocument.VerificationStatus.VERIFIED).count()
    rejected_count = AcademicDocument.objects.filter(verification_status=AcademicDocument.VerificationStatus.REJECTED).count()

    paginator = Paginator(documents, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'university_admin/documents_queue.html',
        {
            'page_obj': page_obj,
            'status_filter': status_filter,
            'doc_type_filter': doc_type_filter,
            'search_query': q,
            'document_types': AcademicDocument.DocumentType.choices,
            'pending_count': pending_count,
            'verified_count': verified_count,
            'rejected_count': rejected_count,
        },
    )


@staff_required
def document_review_action(request, document_id):
    document = get_object_or_404(AcademicDocument.objects.select_related('student'), pk=document_id)

    if request.method == 'POST':
        action = request.POST.get('action', '').strip().lower()
        rejection_reason = request.POST.get('rejection_reason', '').strip()

        if action == 'approve':
            document.verification_status = AcademicDocument.VerificationStatus.VERIFIED
            document.rejection_reason = ''
            document.reviewed_by = request.user
            document.reviewed_at = timezone.now()
            document.save()
            messages.success(request, f'{document.get_document_type_display()} for {document.student.full_name} has been Verified.')
        elif action == 'reject':
            document.verification_status = AcademicDocument.VerificationStatus.REJECTED
            document.rejection_reason = rejection_reason or 'Document is unclear, incomplete, or invalid. Please upload a clear replacement copy.'
            document.reviewed_by = request.user
            document.reviewed_at = timezone.now()
            document.save()

            Notification.objects.create(
                student=document.student,
                title='Document Verification Feedback',
                message=f'Your {document.get_document_type_display()} was rejected. Reason: {document.rejection_reason}',
            )
            messages.warning(request, f'{document.get_document_type_display()} for {document.student.full_name} has been Rejected.')
        else:
            messages.error(request, 'Invalid review action specified.')

        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            return redirect(next_url)
        return redirect('university_admin:documents_queue')

    raise Http404()


# ==============================================================================
# 6. Academic Programs & Admission Controls
# ==============================================================================

@staff_required
def programs_list(request):
    programs = (
        Program.objects.select_related('department', 'department__campus')
        .annotate(total_applicants=Count('applicants'))
        .order_by('department__campus__code', 'department__name', 'name')
    )

    return render(
        request,
        'university_admin/programs.html',
        {
            'programs': programs,
            'campuses': Campus.objects.all(),
        },
    )


@staff_required
def program_toggle_admissions(request, program_id):
    if request.method != 'POST':
        return HttpResponseForbidden()

    program = get_object_or_404(Program, pk=program_id)
    program.admissions_open = not program.admissions_open
    program.save(update_fields=['admissions_open', 'updated_at'])

    status_str = 'Opened' if program.admissions_open else 'Closed'
    messages.success(request, f'Admissions {status_str} for {program.name} ({program.code}).')
    return redirect('university_admin:programs')


@staff_required
def program_edit(request, program_id):
    program = get_object_or_404(Program.objects.select_related('department__campus'), pk=program_id)
    form = ProgramSettingsForm(request.POST or None, instance=program)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Program settings updated for {program.name}.')
        return redirect('university_admin:programs')

    return render(
        request,
        'university_admin/program_edit.html',
        {
            'program': program,
            'form': form,
        },
    )


# ==============================================================================
# 7. Entry Test Sessions Management
# ==============================================================================

@staff_required
def test_sessions_list(request):
    sessions = (
        TestSession.objects.select_related('test_center__campus', 'program')
        .annotate(applicant_count=Count('applications'))
        .order_by('-test_date', '-reporting_time')
    )

    form = TestSessionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        new_session = form.save()
        messages.success(request, f'Test session created for {new_session.program.name} on {new_session.test_date}.')
        return redirect('university_admin:test_sessions')

    return render(
        request,
        'university_admin/test_sessions.html',
        {
            'sessions': sessions,
            'form': form,
            'centers': TestCenter.objects.filter(is_active=True),
        },
    )


@staff_required
def test_session_toggle(request, session_id):
    if request.method != 'POST':
        return HttpResponseForbidden()

    session = get_object_or_404(TestSession, pk=session_id)
    session.is_active = not session.is_active
    session.save(update_fields=['is_active'])

    status_str = 'Activated' if session.is_active else 'Deactivated'
    messages.info(request, f'Test Session on {session.test_date} has been {status_str}.')
    return redirect('university_admin:test_sessions')


# ==============================================================================
# 8. Broadcast Notification Broadcaster
# ==============================================================================

@staff_required
def notifications_list(request):
    recent_notifications = (
        Notification.objects.select_related('student')
        .order_by('-created_at')[:40]
    )
    form = BroadcastNotificationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        target = form.cleaned_data['target_audience']
        title = form.cleaned_data['title'].strip()
        message = form.cleaned_data['message'].strip()

        students_target = []
        if target == 'all':
            students_target = list(StudentProfile.objects.all())
        elif target == 'program':
            prog = form.cleaned_data.get('program')
            if prog:
                students_target = list(StudentProfile.objects.filter(program_applications__program=prog).distinct())
            else:
                messages.error(request, 'Please select a program for program broadcast.')
                return render(request, 'university_admin/notifications.html', {'form': form, 'notifications': recent_notifications})
        elif target == 'single':
            ident = form.cleaned_data.get('student_identifier', '').strip()
            student = StudentProfile.objects.filter(Q(student_id__iexact=ident) | Q(cnic=ident)).first()
            if student:
                students_target = [student]
            else:
                messages.error(request, f'No student found with ID or CNIC: "{ident}".')
                return render(request, 'university_admin/notifications.html', {'form': form, 'notifications': recent_notifications})

        if not students_target:
            messages.warning(request, 'No recipients matched your selection.')
            return redirect('university_admin:notifications')

        notification_objs = [
            Notification(student=s, title=title, message=message)
            for s in students_target
        ]
        Notification.objects.bulk_create(notification_objs)
        messages.success(request, f'Broadcast successfully dispatched to {len(notification_objs)} student(s).')
        return redirect('university_admin:notifications')

    return render(
        request,
        'university_admin/notifications.html',
        {
            'form': form,
            'notifications': recent_notifications,
        },
    )


# ==============================================================================
# 9. Exports & Utility
# ==============================================================================

@staff_required
def export_applications(request, format):
    applicants = PISTApplicant.objects.select_related('campus', 'program__department').order_by('-created_at')
    filtered = ApplicantFilter(request.GET, queryset=applicants)
    if format == 'csv':
        return ApplicantExportService.export_csv(filtered.qs)
    if format == 'json':
        return ApplicantExportService.export_json(filtered.qs)
    raise Http404()


def _pagination_query(query_dict):
    params = query_dict.copy()
    params.pop('page', None)
    encoded = params.urlencode()
    return encoded
