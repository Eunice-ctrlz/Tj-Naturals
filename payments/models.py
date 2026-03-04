from django.db import models
from django.contrib.auth import get_user_model
from shop.models import Order

User = get_user_model()


class MpesaTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='mpesa_transactions'
    )
    merchant_request_id = models.CharField(max_length=100)
    checkout_request_id = models.CharField(max_length=100, unique=True)
    result_code = models.CharField(max_length=10, blank=True, null=True)
    result_desc = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=13)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True, null=True)
    transaction_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"M-Pesa {self.checkout_request_id} - {self.status}"