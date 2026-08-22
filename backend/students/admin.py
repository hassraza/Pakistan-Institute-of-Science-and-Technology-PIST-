from django.contrib import admin

from .models import AcademicDocument, IntermediateRecord, MatricRecord, StudentIdSequence, StudentProfile, StudentTestScore


@admin.register(AcademicDocument)
class AcademicDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_type', 'student', 'file_name', 'verification_status', 'uploaded_at', 'updated_at')
    list_filter = ('document_type', 'verification_status')
    search_fields = ('file_name', 'student__student_id', 'student__user__email')
    readonly_fields = ('id', 'file_name', 'uploaded_at', 'updated_at')


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'full_name', 'email', 'created_at')
    search_fields = ('student_id', 'cnic', 'user__email')
    readonly_fields = ('student_id', 'created_at', 'updated_at')

    @admin.display(description='Email')
    def email(self, obj):
        return obj.user.email


@admin.register(StudentIdSequence)
class StudentIdSequenceAdmin(admin.ModelAdmin):
    list_display = ('year', 'last_value')


@admin.register(MatricRecord)
class MatricRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'board', 'passing_year', 'percentage')
    search_fields = ('student__student_id', 'student__user__email', 'board')


@admin.register(IntermediateRecord)
class IntermediateRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'group', 'passing_year', 'percentage')
    list_filter = ('group',)
    search_fields = ('student__student_id', 'student__user__email', 'board')


@admin.register(StudentTestScore)
class StudentTestScoreAdmin(admin.ModelAdmin):
    list_display = ('student', 'test_type', 'score', 'total_score', 'percentage', 'test_date')
    list_filter = ('test_type', 'test_date')
    search_fields = ('student__student_id', 'student__user__email')
