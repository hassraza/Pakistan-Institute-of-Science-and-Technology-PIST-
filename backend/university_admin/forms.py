from django import forms

from admissions.models import PISTApplicant


class StaffLoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


class ApplicationStatusForm(forms.ModelForm):
    class Meta:
        model = PISTApplicant
        fields = ['status']
