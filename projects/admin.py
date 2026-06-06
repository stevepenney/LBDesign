from django.contrib import admin
from .models import Project, ProjectDocument


class ProjectDocumentInline(admin.TabularInline):
    model = ProjectDocument
    extra = 0
    fields = ['document_type', 'name', 'file', 'external_url', 'uploaded_by', 'uploaded_at']
    readonly_fields = ['uploaded_by', 'uploaded_at']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display  = ['lb_ref', 'client_name', 'organisation', 'status', 'merchant_reference', 'created_at']
    list_filter   = ['status', 'organisation']
    search_fields = ['client_name', 'merchant_reference', 'site_address']
    readonly_fields = ['lb_job_number', 'created_at', 'updated_at']
    inlines = [ProjectDocumentInline]
    fieldsets = (
        (None, {
            'fields': ('lb_job_number', 'organisation', 'status'),
        }),
        ('Project Details', {
            'fields': ('client_name', 'site_address', 'merchant_reference', 'notes'),
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    ordering = ['-lb_job_number']

    def lb_ref(self, obj):
        return obj.lb_ref
    lb_ref.short_description = 'LB Job #'
    lb_ref.admin_order_field = 'lb_job_number'


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display  = ['display_name', 'project', 'document_type', 'uploaded_by', 'uploaded_at']
    list_filter   = ['document_type']
    search_fields = ['name', 'project__client_name']
    readonly_fields = ['uploaded_at']
