import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ArslanProject.settings')
django.setup()

from django.contrib.auth.models import User
from ArslanTakipApp.models import Hareket

users = User.objects.filter(username__icontains='zprb') | User.objects.filter(first_name__icontains='zprb') | User.objects.filter(username__icontains='mgmvt') | User.objects.filter(first_name__icontains='mgmvt')

for u in users:
    print(f"Suspicious User Found - ID: {u.id}, Username: {u.username}, First Name: {u.first_name}, Last Name: {u.last_name}")
