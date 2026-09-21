import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ArslanProject.settings')
django.setup()

from ArslanTakipApp.email_utils import send_email
import logging

logging.basicConfig(level=logging.DEBUG)

try:
    print("Testing send_email...")
    send_email(
        to_addresses=['yazilim@arslanaluminyum.com'], 
        cc_recipients=[], 
        subject='Test Email', 
        body='<p>Test</p>'
    )
    print("Email send function completed.")
except Exception as e:
    print(f"Exception caught: {e}")
