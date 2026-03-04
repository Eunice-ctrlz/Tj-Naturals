from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings


@require_GET
def whatsapp_redirect_view(request):
    """Return WhatsApp business number for chatbot."""
    # Get business WhatsApp number from settings or use default
    whatsapp_number = getattr(settings, 'BUSINESS_WHATSAPP_NUMBER', '254712345678')
    
    # Remove any non-numeric characters
    whatsapp_number = ''.join(filter(str.isdigit, whatsapp_number))
    
    return JsonResponse({
        'success': True,
        'whatsapp_number': whatsapp_number,
        'whatsapp_link': f'https://wa.me/{whatsapp_number}',
        'message': 'Redirect to WhatsApp'
    })


@require_GET
def chatbot_webhook_view(request):
    """Simple webhook for basic chatbot responses."""
    message = request.GET.get('message', '').lower()
    
    responses = {
        'hello': 'Hi! Welcome to TJ Naturals. How can I help you today?',
        'hi': 'Hello! Looking for natural skincare products?',
        'products': 'We have a wide range of natural skincare products. Check out our shop!',
        'price': 'Our prices vary by product. Browse our catalog for details.',
        'shipping': 'We offer fast shipping across Kenya. Delivery within 1-3 days in Nairobi.',
        'payment': 'We accept M-Pesa for secure and instant payments.',
        'contact': 'You can reach us on WhatsApp for immediate assistance.',
        'help': 'I can help you with product info, orders, or connect you to our team on WhatsApp.',
    }
    
    # Find matching response
    response = responses.get('help')  # Default
    for key, value in responses.items():
        if key in message:
            response = value
            break
    
    return JsonResponse({
        'success': True,
        'response': response,
        'whatsapp_available': True
    })