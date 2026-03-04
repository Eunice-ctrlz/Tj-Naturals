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
    
    return context


def categories_context(request):
    """Add categories to template context."""
    return {
        'header_categories': Category.objects.filter(
            parent=None,
            is_active=True
        ).prefetch_related('children')[:6]
    }