from django.contrib import admin
from .models import CutlistProject


@admin.register(CutlistProject)
class CutlistProjectAdmin(admin.ModelAdmin):
    list_display  = ('name', 'project', 'created_by', 'updated_at')
    list_filter   = ('project__organisation',)
    search_fields = ('name', 'project__client_name', 'project__lb_job_number')
    readonly_fields = ('created_at', 'updated_at')
