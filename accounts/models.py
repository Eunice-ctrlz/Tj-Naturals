from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

class User(AbstractUser):
    
    phone_regex = RegexValidator(
        regex=r'^(?:\+254|254|0)?([71]\d{8})$',
        message="Enter a valid phone number (e.g. 0712345678 or 254712345678)"
    )
    
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=15, 
        unique=True,
        blank=True,
        null=True
    )
    
    full_name = models.CharField(max_length=100)
    address = models.TextField()
    email = models.EmailField(unique=True,blank=True, null=True)
    username = models.CharField(max_length=50, unique=True)
    
    profile_image = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        # Store blank email as NULL so unique constraint does not clash on ''.
        if self.email == '':
            self.email = None
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.username

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=50)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'User Activities'