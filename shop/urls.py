from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('products/', views.product_list_view, name='product_list'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/update/', views.update_cart_view, name='update_cart'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/', views.toggle_wishlist_view, name='toggle_wishlist'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('checkout/create-order/', views.create_order_view, name='create_order'),
    path('order/<str:order_number>/', views.order_detail_view, name='order_detail'),
    path('review/<int:product_id>/add/', views.add_review_view, name='add_review'),
    path('search/suggestions/', views.search_suggestions_view, name='search_suggestions'),
]