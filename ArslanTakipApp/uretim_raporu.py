from .models import LastCheckedUretimRaporu, UretimBasilanBillet

def check_new_rapor():
    pres_uretim = list(UretimBasilanBillet.objects.using('dies').order_by('Siralama').values('Siralama'))

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
    else:
        print("yeni rapor bulunmamaktadır.")