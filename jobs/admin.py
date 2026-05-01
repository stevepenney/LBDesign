from django.contrib import admin
from .models import Job, Section, FloorRoofArea, AdditionalBeam, DrawingUpload


class FloorRoofAreaInline(admin.TabularInline):
    model = FloorRoofArea
    extra = 1
    fields = ['area_label', 'area_m2', 'joist_product', 'joist_spacing']


class AdditionalBeamInline(admin.TabularInline):
    model = AdditionalBeam
    extra = 0
    fields = ['product', 'length_m', 'quantity']


class DrawingUploadInline(admin.TabularInline):
    model = DrawingUpload
    extra = 0
    readonly_fields = ['uploaded_by', 'uploaded_at', 'original_filename']
    fields = ['file', 'original_filename', 'uploaded_by', 'uploaded_at']


class SectionInline(admin.StackedInline):
    model = Section
    extra = 0
    show_change_link = True
    fields = [
        'label', 'system_type',
        'include_boundary_joists', 'boundary_perimeter_lm', 'boundary_joist_product',
        'include_stair_void_trimmers', 'stair_void_trimmer_product',
        'roof_pitch', 'calculated_subtotal',
    ]
    readonly_fields = ['calculated_subtotal']


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['job_reference', 'client_name', 'organisation', 'status', 'created_at']
    list_filter = ['status', 'organisation']
    search_fields = ['job_reference', 'client_name', 'site_address']
    readonly_fields = ['created_at', 'updated_at', 'freight_charge', 'freight_surcharge']
    inlines = [SectionInline, DrawingUploadInline]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['label', 'job', 'system_type', 'calculated_subtotal']
    list_filter = ['system_type']
    search_fields = ['label', 'job__job_reference']
    readonly_fields = ['calculated_subtotal', 'member_schedule']
    inlines = [FloorRoofAreaInline, AdditionalBeamInline]


