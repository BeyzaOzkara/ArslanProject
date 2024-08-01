import logging
from .models import LastCheckedUretimRaporu, UretimBasilanBillet, Hareket, Location, KalipMs, DiesLocation

logger = logging.getLogger(__name__)

def check_new_rapor():
    birinci_fab = ['1100-1', '1200-1', '1600-1']
    ikinci_fab = ['1100-2', '1100-3', '1600-2', '2750-1', '4000-1']

    pres_uretim = UretimBasilanBillet.objects.using('dies').order_by('Siralama').values('Siralama', 'KalipNo', 'PresKodu').exclude(Sure__lte=10)
    last_checked= LastCheckedUretimRaporu.objects.latest('Siralama')
    last_checked_siralama = last_checked.Siralama

    # aynı kalıpların aynı gün içerisinde tekrarlama sorunlarını ortadan kaldırmak için Süreyi kısıtlayabiliriz.
    if last_checked_siralama:
        new_raports = pres_uretim.filter(Siralama__gt = last_checked_siralama)
    else:
        new_raports = pres_uretim

    if new_raports:
        LastCheckedUretimRaporu.objects.create(
            Siralama = new_raports.latest('Siralama')['Siralama']
        )

        for n in new_raports:
            if n['KalipNo'] != '':
                if n['PresKodu'] in birinci_fab:
                    varis = 547
                elif n['PresKodu'] in ikinci_fab:
                    varis = 766
                else:
                    continue
                try:
                    kalip = KalipMs.objects.using('dies').filter(KalipNo=n['KalipNo']).first()
                    last_location = DiesLocation.objects.filter(KalipNo = n['KalipNo']).first()
                    pres_location = Location.objects.filter(presKodu__contains = n['PresKodu']).first()
                    if last_location != pres_location:
                        Hareket.objects.create(
                        kalipNo=kalip.KalipNo,
                        kalipKonum=last_location,
                        kalipVaris_id=pres_location,
                        kimTarafindan_id=57,
                        aciklama = 'pres uretim raporu hazırlık'
                    )
                    Hareket.objects.create(
                        kalipNo=kalip.KalipNo,
                        kalipKonum=pres_location,
                        kalipVaris_id=varis,
                        kimTarafindan_id=57,
                        aciklama = n['Siralama']
                    )
                except Exception as e:
                    print(f"Error processing {n['Siralama']}: {e}")
                    logger.error(f"An error occurred while processing the {n['Siralama']}: {e}")
            else:
                continue
    else:
        print("yeni rapor bulunmamaktadır.")