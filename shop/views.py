from django.shortcuts import render, get_object_or_404, redirect

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Avg
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from decimal import Decimal
from types import SimpleNamespace

from .models import Category, Product, Cart, CartItem, Wishlist, Review, Order, OrderItem, ShippingRate
from .utils import get_or_create_cart

import json


SESSION_CART_KEY = 'guest_cart'
SESSION_WISHLIST_KEY = 'guest_wishlist'


def _get_guest_cart(request):
    """Return normalized guest cart data from session."""
    cart = request.session.get(SESSION_CART_KEY, {})
    if not isinstance(cart, dict):
        return {}

    normalized = {}
    for product_id, qty in cart.items():
        try:
            pid = int(product_id)
            qty = int(qty)
        except (TypeError, ValueError):
            continue

        if qty > 0:
            normalized[str(pid)] = qty
    return normalized


def _save_guest_cart(request, cart):
    request.session[SESSION_CART_KEY] = cart
    request.session.modified = True


def _get_guest_wishlist(request):
    """Return normalized guest wishlist product IDs from session."""
    wishlist = request.session.get(SESSION_WISHLIST_KEY, [])
    if not isinstance(wishlist, list):
        return []

    normalized = []
    for product_id in wishlist:
        try:
            normalized.append(int(product_id))
        except (TypeError, ValueError):
            continue
    return normalized


def _save_guest_wishlist(request, wishlist_ids):
    request.session[SESSION_WISHLIST_KEY] = wishlist_ids
    request.session.modified = True


def _build_guest_cart_context(request):
    """Build cart-like objects that cart template can render for guests."""
    cart_data = _get_guest_cart(request)
    if not cart_data:
        empty_cart = SimpleNamespace(subtotal=Decimal('0.00'), total=Decimal('0.00'), total_items=0)
        return empty_cart, []

    product_ids = [int(pid) for pid in cart_data.keys()]
    products = Product.objects.filter(id__in=product_ids, status='active').select_related('category').prefetch_related('images')
    product_map = {product.id: product for product in products}

    items = []
    subtotal = Decimal('0.00')
    total_items = 0
    cleaned_cart = {}

    for product_id_str, quantity in cart_data.items():
        product_id = int(product_id_str)
        product = product_map.get(product_id)
        if not product:
            continue

        if quantity > product.stock_quantity:
            quantity = product.stock_quantity
        if quantity <= 0:
            continue

        cleaned_cart[str(product.id)] = quantity
        item_total = product.price * quantity
        subtotal += item_total
        total_items += quantity
        items.append(
            SimpleNamespace(
                id=product.id,
                product=product,
                quantity=quantity,
                total_price=item_total,
            )
        )

    if cleaned_cart != cart_data:
        _save_guest_cart(request, cleaned_cart)

    guest_cart = SimpleNamespace(subtotal=subtotal, total=subtotal, total_items=total_items)
    return guest_cart, items


def home_view(request):
    active_products = Product.objects.filter(status='active').select_related('category').prefetch_related('images')

    # Hero products (featured/bestsellers)
    hero_products = active_products.filter(is_bestseller=True)[:4]

    # Sales banner products (special offers)
    sales_products = active_products.filter(
        is_special=True,
        compare_at_price__isnull=False,
    )[:3]

    # Homepage sections controlled by admin flags.
    bestsellers = active_products.filter(is_bestseller=True)[:8]
    special_offers = active_products.filter(is_special=True)[:8]
    new_arrivals = active_products.filter(is_new_arrival=True)[:8]

    # Keep sections populated if flags are not set yet.
    if not bestsellers:
        bestsellers = active_products[:8]
    if not special_offers:
        special_offers = active_products[:8]
    if not new_arrivals:
        new_arrivals = active_products[:8]
    
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
        # Gracefully ignore stale/invalid slugs instead of returning a 404 page.
        current_category = Category.objects.filter(slug=category_slug, is_active=True).first()
        if current_category:
            category_ids = [current_category.id]
            subcategories = current_category.children.filter(is_active=True)
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
    else:
        in_wishlist = product.id in _get_guest_wishlist(request)
    
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
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Invalid data'})
    
    product = get_object_or_404(Product, id=product_id, status='active')
    
    if product.stock_quantity < quantity:
        return JsonResponse({
            'status': 'error',
            'success': False,
            'message': f'Only {product.stock_quantity} items available'
        })

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.stock_quantity:
                return JsonResponse({
                    'status': 'error',
                    'success': False,
                    'message': f'Only {product.stock_quantity} items available'
                })
            cart_item.quantity = new_quantity
            cart_item.save()

        cart_count = cart.total_items
        cart_total = float(cart.total)
    else:
        guest_cart = _get_guest_cart(request)
        current_quantity = guest_cart.get(str(product.id), 0)
        new_quantity = current_quantity + quantity

        if new_quantity > product.stock_quantity:
            return JsonResponse({
                'status': 'error',
                'success': False,
                'message': f'Only {product.stock_quantity} items available'
            })

        guest_cart[str(product.id)] = new_quantity
        _save_guest_cart(request, guest_cart)

        guest_cart_obj, _ = _build_guest_cart_context(request)
        cart_count = guest_cart_obj.total_items
        cart_total = float(guest_cart_obj.total)

    return JsonResponse({
        'status': 'success',
        'success': True,
        'message': f'{product.name} added to cart',
        'cart_count': cart_count,
        'cart_total': cart_total
    })


