import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ArslanProject.settings')
django.setup()

from django.contrib.auth.models import User
from ArslanTakipApp.models import Hareket, DiesLocation

print("Recent Users:")
for u in User.objects.order_by('-date_joined')[:10]:
    print(f"ID: {u.id}, Username: {u.username}, First Name: {u.first_name}, Last Name: {u.last_name}, Date Joined: {u.date_joined}")

print("\nRecent Harekets (Transfers):")
for h in Hareket.objects.order_by('-hareketTarihi')[:10]:
    print(f"ID: {h.id}, KalipNo: {h.kalipNo}, From: {h.kalipKonum_id}, To: {h.kalipVaris_id}, By: {h.kimTarafindan_id}, Date: {h.hareketTarihi}")
