from django.contrib import admin
from .models import CutlistProject, MemberProductMapping


@admin.register(CutlistProject)
class CutlistProjectAdmin(admin.ModelAdmin):
    list_display  = ('name', 'project', 'created_by', 'updated_at')
    list_filter   = ('project__organisation',)
    search_fields = ('name', 'project__client_name', 'project__lb_job_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(MemberProductMapping)
class MemberProductMappingAdmin(admin.ModelAdmin):
    list_display  = ('raw_name', 'product', 'updated_at')
    search_fields = ('raw_name', 'normalized_name', 'product__name')
    readonly_fields = ('normalized_name', 'updated_at')
