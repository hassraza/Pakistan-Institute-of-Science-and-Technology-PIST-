from __future__ import annotations

from decimal import Decimal
from django import forms
from django.utils import timezone

from admissions.models import Campus, Department, PISTApplicant, Program, TestCenter, TestSession
from students.models import AcademicDocument, StudentProfile


class StaffLoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'placeholder': 'Staff Username or Email', 'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'}))


class ApplicationStatusForm(forms.ModelForm):
    class Meta:
        model = PISTApplicant
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class ApplicationAcceptForm(forms.Form):
    admission_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional admission remarks or instructions for the student...', 'class': 'form-control'}),
        label='Admission Remarks',
    )
    confirm_acceptance = forms.BooleanField(
        required=True,
        initial=True,
        label='Confirm acceptance and notify candidate',
    )


class ApplicationRejectForm(forms.Form):
    rejection_reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Provide specific reason (e.g. Ineligible percentage, incomplete documents, quota filled)...', 'class': 'form-control'}),
        label='Reason for Rejection',
    )


class ScheduleTestForm(forms.Form):
    test_session = forms.ModelChoiceField(
        queryset=TestSession.objects.none(),
        required=False,
        label='Select Active Test Session',
        empty_label='-- Choose Existing Test Session (Recommended) --',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    custom_test_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Custom Test Date (if no session chosen)',
    )
    custom_reporting_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        label='Custom Reporting Time',
    )
    custom_venue = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. PIST Islamabad Main Campus', 'class': 'form-control'}),
        label='Custom Venue',
    )
    custom_building = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Block A', 'class': 'form-control'}),
        label='Custom Building',
    )
    custom_hall = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Hall 2', 'class': 'form-control'}),
        label='Custom Hall',
    )

    def __init__(self, *args, program=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = TestSession.objects.filter(is_active=True).select_related('test_center', 'program').order_by('test_date', 'reporting_time')
        if program:
            qs = qs.filter(program=program)
        self.fields['test_session'].queryset = qs


class ProgramSettingsForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ['admissions_open', 'eligibility_percentage', 'application_deadline', 'duration', 'required_test_type']
        widgets = {
            'admissions_open': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'eligibility_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'application_deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'required_test_type': forms.Select(attrs={'class': 'form-control'}),
        }


class ProgramCreateForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = [
            'department', 'campus', 'name', 'code', 'description',
            'degree_level', 'duration', 'eligibility_percentage',
            'required_test_type', 'application_deadline', 'admissions_open',
        ]
        widgets = {
            'department': forms.Select(attrs={'class': 'form-control'}),
            'campus': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'degree_level': forms.Select(attrs={'class': 'form-control'}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'eligibility_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'required_test_type': forms.Select(attrs={'class': 'form-control'}),
            'application_deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'admissions_open': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TestSessionForm(forms.ModelForm):
    class Meta:
        model = TestSession
        fields = ['test_center', 'program', 'test_date', 'reporting_time', 'start_time', 'building', 'hall', 'available_seats', 'is_active']
        widgets = {
            'test_center': forms.Select(attrs={'class': 'form-control'}),
            'program': forms.Select(attrs={'class': 'form-control'}),
            'test_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reporting_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'building': forms.TextInput(attrs={'class': 'form-control'}),
            'hall': forms.TextInput(attrs={'class': 'form-control'}),
            'available_seats': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BroadcastNotificationForm(forms.Form):
    AUDIENCE_CHOICES = [
        ('all', 'All Registered Students'),
        ('program', 'Students by Program'),
        ('single', 'Specific Student (by Student ID or CNIC)'),
    ]

    target_audience = forms.ChoiceField(
        choices=AUDIENCE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'targetAudienceSelect'}),
        label='Recipient Audience',
    )
    program = forms.ModelChoiceField(
        queryset=Program.objects.all().order_by('name'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'programSelect'}),
        label='Target Program',
        empty_label='-- Select Program --',
    )
    student_identifier = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. PIST-2026-0001 or CNIC 35201-1234567-1', 'id': 'studentIdInput'}),
        label='Student ID or CNIC',
    )
    title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Notice / Announcement Title'}),
        label='Notification Title',
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Write your message or official instructions here...'}),
        label='Notification Content',
    )
