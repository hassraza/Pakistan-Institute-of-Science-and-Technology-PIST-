import django_filters
from django.db.models import Q

from admissions.models import Department, PISTApplicant


class ApplicantFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search', label='Search')
    department = django_filters.ModelChoiceFilter(field_name='program__department', queryset=Department.objects.select_related('campus').all())
    application_date = django_filters.DateFilter(field_name='created_at', lookup_expr='date')

    class Meta:
        model = PISTApplicant
        fields = {
            'campus': ['exact'],
            'program': ['exact'],
            'status': ['exact'],
            'test_date': ['exact'],
        }

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(full_name__icontains=value)
            | Q(cnic__icontains=value)
            | Q(email__icontains=value)
            | Q(roll_number__icontains=value)
            | Q(source_application_id__icontains=value)
        )
