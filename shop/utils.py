from types import SimpleNamespace
from .models import Cart, CartItem, Product, Wishlist


def get_or_create_cart(request):
    """Get or create cart for user."""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        return cart
    return None


def merge_carts(request):
    """Merge guest cart into user cart on login and clear session afterwards."""
    # 1. Cart
    guest_cart = request.session.get('guest_cart', {})
    if guest_cart:
        user_cart, _ = Cart.objects.get_or_create(user=request.user)
        
        # Prepare data for batch processing (or loop)
        product_ids = []
        quantities = {}
        for pid_str, qty_val in guest_cart.items():
            try:
                pid = int(pid_str)
                qty = int(qty_val)
                if qty > 0:
                    product_ids.append(pid)
                    quantities[pid] = qty
            except (ValueError, TypeError):
                continue
        
        if product_ids:
            products = Product.objects.filter(id__in=product_ids, status='active')
            for product in products:
                qty = quantities.get(product.id, 0)
                
                cart_item, created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    product=product,
                    defaults={'quantity': 0}
                )
                
                # If creating new, quantity is 0 from defaults, so add qty
                # If existing, add qty to current quantity
                new_qty = cart_item.quantity + qty
                
                # Check stock
                if new_qty > product.stock_quantity:
                    new_qty = product.stock_quantity 
                
                cart_item.quantity = new_qty
                cart_item.save()
        
        # Only clear if we processed it
        if 'guest_cart' in request.session:
            del request.session['guest_cart']

    # 2. Wishlist
    guest_wishlist = request.session.get('guest_wishlist', [])
    if guest_wishlist:
        try:
            wishlist_ids = [int(pid) for pid in guest_wishlist if str(pid).isdigit()]
            if wishlist_ids:
                user_wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
                wishlist_products = Product.objects.filter(id__in=wishlist_ids)
                for product in wishlist_products:
                    user_wishlist.products.add(product)
        except (ValueError, TypeError):
            pass
            
        if 'guest_wishlist' in request.session:
            del request.session['guest_wishlist']

    request.session.modified = True
