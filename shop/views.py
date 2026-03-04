from django.shortcuts import render, get_object_or_404, redirect

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Avg
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.template.loader import render_to_string

from .models import Category, Product, Cart, CartItem, Wishlist, Review, Order, OrderItem
from .utils import get_or_create_cart

import json


def home_view(request):
    # Hero products (featured/bestsellers)
    hero_products = Product.objects.filter(
        status='active',
        is_bestseller=True
    ).select_related('category').prefetch_related('images')[:4]
    
    # Sales banner products (special offers)
    sales_products = Product.objects.filter(
        status='active',
        is_special=True,
        compare_at_price__isnull=False
    ).select_related('category').prefetch_related('images')[:3]
    
    # Bestsellers
    bestsellers = Product.objects.filter(
        status='active')[:8]
        #is_bestseller=True
   # ).select_related('category').prefetch_related('images')[:8]
    
    # Special offers
    special_offers = Product.objects.filter(
        status='active')[:8]
        #is_special=True
    #).select_related('category').prefetch_related('images')[:8]
    
    # New arrivals
    new_arrivals = Product.objects.filter(
        status='active')[:8]
        #is_new_arrival=True
   # ).select_related('category').prefetch_related('images')[:8]
    
    context = {
        'hero_products': hero_products,
        'sales_products': sales_products,
        'bestsellers': bestsellers,
        'special_offers': special_offers,
        'new_arrivals': new_arrivals,
    }
    return render(request, 'shop/home.html', context)


def product_list_view(request):
    """Product listing with hierarchical categories and AI search."""
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    products = Product.objects.filter(status='active').select_related(
        'category'
    ).prefetch_related('images', 'reviews')
    
    # Category filtering with hierarchy
    current_category = None
    if category_slug:
        current_category = get_object_or_404(Category, slug=category_slug)
        # Get all subcategories
        category_ids = [current_category.id]
        subcategories = current_category.children.all()
        category_ids.extend([cat.id for cat in subcategories])
        products = products.filter(category_id__in=category_ids)
    
    # AI-like search (case-insensitive, partial match)
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
    
    # Sorting
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    elif sort_by == 'popular':
        products = products.order_by('-is_bestseller', '-created_at')
    else:
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get hierarchical categories for sidebar
    root_categories = Category.objects.filter(
        parent=None,
        is_active=True
    ).prefetch_related('children')
    
    context = {
        'products': page_obj,
        'current_category': current_category,
        'root_categories': root_categories,
        'search_query': search_query,
        'sort_by': sort_by,
        'is_paginated': page_obj.has_other_pages(),
    }
    
    # Handle AJAX requests for real-time search
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('shop/includes/product_grid.html', context, request=request)
        return JsonResponse({'html': html, 'count': products.count()})
    
    return render(request, 'shop/product_list.html', context)


def product_detail_view(request, slug):
    """Product detail page with reviews and related products."""
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('images', 'reviews__user'),
        slug=slug,
        status='active'
    )
    
    # Related products (same category)
    related_products = Product.objects.filter(
        category=product.category,
        status='active'
    ).exclude(id=product.id).prefetch_related('images')[:4]
    
    # Reviews
    reviews = product.reviews.filter(is_approved=True).select_related('user')
    
    # Check if in wishlist
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(
            user=request.user,
            products=product
        ).exists()
    
    # Stock alert
    stock_alert = None
    if product.is_low_stock:
        stock_alert = f"Only {product.stock_quantity} left in stock!"
    elif not product.is_in_stock:
        stock_alert = "Out of stock"
    
    context = {
        'product': product,
        'related_products': related_products,
        'reviews': reviews,
        'in_wishlist': in_wishlist,
        'stock_alert': stock_alert,
        'primary_image': product.images.filter(is_primary=True).first() or product.images.first(),
    }
    return render(request, 'shop/product_detail.html', context)


@require_POST
def add_to_cart_view(request):
    """Add product to cart via AJAX."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Please login to add items to cart'})
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Invalid data'})
    
    product = get_object_or_404(Product, id=product_id, status='active')
    
    if product.stock_quantity < quantity:
        return JsonResponse({
            'success': False,
            'message': f'Only {product.stock_quantity} items available'
        })
    
    cart, _ = Cart.objects.get_or_create(user=request.user)
    
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    
    return JsonResponse({
        'success': True,
        'message': f'{product.name} added to cart',
        'cart_count': cart.total_items,
        'cart_total': float(cart.total)
    })


@require_POST
def update_cart_view(request):
    """Update cart item quantity."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Please login'})
    
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Invalid data'})
    
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    
    if quantity <= 0:
        cart_item.delete()
        message = 'Item removed from cart'
    else:
        if quantity > cart_item.product.stock_quantity:
            return JsonResponse({
                'success': False,
                'message': f'Only {cart_item.product.stock_quantity} items available'
            })
        cart_item.quantity = quantity
        cart_item.save()
        message = 'Cart updated'
    
    cart = cart_item.cart
    return JsonResponse({
        'success': True,
        'message': message,
        'cart_count': cart.total_items,
        'cart_subtotal': float(cart.subtotal),
        'cart_total': float(cart.total),
        'item_total': float(cart_item.total_price) if quantity > 0 else 0
    })


