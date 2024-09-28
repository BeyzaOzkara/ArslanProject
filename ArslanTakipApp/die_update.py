from .models import KalipMs, DiesLocation, Hareket
from django.db import transaction

def check_new_dies():
    kalip_query = KalipMs.objects.using('dies').values('KalipNo')

    for k in kalip_query:
        kalip_no = k['KalipNo']
        if not DiesLocation.objects.filter(kalipNo=kalip_no).exists():
            with transaction.atomic():
                Hareket.objects.create(
                    kalipVaris_id=48, # Yeri Bilinmeyenler
                    kalipNo=k['KalipNo'],
                    kimTarafindan_id=57
                )         

def check_die_deletes():
    kalip_query = KalipMs.objects.using('dies').filter(Silindi=1).values('KalipNo')

    for k in kalip_query:
        kalip_no = k['KalipNo']

        if not DiesLocation.objects.filter(kalipNo=kalip_no, kalipVaris_id=1134).exists():
            try:
                last_loc = DiesLocation.objects.get(kalipNo = k['KalipNo']).kalipVaris_id
                with transaction.atomic():
                    Hareket.objects.create(
                        kalipKonum_id=last_loc,
                        kalipVaris_id=1134, #HURDA
                        kalipNo=k['KalipNo'],
                        kimTarafindan_id=57
                    )
            except DiesLocation.DoesNotExist:
                print(f"Warning: No location found for KalipNo: {kalip_no}")
