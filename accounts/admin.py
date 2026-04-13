from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Organisation, User


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_merchant', 'is_active', 'created_at']
    list_filter = ['is_merchant', 'is_active']
    search_fields = ['name']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'get_full_name', 'organisation', 'role', 'is_active']
    list_filter = ['role', 'is_active', 'organisation']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Lumberbank', {'fields': ('organisation', 'role')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Lumberbank', {'fields': ('organisation', 'role')}),
    )
