from django.contrib import admin

from .models import ApplicantTestScore, Campus, Department, PISTApplicant, Program, TestCenter, TestSession


@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'code', 'admissions_open', 'is_active', 'created_at')
    list_filter = ('city', 'admissions_open', 'is_active')
    search_fields = ('name', 'city', 'code')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'campus', 'is_active', 'created_at')
    list_filter = ('campus', 'is_active')
    search_fields = ('name', 'slug', 'campus__name', 'campus__code')
    readonly_fields = ('created_at',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'department', 'admissions_open', 'required_test_type', 'eligibility_percentage')
    list_filter = ('department__campus', 'department', 'admissions_open', 'required_test_type', 'degree_level')
    search_fields = ('name', 'code', 'slug', 'department__name', 'department__campus__name')
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}


class ApplicantTestScoreInline(admin.TabularInline):
    model = ApplicantTestScore
    extra = 0


@admin.register(PISTApplicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'campus', 'program', 'roll_number', 'status', 'created_at')
    list_filter = ('campus', 'program', 'status', 'created_at')
    search_fields = ('full_name', 'cnic', 'email', 'phone', 'roll_number', 'source_application_id')
    readonly_fields = ('created_at', 'updated_at', 'matric_percentage', 'fsc_percentage')
    inlines = [ApplicantTestScoreInline]


@admin.register(TestCenter)
class TestCenterAdmin(admin.ModelAdmin):
    list_display = ('name', 'campus', 'building', 'hall', 'capacity', 'is_active')
    list_filter = ('campus', 'is_active')
    search_fields = ('name', 'building', 'hall', 'campus__name')


@admin.register(TestSession)
class TestSessionAdmin(admin.ModelAdmin):
    list_display = ('program', 'test_center', 'test_date', 'reporting_time', 'available_seats', 'is_active')
    list_filter = ('test_date', 'is_active', 'program__department__campus')
    search_fields = ('program__name', 'test_center__name', 'test_center__campus__name')
