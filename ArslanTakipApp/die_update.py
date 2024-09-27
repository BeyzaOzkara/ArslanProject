from .models import KalipMs, DiesLocation, Hareket

def check_die_updates():
    all_dies = KalipMs.objects.using('dies').all()
    
