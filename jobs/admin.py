from django.contrib import admin
from .models import (
    Job, Section, FloorRoofArea, CladdingArea, CladdingExtraItem, AdditionalBeam,
    CutlistImportLine, CladdingCutlistLine, DrawingUpload,
)


class FloorRoofAreaInline(admin.TabularInline):
    model = FloorRoofArea
    extra = 1
    fields = ['area_label', 'area_m2', 'joist_product', 'joist_spacing', 'roof_pitch']


class CladdingAreaInline(admin.TabularInline):
    model = CladdingArea
    extra = 1
    fields = ['area_label', 'orientation', 'width_m', 'height_m', 'cladding_product']


class CladdingExtraItemInline(admin.TabularInline):
    model = CladdingExtraItem
    extra = 0
    fields = ['product_description', 'product', 'length_m', 'quantity']


class AdditionalBeamInline(admin.TabularInline):
    model = AdditionalBeam
    extra = 0
    fields = ['product', 'length_m', 'quantity']


class CutlistImportLineInline(admin.TabularInline):
    model = CutlistImportLine
    extra = 0
    fields = ['product', 'product_description', 'length_m', 'quantity']


class CladdingCutlistLineInline(admin.TabularInline):
    model = CladdingCutlistLine
    extra = 0
    fields = ['product', 'product_description', 'length_m', 'quantity']


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
        'label', 'system_type', 'wastage_pct', 'hardware_allowance_pct',
        'include_boundary_joists', 'boundary_perimeter_lm', 'boundary_joist_product',
        'include_stair_void_trimmers', 'stair_void_trimmer_product',
        'calculated_subtotal', 'hardware_allowance_amount',
    ]
    readonly_fields = ['calculated_subtotal', 'hardware_allowance_amount']


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display  = ['__str__', 'project', 'created_at']
    list_filter   = ['project__organisation']
    search_fields = ['label', 'project__client_name', 'project__site_address', 'project__lb_job_number']
    readonly_fields = ['created_at', 'updated_at', 'freight_charge', 'freight_surcharge']
    inlines = [SectionInline, DrawingUploadInline]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display  = ['label', 'job', 'system_type', 'calculated_subtotal', 'hardware_allowance_amount']
    list_filter   = ['system_type']
    search_fields = ['label', 'job__project__client_name']
    readonly_fields = ['calculated_subtotal', 'hardware_allowance_amount', 'member_schedule']
    inlines = [
        FloorRoofAreaInline, AdditionalBeamInline, CutlistImportLineInline,
        CladdingAreaInline, CladdingExtraItemInline, CladdingCutlistLineInline,
    ]
