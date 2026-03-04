from .models import Cart


def get_or_create_cart(request):
    """Get or create cart for user."""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        return cart
    return None