from django import forms
from .models import Project


class ProjectForm(forms.ModelForm):

    class Meta:
        model = Project
        fields = ['client_name', 'site_address', 'merchant_reference', 'status', 'notes']
        widgets = {
            'client_name':        forms.TextInput(attrs={'placeholder': 'e.g. Smith Construction Ltd'}),
            'site_address':       forms.Textarea(attrs={'rows': 3, 'placeholder': '12 Example Street, Auckland'}),
            'merchant_reference': forms.TextInput(attrs={'placeholder': 'e.g. 2605-123 or your own job reference'}),
            'notes':              forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'merchant_reference': 'Your Job Reference (optional)',
            'notes':              'Notes',
        }
