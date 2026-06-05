from django.contrib import admin
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display  = ['lb_ref', 'client_name', 'organisation', 'status', 'merchant_reference', 'created_at']
    list_filter   = ['status', 'organisation']
    search_fields = ['client_name', 'merchant_reference', 'site_address']
    readonly_fields = ['lb_job_number', 'created_at', 'updated_at']
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
