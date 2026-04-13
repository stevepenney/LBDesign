from django.contrib import admin
from .models import Product, PriceBook, PriceBookEntry


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_type', 'product_use', 'is_active', 'sort_order']
    list_filter = ['product_type', 'product_use', 'is_active']
    search_fields = ['name']
    list_editable = ['sort_order', 'is_active']
    ordering = ['product_type', 'sort_order', 'name']


class PriceBookEntryInline(admin.TabularInline):
    model = PriceBookEntry
    extra = 0
    fields = ['product', 'price_per_lm']
    autocomplete_fields = ['product']


@admin.register(PriceBook)
class PriceBookAdmin(admin.ModelAdmin):
    list_display = ['organisation', 'updated_at', 'updated_by']
    inlines = [PriceBookEntryInline]

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
