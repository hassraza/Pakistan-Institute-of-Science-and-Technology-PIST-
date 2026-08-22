from admissions.models import PISTApplicant


def student_portal_context(request):
    application = None
    if request.user.is_authenticated:
        profile = getattr(request.user, 'student_profile', None)
        if profile:
            application = PISTApplicant.objects.filter(
                student=profile,
                roll_number__isnull=False,
                test_session__isnull=False,
            ).exclude(application_status=PISTApplicant.ApplicationStatus.WITHDRAWN).order_by('test_session__test_date').first()
    return {'portal_roll_slip_application': application}
