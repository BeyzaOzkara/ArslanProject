import logging
from .models import LastCheckedUretimRaporu, UretimBasilanBillet, Hareket, Location, KalipMs

logger = logging.getLogger(__name__)

def check_new_rapor():
    birinci_fab = ['1100-1', '1200-1', '1600-1']
    ikinci_fab = ['1100-2', '1100-3', '1600-2', '2750-1', '4000-1']
    # '1.Fabrika Kalıp Hazırlama': 545, '2.Fabrika Kalıp Hazırlama': 574

    pres_uretim = UretimBasilanBillet.objects.using('dies').order_by('Siralama').values('Siralama', 'KalipNo', 'PresKodu')
    last_checked= LastCheckedUretimRaporu.objects.latest('Siralama')
    last_checked_siralama = last_checked.Siralama


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
                    # last_location = DiesLocation.objects.filter(KalipNo = n['KalipNo']).first()
                    last_location = Location.objects.filter(presKodu__contains = n['PresKodu']).first()
                    kalip = KalipMs.objects.using('dies').filter(KalipNo=n['KalipNo']).first()
                    Hareket.objects.create(
                        kalipNo=kalip.KalipNo,
                        kalipKonum=last_location,
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