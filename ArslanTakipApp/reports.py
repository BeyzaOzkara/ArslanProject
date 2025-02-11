import datetime
from django.contrib.auth.models import User
from .models import YudaOnayDurum, YudaForm

def get_user_full_name(user_id):
    user = User.objects.get(id=user_id)
    return f"{user.first_name} {user.last_name}"

def get_yudas():
    now = datetime.datetime.now()
    start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    two_days_ago = now - datetime.timedelta(hours=48)
    results = YudaOnayDurum.objects.filter((Q(yuda_tarih__lte=two_days_ago) & Q(yuda_tarih__gte=start_of_year)) & (Q(kaliphane_onay_durumu=1) | Q(satis_onay_durumu=1) | Q(mekanik_islem_onay_durumu=1))) \
    .values('yuda_id', 'yuda_tarih', 'firma_adi', 'kaliphane_onay_durumu', 'satis_onay_durumu', 'mekanik_islem_onay_durumu').order_by('yuda_tarih')

    yuda_ids = [onay['yuda_id'] for onay in results]
    yuda_forms = YudaForm.objects.filter(id__in=yuda_ids)

    for onay in results:
        yuda_form = yuda_forms.get(id=onay['yuda_id'])
        onay['yuda_no'] = yuda_form.YudaNo
        onay['yuda_acan_kisi'] = get_user_full_name(yuda_form.YudaAcanKisi.id)
        print(f"Yuda ID: {onay['yuda_id']}, Yuda Tarih: {onay['yuda_tarih']}, Firma Adi: {onay['firma_adi']}, Yuda No: {onay['yuda_no']}, Yuda Acan Kisi: {onay['yuda_acan_kisi']}")