@require_POST
def update_cart_view(request):
    """Update cart item quantity."""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Invalid data'})
    
    if request.user.is_authenticated:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

        if quantity <= 0:
            cart_item.delete()
            message = 'Item removed from cart'
            item_total = 0
        else:
            if quantity > cart_item.product.stock_quantity:
                return JsonResponse({
                    'success': False,
                    'message': f'Only {cart_item.product.stock_quantity} items available'
                })
            cart_item.quantity = quantity
            cart_item.save()
            message = 'Cart updated'
            item_total = float(cart_item.total_price)

        cart = cart_item.cart
        cart_count = cart.total_items
        cart_subtotal = float(cart.subtotal)
        cart_total = float(cart.total)
    else:
        product = get_object_or_404(Product, id=item_id, status='active')
        guest_cart = _get_guest_cart(request)
        product_key = str(product.id)

        if quantity <= 0:
            guest_cart.pop(product_key, None)
            message = 'Item removed from cart'
            item_total = 0
        else:
            if quantity > product.stock_quantity:
                return JsonResponse({
                    'success': False,
                    'message': f'Only {product.stock_quantity} items available'
                })
            guest_cart[product_key] = quantity
            message = 'Cart updated'
            item_total = float(product.price * quantity)

        _save_guest_cart(request, guest_cart)
        guest_cart_obj, _ = _build_guest_cart_context(request)
        cart_count = guest_cart_obj.total_items
        cart_subtotal = float(guest_cart_obj.subtotal)
        cart_total = float(guest_cart_obj.total)

    return JsonResponse({
        'success': True,
        'message': message,
        'cart_count': cart_count,
        'cart_subtotal': cart_subtotal,
        'cart_total': cart_total,
        'item_total': item_total
    })


def cart_view(request):
    """Shopping cart page."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.select_related('product').prefetch_related('product__images')
    else:
        cart, cart_items = _build_guest_cart_context(request)
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'shop/cart.html', context)


@require_POST
def toggle_wishlist_view(request):
    """Toggle product in wishlist."""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid data'})
    
    product = get_object_or_404(Product, id=product_id)

    if request.user.is_authenticated:
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)

        if product in wishlist.products.all():
            wishlist.products.remove(product)
            in_wishlist = False
            message = 'Removed from wishlist'
            status = 'removed'
        else:
            wishlist.products.add(product)
            in_wishlist = True
            message = 'Added to wishlist'
            status = 'added'

        wishlist_count = wishlist.total_items
    else:
        wishlist_ids = _get_guest_wishlist(request)
        if product.id in wishlist_ids:
            wishlist_ids = [pid for pid in wishlist_ids if pid != product.id]
            in_wishlist = False
            message = 'Removed from wishlist'
            status = 'removed'
        else:
            wishlist_ids.append(product.id)
            in_wishlist = True
            message = 'Added to wishlist'
            status = 'added'

        _save_guest_wishlist(request, wishlist_ids)
        wishlist_count = len(wishlist_ids)

    return JsonResponse({
        'status': status,
        'success': True,
        'message': message,
        'in_wishlist': in_wishlist,
        'wishlist_count': wishlist_count
    })


def wishlist_view(request):
    """User wishlist page."""
    if request.user.is_authenticated:
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        products = wishlist.products.filter(status='active').prefetch_related('images')
    else:
        wishlist_ids = _get_guest_wishlist(request)
        products = Product.objects.filter(id__in=wishlist_ids, status='active').prefetch_related('images')
        wishlist = SimpleNamespace(total_items=products.count())
    
    context = {
        'wishlist': wishlist,
        'products': products,
    }
    return render(request, 'shop/wishlist.html', context)


@login_required
def checkout_view(request):
    """Checkout page with auto-filled user data."""
    # Ensure we get the fresh cart and items, creating if needed
    cart, _ = Cart.objects.get_or_create(user=request.user)
    
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty')
        return redirect('shop:cart')
    
    # 1) Prefetch items to avoid N+1 in template
    # 2) Calculate subtotal manually to ensure it matches exactly what users see (and avoid property caching weirdness)
    cart_items = cart.items.select_related('product').prefetch_related('product__images')
    
    # Force evaluation of subtotal from the fetched items (source of truth)
    calculated_subtotal = sum(item.total_price for item in cart_items)
    
    # Override cart.subtotal for display consistency if needed, 
    # but passing it explicitly is safer.
    
    shipping_rates = list(ShippingRate.objects.filter(is_active=True).order_by('display_order', 'location_name'))
    if not shipping_rates:
        shipping_rates = [
            SimpleNamespace(location_name='Thika', fee=Decimal('200.00')),
            SimpleNamespace(location_name='Nairobi / Kiambu', fee=Decimal('300.00')),
            SimpleNamespace(location_name='Major towns (Nakuru, Mombasa, Kisumu, Eldoret)', fee=Decimal('400.00')),
            SimpleNamespace(location_name='Other locations', fee=Decimal('500.00')),
        ]

    context = {
        'user': request.user,
        'cart': cart,
        'cart_items': cart_items,
        'calculated_subtotal': calculated_subtotal,
        'shipping_rates': shipping_rates,
        'free_shipping_threshold': Decimal('3000.00'),
    }
    return render(request, 'shop/checkout.html', context)


@require_POST
@login_required
def create_order_view(request):
    """Create order for manual paybill checkout."""
    cart = get_object_or_404(Cart, user=request.user)
    
    if not cart.items.exists():
        return JsonResponse({'success': False, 'message': 'Cart is empty'})
    
    try:
        payload = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    except json.JSONDecodeError:
        payload = request.POST

    # Get shipping details (allow editing)
    full_name = payload.get('full_name', request.user.full_name)
    phone_number = payload.get('phone_number', request.user.phone_number)
    email = payload.get('email', request.user.email)
    address = payload.get('address', request.user.address)
    
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
        payment_method='manual_paybill',
        payment_status='pending',
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