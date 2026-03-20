import os
import smtplib
from decouple import config

# Load settings directly from .env to verify what the script sees
print("--- Testing Email Configuration ---")

try:
    email = config('EMAIL_HOST_USER')
    password = config('EMAIL_HOST_PASSWORD')
    host = config('EMAIL_HOST', default='smtp.gmail.com')
    port = config('EMAIL_PORT', default=587, cast=int)
    use_tls = config('EMAIL_USE_TLS', default=True, cast=bool)
    
    print(f"User: {email}")
    print(f"Host: {host}:{port}")
    # Don't print the password, but check length
    print(f"Password length: {len(password)}")
    
    print("\nAttempting connection...")
    server = smtplib.SMTP(host, port)
    server.ehlo()
    
    if use_tls:
        print("Starting TLS...")
        server.starttls()
        server.ehlo()
    
    print("Authenticating...")
    server.login(email, password)
    print("SUCCESS! Username and Password accepted.")
    server.quit()

except Exception as e:
    print(f"\nFAILED: {e}")
    print("\nTroubleshooting Tips:")
    print("1. Ensure 'App Password' is used, not your login password.")
    print("2. Ensure 2-Step Verification is ON for this Google account.")
    print("3. Check for leading/trailing spaces in .env file.")
