from django.shortcuts import render, redirect

# Create your views here.
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from .forms import UserRegistrationForm, UserLoginForm, UserProfileUpdateForm
from shop.models import Cart, Wishlist, Order


def register_view(request):
    if request.user.is_authenticated:
        return redirect('shop:home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to TJ Naturals, {user.full_name}!')
            
            # Redirect to next page if specified
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
                
            return redirect('shop:home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('shop:home')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.full_name}!')
                
                # Redirect to next page if specified
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('shop:home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('shop:home')


@login_required
def profile_view(request):
    user = request.user
    cart = Cart.objects.filter(user=user).first()
    wishlist = Wishlist.objects.filter(user=user).first()
    orders = Order.objects.filter(user=user).order_by('-created_at')[:10]
    
   
    if wishlist:
        wishlist_items = wishlist.products.all()[:4]
        wishlist_count = wishlist.products.count()
    else:
        wishlist_items = []
        wishlist_count = 0
    
    context = {
        'user': user,
        'cart_items_count': cart.items.count() if cart else 0,
        'wishlist_items_count': wishlist_count, 
        'wishlist_items': wishlist_items,  
        'orders': orders,
    }
    return render(request, 'accounts/profile.html', context)
@login_required
def profile_edit_view(request):
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('accounts:profile')
        else:
            
            print("Form errors:", form.errors)
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserProfileUpdateForm(instance=request.user)
    
    return render(request, 'accounts/profile_edit.html', {'form': form})
   