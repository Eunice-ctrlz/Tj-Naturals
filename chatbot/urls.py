from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('whatsapp/', views.whatsapp_redirect_view, name='whatsapp'),
    path('webhook/', views.chatbot_webhook_view, name='webhook'),
]