from django.contrib import admin

# Register your models here.
from .models import MpesaTransaction


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'checkout_request_id', 'order', 'phone_number',
        'amount', 'status', 'mpesa_receipt_number', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = [
        'checkout_request_id', 'merchant_request_id',
        'mpesa_receipt_number', 'phone_number'
    ]
    readonly_fields = [
        'order', 'merchant_request_id', 'checkout_request_id',
        'result_code', 'result_desc', 'amount', 'phone_number',
        'mpesa_receipt_number', 'transaction_date', 'created_at'
    ]
    date_hierarchy = 'created_at'