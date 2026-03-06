import re

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()


def _normalize_ke_phone(phone):
    """Normalize Kenyan phone numbers to 254XXXXXXXXX format."""
    if phone is None:
        return ''

    phone = re.sub(r'\D', '', str(phone).strip())
    if not phone:
        return ''

    if phone.startswith('0'):
        phone = '254' + phone[1:]
    elif (phone.startswith('7') or phone.startswith('1')) and len(phone) == 9:
        phone = '254' + phone
    elif phone.startswith('254'):
        pass

    return phone


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def clean_phone_number(self):
        phone = _normalize_ke_phone(self.cleaned_data.get('phone_number', ''))
        if len(phone) != 12:
            raise forms.ValidationError(
                'Please enter a valid Kenyan phone number (e.g., 0712345678 or 0112345678).'
            )
        return phone


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Username',
        widget=forms.TextInput(attrs={
            'placeholder': 'your username',
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

        # Allow partial updates: keep current values when optional fields are left blank.
        self.fields['full_name'].required = False
        self.fields['phone_number'].required = False

    def clean_full_name(self):
        full_name = (self.cleaned_data.get('full_name') or '').strip()
        if full_name:
            return full_name

        if self.instance and self.instance.pk:
            return self.instance.full_name

        return full_name

    def clean_phone_number(self):
        raw_phone = self.cleaned_data.get('phone_number')

        # If left blank during edit, keep the existing number.
        if not raw_phone:
            return self.instance.phone_number if self.instance and self.instance.pk else ''

        phone = _normalize_ke_phone(raw_phone)
        if len(phone) != 12:
            raise forms.ValidationError(
                'Please enter a valid Kenyan phone number (e.g., 0712345678 or 0112345678).'
            )

        # Enforce uniqueness but allow the current user's existing number.
        qs = User.objects.filter(phone_number=phone)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('This phone number is already in use.')

        return phone