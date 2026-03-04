from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('initiate/', views.initiate_payment_view, name='initiate'),
    path('callback/', views.mpesa_callback_view, name='callback'),
    path('check-status/', views.check_payment_status_view, name='check_status'),
]