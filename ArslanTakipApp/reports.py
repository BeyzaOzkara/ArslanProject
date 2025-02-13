import datetime
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.db.models import Q
from .models import YudaOnayDurum, YudaForm
from .email_utils import send_email


def format_date(date):
    return date.strftime("%d-%m-%Y")

def get_user_full_name(user_id):
    user = User.objects.get(id=user_id)
    return f"{user.first_name} {user.last_name}"

def get_yudas():
    now = datetime.datetime.now()
    start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    two_days_ago = now - datetime.timedelta(hours=48)
    results = YudaOnayDurum.objects.filter((Q(yuda_tarih__lte=two_days_ago) & Q(yuda_tarih__gte=start_of_year)) & (Q(kaliphane_onay_durumu=1) | Q(satis_onay_durumu=1) | Q(mekanik_islem_onay_durumu=1))) \
        .exclude(Silindi=True).values('yuda_id', 'yuda_tarih', 'firma_adi', 'kaliphane_onay_durumu', 'satis_onay_durumu', 'mekanik_islem_onay_durumu').order_by('yuda_tarih')

    yuda_ids = [onay['yuda_id'] for onay in results]
    yuda_forms = YudaForm.objects.filter(id__in=yuda_ids)

    for onay in results:
        firma_adi_first_word = onay['firma_adi'].split()[0] if onay['firma_adi'] else ''
        onay['firma_adi'] = firma_adi_first_word
        yuda_form = yuda_forms.get(id=onay['yuda_id'])
        onay['yuda_no'] = yuda_form.YudaNo
        onay['yuda_acan_kisi'] = get_user_full_name(yuda_form.YudaAcanKisi.id)
        onay['yuda_tarih'] = format_date(onay['yuda_tarih'])
    return results

def send_report_email():
    to_addresses = ['yazilim@arslanaluminyum.com']
    cc_addresses = []
    subject = f"Yuda Onay Durum Raporu"
    try:
        yudaList = get_yudas()
        html_message = render_to_string('mail/yuda_onay_durum_raporu.html', {
            'yudaList': yudaList,
        })
        body = html_message

        send_email(to_addresses=to_addresses, cc_recipients=cc_addresses, subject= subject, body= body)
    except Exception as e:
        print(f"Error sending email: {e}")
    