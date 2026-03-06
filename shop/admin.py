from django.contrib import admin
from .models import (
    Category, Product, ProductImage, Review,
    Cart, CartItem, Wishlist, Order, OrderItem, ShippingRate
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')


class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'price', 'stock_quantity',
        'is_in_stock', 'is_bestseller', 'is_special', 'is_new_arrival', 'status'
    ]
    list_filter = [
        'status', 'is_bestseller', 'is_special', 'is_new_arrival',
        'category', 'created_at'
    ]
    search_fields = ['name', 'sku', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    list_editable = [
        'price', 'stock_quantity',
        'is_bestseller', 'is_special', 'is_new_arrival',
        'status'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'sku', 'category', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'compare_at_price')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'low_stock_threshold', 'weight')
        }),
        ('Status & Flags', {
            'fields': ('status', 'is_bestseller', 'is_special', 'is_new_arrival')
        }),
    )


class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']
    actions = ['approve_reviews']
    
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = "Approve selected reviews"


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['total_price']


class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_items', 'subtotal', 'updated_at']
    inlines = [CartItemInline]
    readonly_fields = ['subtotal', 'total_items']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['total']


class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'user', 'full_name', 'total',
        'status', 'payment_status', 'created_at'
    ]
    list_filter = ['status', 'payment_status', 'created_at']
    search_fields = ['order_number', 'user__email', 'full_name', 'phone_number']
    inlines = [OrderItemInline]
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'created_at', 'updated_at')
        }),
        ('Shipping Details', {
            'fields': ('full_name', 'phone_number', 'email', 'address')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_status', 'transaction_id')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'shipping_cost', 'total')
        }),
    )


class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ['location_name', 'fee', 'is_active', 'display_order']
    list_filter = ['is_active']
    search_fields = ['location_name']
    list_editable = ['fee', 'is_active', 'display_order']


admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Wishlist)
admin.site.register(Order, OrderAdmin)
admin.site.register(ShippingRate, ShippingRateAdmin)

admin.site.site_header = 'TJ Naturals Admin'
admin.site.site_title = 'TJ Naturals Admin Portal'
admin.site.index_title = 'Store Management Dashboard'