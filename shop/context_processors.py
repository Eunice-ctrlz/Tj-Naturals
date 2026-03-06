from .models import Cart, Wishlist, Category

def cart_and_wishlist_counts(request):
    """Add cart and wishlist counts to all templates."""
    context = {
        'cart_count': 0,
        'wishlist_count': 0,
        'user_wishlist_ids': [],
    }
    
    if request.user.is_authenticated:
        # Cart count
        try:
            cart = Cart.objects.get(user=request.user)
            context['cart_count'] = cart.total_items
        except Cart.DoesNotExist:
            pass
        
        # Wishlist count and IDs
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            context['wishlist_count'] = wishlist.total_items
            context['user_wishlist_ids'] = list(
                wishlist.products.values_list('id', flat=True)
            )
        except Wishlist.DoesNotExist:
            pass
    else:
        guest_cart = request.session.get('guest_cart', {})
        if isinstance(guest_cart, dict):
            try:
                context['cart_count'] = sum(max(int(qty), 0) for qty in guest_cart.values())
            except (TypeError, ValueError):
                context['cart_count'] = 0

        guest_wishlist = request.session.get('guest_wishlist', [])
        if isinstance(guest_wishlist, list):
            cleaned_ids = []
            for product_id in guest_wishlist:
                try:
                    cleaned_ids.append(int(product_id))
                except (TypeError, ValueError):
                    continue

            context['wishlist_count'] = len(cleaned_ids)
            context['user_wishlist_ids'] = cleaned_ids
    
    return context


def categories_context(request):
    """Add categories to template context."""
    categories = list(
        Category.objects.filter(parent=None, is_active=True)
        .prefetch_related('children')
    )

    # Keep browse categories compact, but always include Hair Accessories.
    featured = categories[:6]
    hair_accessories = next((c for c in categories if c.slug == 'hair-accessories'), None)
    if hair_accessories and hair_accessories not in featured:
        featured = featured[:-1] + [hair_accessories]

    return {
        'header_categories': featured
    }