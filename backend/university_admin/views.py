from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator
from django.db.models import Count
from django.utils import timezone
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from urllib.parse import urlencode

from admissions.models import PISTApplicant, Campus, Department, Program, TestCenter, TestSession

from .filters import ApplicantFilter
from .forms import ApplicationStatusForm
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
            messages.success(request, 'Logged in successfully.')
            return redirect('university_admin:dashboard')
        form.add_error(None, 'Only staff users can access the university admin portal.')

    return render(request, 'university_admin/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('university_admin:login')


@staff_required
def dashboard(request):
    applicants = PISTApplicant.objects.select_related('campus', 'program__department')
    stats = {
        'total_applications': applicants.count(),
        'applications_today': applicants.filter(created_at__date=timezone.now().date()).count(),
        'islamabad_applications': applicants.filter(campus__code='ISB').count(),
        'lahore_applications': applicants.filter(campus__code='LHR').count(),
        'karachi_applications': applicants.filter(campus__code='KHI').count(),
        'awaiting_review': applicants.filter(status=PISTApplicant.Status.RECEIVED).count(),
        'entry_tests_scheduled': applicants.filter(status=PISTApplicant.Status.ROLL_ISSUED).count(),
        'shortlisted': applicants.filter(status=PISTApplicant.Status.SHORTLISTED).count(),
        'rejected': applicants.filter(status=PISTApplicant.Status.REJECTED).count(),
    }

    filtered = ApplicantFilter(request.GET, queryset=applicants.order_by('-created_at'))
    paginator = Paginator(filtered.qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'university_admin/dashboard.html',
        {
            'stats': stats,
            'filter': filtered,
            'page_obj': page_obj,
            'page_query': _pagination_query(request.GET),
            'campuses': Campus.objects.all(),
            'departments': Department.objects.select_related('campus').all(),
            'programs': Program.objects.select_related('department', 'department__campus').all(),
            'test_centers': TestCenter.objects.select_related('campus').all(),
            'test_sessions': TestSession.objects.select_related('test_center', 'program').all()[:8],
        },
    )


@staff_required
def applications(request):
    applicants = PISTApplicant.objects.select_related('campus', 'program__department').order_by('-created_at')
    filtered = ApplicantFilter(request.GET, queryset=applicants)
    paginator = Paginator(filtered.qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'university_admin/applications.html', {'filter': filtered, 'page_obj': page_obj, 'page_query': _pagination_query(request.GET)})


@staff_required
def application_detail(request, application_uuid):
    applicant = get_object_or_404(
        PISTApplicant.objects.select_related('campus', 'program__department').prefetch_related('test_scores'),
        pk=application_uuid,
    )
    form = ApplicationStatusForm(request.POST or None, instance=applicant)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Application status updated successfully.')
        return redirect('university_admin:application_detail', application_uuid=applicant.pk)
    return render(request, 'university_admin/application_detail.html', {'application': applicant, 'form': form})


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
