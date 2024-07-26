import logging
from .models import LastCheckedUretimRaporu, UretimBasilanBillet, Hareket, Location, DiesLocation

logger = logging.getLogger(__name__)

def check_new_rapor():
    birinci_fab = ['1100-1', '1200-1', '1600-1']
    ikinci_fab = ['1100-2', '1100-3', '1600-2', '2750-1', '4000-1']
    # '1.Fabrika Kalıp Hazırlama': 545, '2.Fabrika Kalıp Hazırlama': 574

    pres_uretim = list(UretimBasilanBillet.objects.using('dies').order_by('Siralama').values('Siralama', 'KalipNo', 'PresKodu'))

    last_checked, created = LastCheckedUretimRaporu.objects.get_or_create(id=1)
    last_checked_siralama = last_checked.Siralama

    if last_checked_siralama:
        last_index = next((i for i, entry in enumerate(pres_uretim) if entry['Siralama'] == last_checked_siralama), -1)
        new_rapors = pres_uretim[last_index +1:]
    else:
        new_rapors = pres_uretim

    if new_rapors:
        last_checked.Siralama = new_rapors[-1]['Siralama']
        last_checked.save()

        for n in new_rapors:
            if n['KalipNo'] != '':
                if n['PresKodu'] in birinci_fab:
                    print(f"birinci: {n}")
                    varis = 547
                elif n['PresKodu'] in ikinci_fab:
                    print(f"ikinci: {n}")
                    varis = 766
                else:
                    continue
                try:
                    # last_location = DiesLocation.objects.filter(KalipNo = n['KalipNo']).first()
                    last_location = Location.objects.filter(presKodu__contains = n['PresKodu']).first()

                    Hareket.objects.create(
                        kalipNo=n['KalipNo'],
                        kalipKonum=last_location,
                        kalipVaris_id=varis,
                        kimTarafindan_id=57,
                    )
                except Exception as e:
                    print(f"Error processing {n['Siralama']}: {e}")
                    logger.error(f"An error occurred while processing the {n['Siralama']}: {e}")
            else:
                continue
    else:
        print("yeni rapor bulunmamaktadır.")