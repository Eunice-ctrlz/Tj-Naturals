from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
import re

User = get_user_model()

def normalize_phone_input(identifier):
    """Normalize input to Kenyan phone format if it looks like a phone number."""
    if not identifier:
        return identifier
        
    # Remove non-digits
    digits = re.sub(r'\D', '', str(identifier))
    
    # If it looks like a Kenyan phone number ( starts with 07, 01, 254...), try to normalize
    if len(digits) == 10 and (digits.startswith('07') or digits.startswith('01')):
        return '254' + digits[1:]
    elif len(digits) == 12 and digits.startswith('254'):
        return digits
    elif len(digits) == 9 and (digits.startswith('7') or digits.startswith('1')):
        return '254' + digits
        
    return identifier

class PhoneNumberBackend(ModelBackend):
    """
    Custom backend to allow login via phone number or username.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            return None
        
        try:
            # Check if user exists with this username
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # If not found by username, try phone number
            try:
                # Try exact match first
                user = User.objects.get(phone_number=username)
            except User.DoesNotExist:
                # Try normalized phone number
                normalized_phone = normalize_phone_input(username)
                if normalized_phone != username:
                    try:
                        user = User.objects.get(phone_number=normalized_phone)
                    except User.DoesNotExist:
                        return None
                else:
                    return None
        except User.MultipleObjectsReturned:
             # Should not happen with unique constraints
             return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
