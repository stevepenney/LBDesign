from django import forms
from django.contrib import admin
from django.urls import path

from .admin_import import import_products_csv, import_pricebook_entries_csv
from .models import Product, ProductType, PriceBook, PriceBookEntry, TimberTypeDefaultStockLengths


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'sort_order', 'product_count']
    list_editable = ['sort_order']
    ordering = ['sort_order', 'name']

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'product_type', 'stock_lengths',
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
        'stock_lengths',
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
        ('Cutlist Optimizer', {
            'description': 'Stock lengths offered as defaults when a cutlist member is linked '
                            'to this product. Leave blank to use the generic default for this '
                            "product's timber type (see Timber Type Default Stock Lengths).",
            'fields': ('stock_lengths',),
        }),
    )
    ordering = ['product_type__sort_order', 'sort_order', 'name']

    def get_urls(self):
        return [
            path('import-csv/', self.admin_site.admin_view(import_products_csv),
                 name='products_product_import_csv'),
        ] + super().get_urls()


@admin.register(TimberTypeDefaultStockLengths)
class TimberTypeDefaultStockLengthsAdmin(admin.ModelAdmin):
    list_display = ['timber_type', 'stock_lengths']
    list_editable = ['stock_lengths']
    ordering = ['timber_type']


class PriceBookEntryInline(admin.TabularInline):
    model = PriceBookEntry
    extra = 0
    fields = ['product', 'price_per_lm']
    autocomplete_fields = ['product']


class PriceBookAdminForm(forms.ModelForm):
    pricing_csv = forms.FileField(
        required=False,
        help_text='Optional. Columns: product_name, price_per_lm. Uploading here fully '
                   "replaces this price book's entries with what's in the file — any existing "
                   "entry for a product not present in this upload is removed.",
    )

    class Meta:
        model = PriceBook
        fields = ['name', 'is_default', 'notes', 'updated_by']


@admin.register(PriceBook)
class PriceBookAdmin(admin.ModelAdmin):
    form = PriceBookAdminForm
    list_display = ['name', 'is_default', 'entry_count', 'organisations_count', 'updated_at', 'updated_by']
    list_filter = ['is_default']
    search_fields = ['name']
    inlines = [PriceBookEntryInline]
    fields = ['name', 'is_default', 'notes', 'updated_by', 'pricing_csv']
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

        uploaded_file = form.cleaned_data.get('pricing_csv')
        if uploaded_file:
            import_pricebook_entries_csv(request, obj, uploaded_file)
