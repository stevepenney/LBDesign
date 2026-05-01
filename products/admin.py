from django.contrib import admin
from .models import Product, PriceBook, PriceBookEntry


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'product_type',
        'use_as_joist_rafter', 'use_as_boundary_joist',
        'use_as_stair_void_trimmer', 'use_as_beam',
        'is_active', 'sort_order',
    ]
    list_filter = [
        'product_type', 'is_active',
        'use_as_joist_rafter', 'use_as_boundary_joist',
        'use_as_stair_void_trimmer', 'use_as_beam',
    ]
    search_fields = ['name']
    list_editable = [
        'use_as_joist_rafter', 'use_as_boundary_joist',
        'use_as_stair_void_trimmer', 'use_as_beam',
        'is_active', 'sort_order',
    ]
    fieldsets = (
        (None, {
            'fields': ('name', 'product_type', 'is_active', 'sort_order'),
        }),
        ('Permitted Uses', {
            'description': 'Tick every role this product may be selected for.',
            'fields': (
                'use_as_joist_rafter',
                'use_as_boundary_joist',
                'use_as_stair_void_trimmer',
                'use_as_beam',
            ),
        }),
    )
    ordering = ['product_type', 'sort_order', 'name']


class PriceBookEntryInline(admin.TabularInline):
    model = PriceBookEntry
    extra = 0
    fields = ['product', 'price_per_lm']
    autocomplete_fields = ['product']


@admin.register(PriceBook)
class PriceBookAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_default', 'entry_count', 'organisations_count', 'updated_at', 'updated_by']
    list_filter = ['is_default']
    search_fields = ['name']
    inlines = [PriceBookEntryInline]
    fields = ['name', 'is_default', 'notes', 'updated_by']
    readonly_fields = ['updated_by']

    def entry_count(self, obj):
        return obj.entries.count()
    entry_count.short_description = 'Products'

    def organisations_count(self, obj):
        return obj.organisations.count()
    organisations_count.short_description = 'Orgs using'

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
