from django import forms
from django.forms import inlineformset_factory

from products.models import Product
from .models import Job, Section, FloorRoofArea, AdditionalBeam


class JobForm(forms.ModelForm):

    class Meta:
        model = Job
        fields = ['job_reference', 'client_name', 'site_address']
        widgets = {
            'job_reference': forms.TextInput(attrs={'placeholder': 'e.g. 2026-042 or Smith Residence'}),
            'client_name':   forms.TextInput(attrs={'placeholder': 'e.g. Smith Construction Ltd'}),
            'site_address':  forms.Textarea(attrs={'rows': 3, 'placeholder': '12 Example Street, Auckland'}),
        }


class SectionForm(forms.ModelForm):

    class Meta:
        model = Section
        fields = [
            'label', 'system_type',
            # Midfloor — boundary joists
            'include_boundary_joists', 'boundary_perimeter_lm', 'boundary_joist_product',
            # Midfloor — stair void trimmers
            'include_stair_void_trimmers', 'stair_void_trimmer_product',
            # Roof
            'roof_pitch',
        ]
        widgets = {
            'label': forms.TextInput(attrs={'placeholder': "e.g. Unit 1 Midfloor"}),
            'boundary_perimeter_lm': forms.NumberInput(
                attrs={'step': '0.1', 'placeholder': '0.0'}
            ),
        }
        labels = {
            'label': 'Sub-Job Label',
            'system_type': 'System Type',
            'include_boundary_joists': 'Include boundary joists',
            'boundary_perimeter_lm': 'Perimeter (lineal metres)',
            'boundary_joist_product': 'Member',
            'include_stair_void_trimmers': 'Include stair void trimmers',
            'stair_void_trimmer_product': 'Member',
            'roof_pitch': 'Roof pitch',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['boundary_joist_product'].queryset = (
            Product.objects.filter(use_as_boundary_joist=True, is_active=True)
        )
        self.fields['boundary_joist_product'].empty_label = '— select member —'
        self.fields['stair_void_trimmer_product'].queryset = (
            Product.objects.filter(use_as_stair_void_trimmer=True, is_active=True)
        )
        self.fields['stair_void_trimmer_product'].empty_label = '— select member —'
        self.fields['roof_pitch'].empty_label = '— select pitch —'

    def clean(self):
        cleaned = super().clean()
        system_type = cleaned.get('system_type')

        if system_type == Section.SystemType.MIDFLOOR:
            if cleaned.get('include_boundary_joists'):
                if not cleaned.get('boundary_perimeter_lm'):
                    self.add_error('boundary_perimeter_lm', 'Enter the perimeter when boundary joists are included.')
            cleaned['roof_pitch'] = None

        if system_type == Section.SystemType.ROOF:
            cleaned['include_boundary_joists'] = False
            cleaned['boundary_perimeter_lm'] = None
            cleaned['boundary_joist_product'] = None
            cleaned['include_stair_void_trimmers'] = False
            cleaned['stair_void_trimmer_product'] = None

        return cleaned


class FloorRoofAreaForm(forms.ModelForm):

    class Meta:
        model = FloorRoofArea
        fields = ['area_label', 'area_m2', 'joist_product', 'joist_spacing']
        widgets = {
            'area_label': forms.TextInput(attrs={'placeholder': 'e.g. Main Floor (optional)'}),
            'area_m2': forms.NumberInput(attrs={'step': '0.1', 'placeholder': '0.0'}),
            'joist_spacing': forms.NumberInput(attrs={'placeholder': '400', 'min': '100', 'max': '1200'}),
        }
        labels = {
            'area_label': 'Area label (optional)',
            'area_m2': 'Area (m²)',
            'joist_product': 'Joist / Rafter',
            'joist_spacing': 'Spacing (mm)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['joist_product'].queryset = (
            Product.objects.filter(use_as_joist_rafter=True, is_active=True)
        )
        self.fields['joist_product'].empty_label = '— select —'
        self.fields['joist_product'].required = False


class AdditionalBeamForm(forms.ModelForm):

    class Meta:
        model = AdditionalBeam
        fields = ['product', 'length_m', 'quantity']
        widgets = {
            'length_m': forms.NumberInput(attrs={'step': '0.1', 'placeholder': '0.0'}),
            'quantity': forms.NumberInput(attrs={'min': '1', 'placeholder': '1'}),
        }
        labels = {
            'product': 'Member',
            'length_m': 'Length (m)',
            'quantity': 'Qty',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = (
            Product.objects.filter(use_as_beam=True, is_active=True)
        )
        self.fields['product'].empty_label = '— select member —'
        self.fields['product'].required = False


FloorRoofAreaFormSet = inlineformset_factory(
    Section,
    FloorRoofArea,
    form=FloorRoofAreaForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True,
)

AdditionalBeamFormSet = inlineformset_factory(
    Section,
    AdditionalBeam,
    form=AdditionalBeamForm,
    extra=1,
    min_num=0,
    can_delete=True,
)
