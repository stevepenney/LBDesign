from django import forms
from .models import Organisation


class OrganisationForm(forms.ModelForm):

    class Meta:
        model = Organisation
        fields = ['name', 'is_merchant', 'is_active', 'price_book']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. ITM Kaikoura'}),
        }
        labels = {
            'name': 'Organisation name',
            'is_merchant': 'Merchant access',
            'is_active': 'Active',
            'price_book': 'Price book override',
        }
        help_texts = {
            'is_merchant': 'Grants this organisation access to pricing and the estimation tool.',
            'price_book': 'Leave blank to use the default price book.',
        }
