import base64
import json
import requests
from datetime import datetime
from django.conf import settings


class MpesaHandler:
    """Handle M-Pesa STK Push integration."""
    
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE
        self.environment = settings.MPESA_ENVIRONMENT
        self.callback_url = settings.MPESA_CALLBACK_URL
        
        if self.environment == 'production':
            self.base_url = 'https://api.safaricom.co.ke'
        else:
            self.base_url = 'https://sandbox.safaricom.co.ke'
    
    def get_access_token(self):
        """Generate M-Pesa access token."""
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        
        credentials = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {credentials}'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result.get('access_token')
        except requests.RequestException as e:
            print(f"Error getting access token: {e}")
            return None
    
    def generate_password(self, timestamp):
        """Generate M-Pesa password."""
        data_to_encode = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(data_to_encode.encode()).decode()
    
    def format_phone_number(self, phone):
        """Format phone number to 254XXXXXXXXX format."""
        phone = str(phone).replace(' ', '').replace('-', '').replace('+', '')
        
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('7'):
            phone = '254' + phone
        elif phone.startswith('1'):
            phone = '254' + phone
            
        return phone
    
    def initiate_stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """Initiate STK Push request."""
        access_token = self.get_access_token()
        
        if not access_token:
            return {
                'success': False,
                'error': 'Failed to get access token'
            }
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = self.generate_password(timestamp)
        formatted_phone = self.format_phone_number(phone_number)
        
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': formatted_phone,
            'PartyB': self.shortcode,
            'PhoneNumber': formatted_phone,
            'CallBackURL': self.callback_url,
            'AccountReference': account_reference[:12],  # Max 12 chars
            'TransactionDesc': transaction_desc[:20]  # Max 20 chars
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('ResponseCode') == '0':
                return {
                    'success': True,
                    'checkout_request_id': result.get('CheckoutRequestID'),
                    'merchant_request_id': result.get('MerchantRequestID'),
                    'message': result.get('CustomerMessage', 'STK Push sent successfully')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('errorMessage', 'Unknown error')
                }
                
        except requests.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def query_transaction_status(self, checkout_request_id):
        """Query status of STK Push transaction."""
        access_token = self.get_access_token()
        
        if not access_token:
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = self.generate_password(timestamp)
        
        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'CheckoutRequestID': checkout_request_id
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )
            return response.json()
        except requests.RequestException as e:
            return {'error': str(e)}