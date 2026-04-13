from django.contrib import admin
from .models import FreightSettings


@admin.register(FreightSettings)
class FreightSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Freight Threshold', {
            'fields': ('freight_threshold', 'fixed_freight_fee'),
            'description': 'Orders below the threshold attract the fixed fee. Orders at or above are FIS.',
        }),
        ('Fuel Surcharge', {
            'fields': ('surcharge_enabled', 'surcharge_percentage'),
        }),
        ('Stair Void Trimmer Allowance', {
            'fields': ('stair_void_trimmer_allowance_lm',),
        }),
    )

    def has_add_permission(self, request):
        # Only allow one record
        return not FreightSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
