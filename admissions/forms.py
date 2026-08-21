from django import forms


class ApplicationTrackForm(forms.Form):
    reference = forms.CharField(
        label='Roll Number or Application ID',
        max_length=128,
        widget=forms.TextInput(attrs={'placeholder': 'Enter roll number or application UUID'}),
    )
