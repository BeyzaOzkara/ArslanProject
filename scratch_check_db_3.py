import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ArslanProject.settings')
django.setup()

from ArslanTakipApp.models import KalipMs

dies = KalipMs.objects.using('dies').filter(KalipNo__icontains='zprb') | KalipMs.objects.using('dies').filter(KalipNo__icontains='mgmvt')

for d in dies:
    print(f"Suspicious Die Found: {d.KalipNo}")
