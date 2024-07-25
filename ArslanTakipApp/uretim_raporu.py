from .models import LastCheckedUretimRaporu, PresUretimRaporu

def check_new_rapor():
    pres_uretim = PresUretimRaporu.objects.order_by('Tarih', 'BaslamaSaati')

    last_checked, created = LastCheckedUretimRaporu.objects.get_or_create(id=1)
    last_checked_testere_no = last_checked.PresTestereNo

    if last_checked_testere_no:
        new_rapors = pres_uretim.filter(PresTestereNo__gt = last_checked_testere_no)
    else:
        new_rapors = pres_uretim.all()

    if new_rapors.exists():
        print(new_rapors.values())