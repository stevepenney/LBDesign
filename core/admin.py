from django.contrib import admin
from django.utils.html import format_html

from .models import Feedback, FreightSettings, RoofPitch, StairVoidSettings


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
    )

    def has_add_permission(self, request):
        return not FreightSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StairVoidSettings)
class StairVoidSettingsAdmin(admin.ModelAdmin):
    fields = ('allowance_lm',)

    def has_add_permission(self, request):
        return not StairVoidSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RoofPitch)
class RoofPitchAdmin(admin.ModelAdmin):
    list_display = ['label', 'pitch_degrees', 'pitch_factor_display', 'sort_order']
    list_editable = ['pitch_degrees', 'sort_order']
    ordering = ['sort_order', 'pitch_degrees']

    @admin.display(description='Factor (1/cos θ)')
    def pitch_factor_display(self, obj):
        return f'{obj.pitch_factor:.4f}'


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['submitted_at', 'user', 'page_title', 'page_url', 'has_screenshot']
    list_filter = ['submitted_at', 'user']
    readonly_fields = ['user', 'page_url', 'page_title', 'comments', 'screenshot_preview', 'submitted_at']
    fields = ['submitted_at', 'user', 'page_title', 'page_url', 'comments', 'screenshot_preview']
    ordering = ['-submitted_at']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return True

    @admin.display(description='Screenshot', boolean=True)
    def has_screenshot(self, obj):
        return bool(obj.screenshot)

    @admin.display(description='Screenshot')
    def screenshot_preview(self, obj):
        if obj.screenshot:
            return format_html(
                '<img src="{}" style="max-width:800px; max-height:600px; border:1px solid #ccc;">',
                obj.screenshot.url,
            )
        return '—'
