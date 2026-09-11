import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ArslanProject.settings')
django.setup()

from django.db import connections

try:
    with connections['dms'].cursor() as cursor:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        print(cursor.fetchall())
except Exception as e:
    print(e)
