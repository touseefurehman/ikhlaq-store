from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import *

# Remove or fix the custom admin site if you have it
# admin_site = CustomAdminSite(name='custom_admin')  # Comment or remove this

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price']
    can_delete = False
    max_num = 0

class OrderTrackingInline(admin.TabularInline):
    model = OrderTracking
    extra = 1
    readonly_fields = ['created_at']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # CORRECT: actions should be a list, not a method
    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled']
    
    list_display = ['order_id', 'full_name', 'email', 'total_amount', 
                    'payment_status', 'order_status', 'created_at', 'actions_column']
    list_filter = ['order_status', 'payment_status', 'created_at', 'city']
    search_fields = ['order_id', 'first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['order_id', 'created_at', 'updated_at', 'full_name_display']
    inlines = [OrderItemInline, OrderTrackingInline]
    list_per_page = 20
    
    # Custom fields display
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'user', 'full_name_display', 'email', 'phone', 'created_at')
        }),
        ('Shipping Information', {
            'fields': ('address', 'city', 'state', 'zip_code')
        }),
        ('Payment & Status', {
            'fields': ('total_amount', 'payment_status', 'order_status')
        }),
    )
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Customer Name'
    
    def full_name_display(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name_display.short_description = 'Customer Name'
    
    def actions_column(self, obj):
        return format_html(
            '<a class="button btn btn-sm btn-info" href="{}">View</a>&nbsp;'
            '<a class="button btn btn-sm btn-success" href="{}">Track</a>&nbsp;'
            '<a class="button btn btn-sm btn-warning" href="{}">Invoice</a>',
            reverse('admin:shop_order_change', args=[obj.id]),
            reverse('admin:order-tracking', args=[obj.id]),
            reverse('admin:order-invoice', args=[obj.id])
        )
    actions_column.short_description = 'Actions'
    actions_column.allow_tags = True
    
    # Custom admin actions
    def mark_as_processing(self, request, queryset):
        updated = queryset.update(order_status='processing')
        for order in queryset:
            OrderTracking.objects.create(
                order=order,
                status='processing',
                description='Order is being processed'
            )
        self.message_user(request, f'{updated} order(s) marked as processing.')
    mark_as_processing.short_description = "Mark selected as Processing"
    
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(order_status='shipped')
        for order in queryset:
            OrderTracking.objects.create(
                order=order,
                status='shipped',
                description='Order has been shipped'
            )
        self.message_user(request, f'{updated} order(s) marked as shipped.')
    mark_as_shipped.short_description = "Mark selected as Shipped"
    
    def mark_as_delivered(self, request, queryset):
        updated = queryset.update(order_status='delivered')
        for order in queryset:
            OrderTracking.objects.create(
                order=order,
                status='delivered',
                description='Order has been delivered'
            )
        self.message_user(request, f'{updated} order(s) marked as delivered.')
    mark_as_delivered.short_description = "Mark selected as Delivered"
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(order_status='cancelled')
        for order in queryset:
            OrderTracking.objects.create(
                order=order,
                status='cancelled',
                description='Order has been cancelled'
            )
        self.message_user(request, f'{updated} order(s) marked as cancelled.')
    mark_as_cancelled.short_description = "Mark selected as Cancelled"
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Create tracking entry when status changes
        if 'order_status' in form.changed_data:
            OrderTracking.objects.create(
                order=obj,
                status=obj.order_status,
                description=f"Order status changed to {obj.get_order_status_display()}"
            )

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # CORRECT: Empty list is fine too
    actions = ['activate_products', 'deactivate_products']
    
    list_display = ['name', 'category', 'price_display', 'discount_price_display', 
                   'stock', 'is_active', 'image_preview']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'category__name']
    list_editable = ['stock', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 20
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'slug', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price', 'stock')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def price_display(self, obj):
        return f"${obj.price}"
    price_display.short_description = 'Price'
    
    def discount_price_display(self, obj):
        return f"${obj.discount_price}" if obj.discount_price else "-"
    discount_price_display.short_description = 'Sale Price'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image'
    
    # Custom actions
    def activate_products(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} product(s) activated.')
    activate_products.short_description = "Activate selected products"
    
    def deactivate_products(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} product(s) deactivated.')
    deactivate_products.short_description = "Deactivate selected products"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    # CORRECT: Can be empty list
    actions = []
    
    list_display = ['name', 'slug', 'product_count', 'image_preview']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    def product_count(self, obj):
        return obj.product_set.count()
    product_count.short_description = 'Products'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image'

@admin.register(OrderTracking)
class OrderTrackingAdmin(admin.ModelAdmin):
    # CORRECT
    actions = []
    
    list_display = ['order_link', 'status', 'description', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__order_id', 'description', 'status']
    readonly_fields = ['created_at']
    list_per_page = 20
    
    def order_link(self, obj):
        url = reverse('admin:shop_order_change', args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_id)
    order_link.short_description = 'Order ID'
    order_link.admin_order_field = 'order__order_id'

# Simple registration for other models
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    actions = []
    list_display = ['id', 'user', 'session_key', 'total_items', 'total_price_display', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def total_items(self, obj):
        return obj.items.count()
    total_items.short_description = 'Items'
    
    def total_price_display(self, obj):
        return f"${obj.total_price}"
    total_price_display.short_description = 'Total'

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    actions = []
    list_display = ['cart', 'product', 'quantity', 'price_display']
    list_filter = ['cart']
    
    def price_display(self, obj):
        return f"${obj.total_price}"
    price_display.short_description = 'Total'

# If you have custom admin views, add them like this:
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse

@staff_member_required
def order_tracking_view(request, order_id):
    """Custom admin view for order tracking"""
    from django.shortcuts import get_object_or_404
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        description = request.POST.get('description')
        
        if status and description:
            OrderTracking.objects.create(
                order=order,
                status=status,
                description=description
            )
            order.order_status = status
            order.save()
            messages.success(request, 'Tracking updated successfully!')
            return redirect('admin:order-tracking', order_id=order_id)
    
    return render(request, 'admin/order_tracking.html', {
        'order': order,
        'title': f'Tracking Order {order.order_id}'
    })

@staff_member_required
def order_invoice_view(request, order_id):
    """Custom admin view for invoice"""
    from django.shortcuts import get_object_or_404
    order = get_object_or_404(Order, id=order_id)
    
    return render(request, 'admin/order_invoice.html', {
        'order': order,
        'title': f'Invoice - Order {order.order_id}'
    })

# Register custom admin URLs
from django.urls import path
from django.contrib import admin

class CustomAdminSite(admin.AdminSite):
    """Simple custom admin site without overriding get_urls incorrectly"""
    site_header = 'E-Store Administration'
    site_title = 'E-Store Admin Portal'
    index_title = 'Welcome to E-Store Admin Dashboard'

# If you want to use custom admin, uncomment these lines:
# admin_site = CustomAdminSite(name='custom_admin')
# admin_site.register(Order, OrderAdmin)
# admin_site.register(Product, ProductAdmin)
# admin_site.register(Category, CategoryAdmin)
# admin_site.register(OrderTracking, OrderTrackingAdmin)
# admin_site.register(Cart, CartAdmin)
# admin_site.register(CartItem, CartItemAdmin)

# But for simplicity, use default admin:
# Remove any custom admin site registration and use default