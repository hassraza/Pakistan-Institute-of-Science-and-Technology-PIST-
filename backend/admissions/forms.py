from django import forms


class ApplicationTrackForm(forms.Form):
    reference = forms.CharField(
        label='Application ID, Program Registration ID, or Roll Number',
        max_length=128,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., APP-2026-12345, CS26-0001, or PIST-ISB-CS-2026-0001'}),
    )
