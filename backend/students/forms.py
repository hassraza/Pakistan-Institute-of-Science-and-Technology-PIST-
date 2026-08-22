from __future__ import annotations

import re
from datetime import date

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.core.exceptions import ValidationError

from .models import AcademicDocument, IntermediateRecord, MatricRecord, StudentProfile, StudentTestScore


class StudentRegistrationForm(forms.Form):
    full_name = forms.CharField(max_length=150, label='Full name')
    email = forms.EmailField(label='Email address')
    cnic = forms.CharField(max_length=20, label='CNIC / B-Form number')
    date_of_birth = forms.DateField(label='Date of birth', widget=forms.DateInput(attrs={'type': 'date'}))
    phone = forms.CharField(max_length=20, label='Phone number')
    gender = forms.ChoiceField(label='Gender (optional)', choices=[('', 'Prefer not to say')] + list(StudentProfile.Gender.choices), required=False)
    father_name = forms.CharField(max_length=150, label='Father / guardian name (optional)', required=False)
    address = forms.CharField(label='Address (optional)', widget=forms.Textarea(attrs={'rows': 3}), required=False)
    nationality = forms.CharField(max_length=80, label='Nationality (optional)', required=False, initial='Pakistani')
    profile_photo = forms.ImageField(label='Profile photo (optional)', required=False)
    password = forms.CharField(label='Password', widget=forms.PasswordInput(render_value=False))
    confirm_password = forms.CharField(label='Confirm password', widget=forms.PasswordInput(render_value=False))
    terms = forms.BooleanField(label='I agree to the Terms of Service and Privacy Policy')
    website = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs['aria-describedby'] = f'id_{name}-error'
        today = date.today()
        self.fields['date_of_birth'].widget.attrs.update(
            min=self._shift_year(today, -getattr(settings, 'STUDENT_MAX_AGE', 100)).isoformat(),
            max=self._shift_year(today, -getattr(settings, 'STUDENT_MIN_AGE', 15)).isoformat(),
        )

    @staticmethod
    def _shift_year(value, years):
        try:
            return value.replace(year=value.year + years)
        except ValueError:
            return value.replace(month=2, day=28, year=value.year + years)

    def clean_full_name(self):
        value = ' '.join(self.cleaned_data['full_name'].split())
        minimum = getattr(settings, 'STUDENT_MIN_NAME_LENGTH', 3)
        if len(value) < minimum or not any(character.isalpha() for character in value):
            raise ValidationError(f'Enter a name of at least {minimum} characters containing letters.')
        return value

    def clean_email(self):
        value = self.cleaned_data['email'].strip().lower()
        if get_user_model().objects.filter(email__iexact=value).exists():
            raise ValidationError('An account with this email is already registered.')
        return value

    def clean_cnic(self):
        digits = re.sub(r'\D', '', self.cleaned_data['cnic'])
        if not re.fullmatch(r'\d{13}', digits):
            raise ValidationError('Enter a valid CNIC / B-Form number with 13 digits.')
        value = f'{digits[:5]}-{digits[5:12]}-{digits[12:]}'
        if StudentProfile.objects.filter(cnic=value).exists():
            raise ValidationError('This CNIC / B-Form number is already registered.')
        return value

    def clean_phone(self):
        digits = re.sub(r'\D', '', self.cleaned_data['phone'])
        if not re.fullmatch(r'03\d{9}', digits):
            raise ValidationError('Enter a valid Pakistani mobile number, such as 0300-1234567.')
        return digits

    def clean_date_of_birth(self):
        value = self.cleaned_data['date_of_birth']
        today = date.today()
        minimum_age = getattr(settings, 'STUDENT_MIN_AGE', 15)
        maximum_age = getattr(settings, 'STUDENT_MAX_AGE', 100)
        if value >= today:
            raise ValidationError('Date of birth must be in the past.')
        latest = self._shift_year(today, -minimum_age)
        earliest = self._shift_year(today, -maximum_age)
        if value > latest:
            raise ValidationError(f'You must be at least {minimum_age} years old.')
        if value < earliest:
            raise ValidationError(f'Please enter a realistic date of birth (maximum age {maximum_age}).')
        return value

    def clean_profile_photo(self):
        value = self.cleaned_data.get('profile_photo')
        if value:
            limit = getattr(settings, 'STUDENT_PHOTO_MAX_SIZE_MB', 2) * 1024 * 1024
            if value.size > limit:
                raise ValidationError(f'Profile photo must be {getattr(settings, "STUDENT_PHOTO_MAX_SIZE_MB", 2)}MB or smaller.')
            if value.content_type not in {'image/jpeg', 'image/png'}:
                raise ValidationError('Profile photo must be a JPG or PNG image.')
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') and cleaned.get('confirm_password') and cleaned['password'] != cleaned['confirm_password']:
            self.add_error('confirm_password', 'Passwords do not match.')
        if cleaned.get('password') and cleaned.get('email'):
            user = get_user_model()(username=cleaned['email'], email=cleaned['email'], first_name=cleaned.get('full_name', ''))
            try:
                password_validation.validate_password(cleaned['password'], user)
            except ValidationError as error:
                for message in error.messages:
                    self.add_error('password', message)
        return cleaned


class StudentProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs['aria-describedby'] = f'id_{name}-error'

    class Meta:
        model = StudentProfile
        fields = ('phone', 'gender', 'father_name', 'address', 'nationality', 'profile_photo')
        widgets = {'date_of_birth': forms.DateInput(attrs={'type': 'date'}), 'address': forms.Textarea(attrs={'rows': 3})}

    def clean_cnic(self):
        digits = re.sub(r'\D', '', self.cleaned_data['cnic'])
        if not re.fullmatch(r'\d{13}', digits):
            raise ValidationError('Enter a valid CNIC / B-Form number with 13 digits.')
        return f'{digits[:5]}-{digits[5:12]}-{digits[12:]}'

    def clean_phone(self):
        digits = re.sub(r'\D', '', self.cleaned_data['phone'])
        if not re.fullmatch(r'03\d{9}', digits):
            raise ValidationError('Enter a valid Pakistani mobile number, such as 0300-1234567.')
        return digits

    def clean_profile_photo(self):
        value = self.cleaned_data.get('profile_photo')
        if value:
            limit = getattr(settings, 'STUDENT_PHOTO_MAX_SIZE_MB', 2) * 1024 * 1024
            if value.size > limit:
                raise ValidationError(f'Profile photo must be {getattr(settings, "STUDENT_PHOTO_MAX_SIZE_MB", 2)}MB or smaller.')
            if value.content_type not in {'image/jpeg', 'image/png'}:
                raise ValidationError('Profile photo must be a JPG or PNG image.')
        return value


class StudentPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        User = get_user_model()
        return User._default_manager.filter(email__iexact=email, is_active=True, student_profile__isnull=False).order_by('pk')


class StudentPasswordChangeForm(PasswordChangeForm):
    pass


class AcademicDocumentForm(forms.ModelForm):
    class Meta:
        model = AcademicDocument
        fields = ('document_type', 'file')
        widgets = {
            'file': forms.ClearableFileInput(attrs={'accept': 'application/pdf,image/jpeg,image/png'}),
        }

    def clean_file(self):
        value = self.cleaned_data['file']
        from .validators import validate_academic_document

        validate_academic_document(value)
        return value


class AcademicDocumentReplaceForm(forms.ModelForm):
    class Meta:
        model = AcademicDocument
        fields = ('file',)
        widgets = {
            'file': forms.ClearableFileInput(attrs={'accept': 'application/pdf,image/jpeg,image/png'}),
        }

    def clean_file(self):
        value = self.cleaned_data['file']
        from .validators import validate_academic_document

        validate_academic_document(value)
        return value


class MatricRecordForm(forms.ModelForm):
    class Meta:
        model = MatricRecord
        fields = ('board', 'group', 'passing_year', 'obtained_marks', 'total_marks')


class IntermediateRecordForm(forms.ModelForm):
    class Meta:
        model = IntermediateRecord
        fields = ('board', 'group', 'passing_year', 'obtained_marks', 'total_marks')


class StudentTestScoreForm(forms.ModelForm):
    class Meta:
        model = StudentTestScore
        fields = ('test_type', 'score', 'total_score', 'test_date', 'result_certificate')
        widgets = {
            'test_date': forms.DateInput(attrs={'type': 'date'}),
            'result_certificate': forms.ClearableFileInput(attrs={'accept': 'application/pdf,image/jpeg,image/png'}),
        }

    def clean_result_certificate(self):
        value = self.cleaned_data.get('result_certificate')
        if value:
            from .validators import validate_academic_document

            validate_academic_document(value)
        return value


class ProgramApplicationForm(forms.Form):
    qualification = forms.ModelChoiceField(queryset=None, label='Qualifying examination')
    percentage = forms.DecimalField(min_value=0, max_value=100, max_digits=5, decimal_places=2, label='Qualifying examination percentage')

    def __init__(self, program, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.program = program
        from admissions.models import Qualification
        self.fields['qualification'].queryset = Qualification.objects.filter(
            pk__in=program.eligibility_rules.values('qualification_id'),
        )