@login_required
def cart_view(request):
    """Shopping cart page."""
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('product').prefetch_related('product__images')
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'shop/cart.html', context)


@require_POST
def toggle_wishlist_view(request):
    """Toggle product in wishlist."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Please login'})
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid data'})
    
    product = get_object_or_404(Product, id=product_id)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    
    if product in wishlist.products.all():
        wishlist.products.remove(product)
        in_wishlist = False
        message = 'Removed from wishlist'
        status='removed'
    else:
        wishlist.products.add(product)
        in_wishlist = True
        message = 'Added to wishlist'
        status='added'
    
    return JsonResponse({
        'status': status,
        'success': True,
        'message': message,
        'in_wishlist': in_wishlist,
        'wishlist_count': wishlist.total_items
    })


@login_required
def wishlist_view(request):
    """User wishlist page."""
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    products = wishlist.products.filter(status='active').prefetch_related('images')
    
    context = {
        'wishlist': wishlist,
        'products': products,
    }
    return render(request, 'shop/wishlist.html', context)


@login_required
def checkout_view(request):
    """Checkout page with auto-filled user data."""
    cart = get_object_or_404(Cart, user=request.user)
    
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty')
        return redirect('shop:cart')
    
    cart_items = cart.items.select_related('product').prefetch_related('product__images')
    
    context = {
        'user': request.user,
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'shop/checkout.html', context)


@require_POST
@login_required
def create_order_view(request):
    """Create order and initiate M-Pesa payment."""
    cart = get_object_or_404(Cart, user=request.user)
    
    if not cart.items.exists():
        return JsonResponse({'success': False, 'message': 'Cart is empty'})
    
    # Get shipping details (allow editing)
    full_name = request.POST.get('full_name', request.user.full_name)
    phone_number = request.POST.get('phone_number', request.user.phone_number)
    email = request.POST.get('email', request.user.email)
    address = request.POST.get('address', request.user.address)
    
    # Validate stock
    for item in cart.items.all():
        if item.quantity > item.product.stock_quantity:
            return JsonResponse({
                'success': False,
                'message': f'Insufficient stock for {item.product.name}'
            })
    
    # Create order
    order = Order.objects.create(
        user=request.user,
        full_name=full_name,
        phone_number=phone_number,
        email=email,
        address=address,
        subtotal=cart.subtotal,
        shipping_cost=0,  # Add shipping calculation
        total=cart.total,
    )
    
    # Create order items
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product.name,
            product_price=item.product.price,
            quantity=item.quantity
        )
        # Reduce stock
        item.product.stock_quantity -= item.quantity
        item.product.save()
    
    # Clear cart
    cart.items.all().delete()
    
    return JsonResponse({
        'success': True,
        'order_id': order.id,
        'order_number': order.order_number,
        'total': float(order.total),
        'phone': phone_number
    })


@login_required
def order_detail_view(request, order_number):
    """Order detail page."""
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        order_number=order_number,
        user=request.user
    )
    return render(request, 'shop/order_detail.html', {'order': order})


@require_POST
def add_review_view(request, product_id):
    """Add product review."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Please login'})
    
    product = get_object_or_404(Product, id=product_id)
    
    try:
        data = json.loads(request.body)
        rating = int(data.get('rating', 0))
        title = data.get('title', '')
        comment = data.get('comment', '')
        
        if not (1 <= rating <= 5):
            raise ValueError("Invalid rating")
            
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({'success': False, 'message': 'Invalid data'})
    
    review, created = Review.objects.update_or_create(
        product=product,
        user=request.user,
        defaults={
            'rating': rating,
            'title': title,
            'comment': comment,
            'is_approved': False  # Require approval
        }
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Review submitted and pending approval'
    })


def search_suggestions_view(request):
    """AJAX endpoint for search autocomplete."""
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    products = Product.objects.filter(
        Q(name__icontains=query) |
        Q(category__name__icontains=query),
        status='active'
    ).values('name', 'slug', 'price')[:5]
    
    suggestions = list(products)
    return JsonResponse({'suggestions': suggestions})