from django import forms
from .models import Project, ProjectDocument


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


class ProjectDocumentForm(forms.ModelForm):

    class Meta:
        model = ProjectDocument
        fields = ['document_type', 'name', 'file', 'external_url', 'notes']
        widgets = {
            'name':         forms.TextInput(attrs={'placeholder': 'e.g. Ground Floor Plan (optional)'}),
            'external_url': forms.URLInput(attrs={'placeholder': 'https://drive.google.com/...'}),
            'notes':        forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional notes'}),
        }
        labels = {
            'external_url': 'Cloud Storage Link',
            'name':         'Document Name (optional)',
            'notes':        'Notes (optional)',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Merchants can only add drawings and other; LB staff can add any type
        if user and not (getattr(user, 'is_lb_admin', False) or getattr(user, 'is_lb_detailing', False)):
            self.fields['document_type'].choices = [
                choice for choice in ProjectDocument.DocumentType.choices
                if choice[0] in ('drawing', 'other')
            ]

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('file') and not cleaned.get('external_url'):
            raise forms.ValidationError(
                'Please either upload a file or provide a cloud storage link.'
            )
        return cleaned
