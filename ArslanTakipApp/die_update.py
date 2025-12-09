from .models import KalipMs, DiesLocation, Hareket
from django.db import transaction

def check_new_dies():
    # 1) MSSQL tarafındaki tüm kalıp numaralarını çek (sadece kalipNo, düz liste)
    kalip_nos = set(
        KalipMs.objects.using('dies')
        .values_list('KalipNo', flat=True)
    )

    if not kalip_nos:
        return

    # 2) PostgreSQL tarafında halihazırda DiesLocation'da olan kalıpları çek
    existing_nos = set(
        DiesLocation.objects
        .filter(kalipNo__in=kalip_nos)
        .values_list('kalipNo', flat=True)
        .distinct()
    )

    # 3) Aradaki fark = yeni kalıplar
    missing_nos = kalip_nos - existing_nos
    if not missing_nos:
        return

    # 4) Hepsi için tek seferde Hareket oluştur (bulk_create)
    hareketler = [
        Hareket(
            kalipVaris_id=48,   # Yeri Bilinmeyenler
            kalipNo=no,
            kimTarafindan_id=57,  # Yapay Zeka user
            aciklama="Yeni Kalıp",
        )
        for no in missing_nos
    ]

    with transaction.atomic():
        Hareket.objects.bulk_create(hareketler, ignore_conflicts=True)
    # kalip_query = KalipMs.objects.using('dies').values('KalipNo')

    # for k in kalip_query:
    #     kalip_no = k['KalipNo']
    #     if not DiesLocation.objects.filter(kalipNo=kalip_no).exists():
    #         with transaction.atomic():
    #             Hareket.objects.create(
    #                 kalipVaris_id=48, # Yeri Bilinmeyenler
    #                 kalipNo=k['KalipNo'],
    #                 kimTarafindan_id=57, # Yapay Zeka user
    #                 aciklama="Yeni Kalıp"
    #             )         

def check_die_deletes():
    # 1) MSSQL: Silinmiş kalıpların numaraları
    deleted_nos = list(
        KalipMs.objects.using('dies')
        .filter(Silindi=1)
        .values_list('KalipNo', flat=True)
    )

    if not deleted_nos:
        return

    # 2) PostgreSQL: Zaten HURDA'da olan kalıpları bul
    already_scrapped = set(
        DiesLocation.objects
        .filter(kalipNo__in=deleted_nos, kalipVaris_id=1134)
        .values_list('kalipNo', flat=True)
        .distinct()
    )

    # 3) İşlem yapılması gerekenler
    to_process = [no for no in deleted_nos if no not in already_scrapped]
    if not to_process:
        return

    # 4) Bu kalıpların son lokasyonlarını tek query ile al
    last_locations_qs = (
        DiesLocation.objects
        .filter(kalipNo__in=to_process)
        .order_by('kalipNo', '-id')  # id'e göre son kayıt
        .values('kalipNo', 'kalipVaris_id')
    )

    last_location_by_no = {}
    for row in last_locations_qs:
        no = row['kalipNo']
        if no not in last_location_by_no:
            last_location_by_no[no] = row['kalipVaris_id']

    # 5) Hareket'leri toplu hazırla
    hareketler = []
    for kalip_no, last_loc in last_location_by_no.items():
        hareketler.append(
            Hareket(
                kalipKonum_id=last_loc,
                kalipVaris_id=1134,  # HURDA
                kalipNo=kalip_no,
                kimTarafindan_id=57,
                aciklama="Kalıp Hurda",
            )
        )

    if not hareketler:
        return

    with transaction.atomic():
        Hareket.objects.bulk_create(hareketler, ignore_conflicts=True)
    # kalip_query = KalipMs.objects.using('dies').filter(Silindi=1).values('KalipNo')

    # for k in kalip_query:
    #     kalip_no = k['KalipNo']

    #     if not DiesLocation.objects.filter(kalipNo=kalip_no, kalipVaris_id=1134).exists():
    #         try:
    #             last_loc = DiesLocation.objects.get(kalipNo = k['KalipNo']).kalipVaris_id
    #             with transaction.atomic():
    #                 Hareket.objects.create(
    #                     kalipKonum_id=last_loc,
    #                     kalipVaris_id=1134, #HURDA
    #                     kalipNo=k['KalipNo'],
    #                     kimTarafindan_id=57,
    #                     aciklama="Kalıp Hurda"
    #                 )
    #         except DiesLocation.DoesNotExist:
    #             print(f"Warning: No location found for KalipNo: {kalip_no}")
