from .models import Campus
from .models import Program


def site_context(request):
    active_campuses = Campus.objects.filter(is_active=True).order_by('city', 'name')
    return {
        'site_name': 'Pakistan Institute of Science and Technology',
        'active_campuses': active_campuses,
        'campus_count': active_campuses.count(),
        'admissions_open_count': Program.objects.filter(admissions_open=True, department__campus__is_active=True).values('department__campus').distinct().count(),
    }
