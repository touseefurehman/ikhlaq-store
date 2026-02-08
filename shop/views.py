from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView
from .models import *
from .forms import OrderForm
from django.db.models import Q
import json

class ProductListView(ListView):
    model = Product
    template_name = 'shop/product_list.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True)
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)
        
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'shop/product_detail.html'
    context_object_name = 'product'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_products'] = Product.objects.filter(
            category=self.object.category,
            is_active=True
        ).exclude(id=self.object.id)[:4]
        return context

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    return JsonResponse({
        'success': True,
        'cart_total': cart.total_items
    })

def update_cart(request, item_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        quantity = data.get('quantity', 1)
        
        cart_item = get_object_or_404(CartItem, id=item_id)
        cart_item.quantity = quantity
        cart_item.save()
        
        return JsonResponse({
            'success': True,
            'item_total': cart_item.total_price,
            'cart_total': cart_item.cart.total_price
        })

def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart_item.delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    return redirect('cart_view')

def cart_view(request):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        cart = Cart.objects.filter(session_key=session_key).first()
    
    context = {'cart': cart}
    return render(request, 'shop/cart.html', context)

def checkout(request):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        cart = Cart.objects.filter(session_key=session_key).first()
    
    if not cart or cart.items.count() == 0:
        return redirect('product_list')
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.total_amount = cart.total_price
            
            if request.user.is_authenticated:
                order.user = request.user
            
            order.save()
            
            # Create order items
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.final_price
                )
            
            # Create initial tracking
            OrderTracking.objects.create(
                order=order,
                status='pending',
                description='Order placed successfully'
            )
            
            # Clear cart
            cart.delete()
            
            return render(request, 'shop/order_success.html', {'order': order})
    else:
        if request.user.is_authenticated:
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
            form = OrderForm(initial=initial_data)
        else:
            form = OrderForm()
    
    return render(request, 'shop/checkout.html', {
        'form': form,
        'cart': cart
    })

@staff_member_required
def admin_order_tracking(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        description = request.POST.get('description')
        
        OrderTracking.objects.create(
            order=order,
            status=status,
            description=description
        )
        
        order.order_status = status
        order.save()
        
        return redirect('admin_order_tracking', order_id=order_id)
    
    return render(request, 'admin/order_tracking.html', {
        'order': order,
        'title': f'Tracking Order {order.order_id}'
    })