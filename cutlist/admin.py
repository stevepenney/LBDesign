from django.contrib import admin

from .models import CutlistProject


@admin.register(CutlistProject)
class CutlistProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'organisation', 'created_by', 'job', 'updated_at')
    list_filter = ('organisation',)
    search_fields = ('name', 'organisation__name')
    readonly_fields = ('created_at', 'updated_at')
