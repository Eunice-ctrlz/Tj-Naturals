
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.conf import settings

from .mpesa import MpesaHandler
from .models import MpesaTransaction
from shop.models import Order


@login_required
@require_POST
def initiate_payment_view(request):
    """Initiate M-Pesa STK Push payment."""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        phone_number = data.get('phone_number')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if not phone_number:
        phone_number = order.phone_number
    
    mpesa = MpesaHandler()
    
    result = mpesa.initiate_stk_push(
        phone_number=phone_number,
        amount=int(order.total),
        account_reference=order.order_number,
        transaction_desc=f'Payment for order {order.order_number}'
    )
    
    if result['success']:
        MpesaTransaction.objects.create(
            order=order,
            merchant_request_id=result['merchant_request_id'],
            checkout_request_id=result['checkout_request_id'],
            amount=order.total,
            phone_number=mpesa.format_phone_number(phone_number),
            status='pending'
        )
        
        return JsonResponse({
            'success': True,
            'checkout_request_id': result['checkout_request_id'],
            'message': result['message']
        })
    else:
        return JsonResponse({
            'success': False,
            'error': result.get('error', 'Payment initiation failed')
        })


@csrf_exempt
@require_POST
def mpesa_callback_view(request):
    """Handle M-Pesa callback."""
    try:
        data = json.loads(request.body)
        
        stk_callback = data.get('Body', {}).get('stkCallback', {})
        merchant_request_id = stk_callback.get('MerchantRequestID')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        
        try:
            transaction = MpesaTransaction.objects.get(
                checkout_request_id=checkout_request_id
            )
        except MpesaTransaction.DoesNotExist:
            return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Transaction not found'})
        
        transaction.result_code = str(result_code)
        transaction.result_desc = result_desc
        
        if result_code == 0:
            callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            
            receipt_number = None
            transaction_date = None
            
            for item in callback_metadata:
                name = item.get('Name')
                value = item.get('Value')
                
                if name == 'MpesaReceiptNumber':
                    receipt_number = value
                elif name == 'TransactionDate':
                    from datetime import datetime
                    if value:
                        transaction_date = datetime.strptime(str(value), '%Y%m%d%H%M%S')
            
            transaction.mpesa_receipt_number = receipt_number
            transaction.transaction_date = transaction_date
            transaction.status = 'success'
            
            order = transaction.order
            order.payment_status = 'paid'
            order.transaction_id = receipt_number
            order.status = 'processing'
            order.save()
        else:
            transaction.status = 'failed'
        
        transaction.save()
        
        return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})
        
    except json.JSONDecodeError:
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'ResultCode': 1, 'ResultDesc': str(e)})


@login_required
def check_payment_status_view(request):
    """Check payment status via AJAX."""
    checkout_request_id = request.GET.get('checkout_request_id')
    
    if not checkout_request_id:
        return JsonResponse({'success': False, 'error': 'Missing checkout_request_id'})
    
    try:
        transaction = MpesaTransaction.objects.get(
            checkout_request_id=checkout_request_id,
            order__user=request.user
        )
        
        return JsonResponse({
            'success': True,
            'status': transaction.status,
            'receipt_number': transaction.mpesa_receipt_number,
            'order_number': transaction.order.order_number if transaction.status == 'success' else None
        })
    except MpesaTransaction.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Transaction not found'})
