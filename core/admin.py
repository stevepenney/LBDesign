from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .help_registry import REGISTERED_TOPICS
from .models import Feedback, FreightSettings, HelpTopic, RoofPitch, StairVoidSettings


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
        ('Hardware Allowance', {
            'fields': ('hardware_allowance_pct',),
            'description': 'Default % added to materials cost on every estimate. Individual estimates can override this.',
        }),
        ('Estimate Uncertainty', {
            'fields': ('estimate_uncertainty_pct',),
            'description': 'Total uncertainty band shown on estimates. Half this value is displayed as ±% (e.g. 30 → displayed as ±15%).',
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


class HelpTopicAdminForm(forms.ModelForm):
    slug = forms.ChoiceField(
        choices=[(s, f'{s}  —  {desc}') for s, desc in REGISTERED_TOPICS.items()],
        help_text='Slugs are registered in core/help_registry.py whenever a {% help_trigger %} is added to a template.',
    )

    class Meta:
        model = HelpTopic
        fields = '__all__'


@admin.register(HelpTopic)
class HelpTopicAdmin(admin.ModelAdmin):
    form = HelpTopicAdminForm
    list_display = ['title', 'slug', 'location', 'sort_order', 'has_image']
    list_editable = ['sort_order']
    fields = ['title', 'slug', 'body', 'image', 'body_preview', 'sort_order']
    readonly_fields = ['body_preview']

    @admin.display(description='Template location')
    def location(self, obj):
        return REGISTERED_TOPICS.get(obj.slug, '—')

    @admin.display(description='Image', boolean=True)
    def has_image(self, obj):
        return bool(obj.image)

    @admin.display(description='Body preview')
    def body_preview(self, obj):
        if not obj.body:
            return '—'
        return format_html(
            '<div style="border:1px solid #ddd;border-radius:4px;padding:1rem;max-width:700px;">{}</div>',
            mark_safe(obj.body),
        )


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
