import re

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import User

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    phone_number = forms.CharField(
        max_length=13,
        widget=forms.TextInput(attrs={
            'placeholder': '254712345678',
            'class': 'form-control'
        })
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter your full address',
            'class': 'form-control',
            'rows': 1
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'your@gmail.com',
            'class': 'form-control'
        })
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'johndoe',
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = User
        fields = ['phone_number', 'email', 'username', 'address', 'password1', 'password2']
    
    import re
from django import forms

def clean_phone_number(self):
    
    phone = self.cleaned_data.get('phone_number', '').strip()
    
   
    phone = re.sub(r'\D', '', phone)
    
    
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    
    
    elif (phone.startswith('7') or phone.startswith('1')) and len(phone) == 9:
        phone = '254' + phone

    
    if len(phone) != 12:
        raise forms.ValidationError("Please enter a valid Kenyan phone number (e.g., 0712345678 or 0112345678).")
        
    return phone
    
def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})


class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'your@email.com',
            'class': 'form-control'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-control'
        })
    )


class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['full_name','email', 'phone_number','address', 'profile_image']
        widgets = {
            'full_name':forms.TextInput(attrs={'class':'form-control'}),
            #'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

            
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        phone = phone.replace(' ', '').replace('-', '')
        
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('+'):
            phone = phone[1:]
        elif not phone.startswith('254'):
            phone = '254' + phone
            
        return phone