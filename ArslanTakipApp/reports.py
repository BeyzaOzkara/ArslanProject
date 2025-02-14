from collections import defaultdict
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
        .values('yuda_id', 'yuda_tarih', 'firma_adi', 'kaliphane_onay_durumu', 'satis_onay_durumu', 'mekanik_islem_onay_durumu').order_by('yuda_tarih')

    yuda_ids = [onay['yuda_id'] for onay in results]
    yuda_forms = {yuda.id: yuda for yuda in YudaForm.objects.filter(id__in=yuda_ids)}

    for index, onay in enumerate(results):
        # Assign row class based on even/odd index
        onay['row_class'] = "even-row" if index % 2 == 0 else "odd-row"
        firma_adi = onay.get('firma_adi', '')  
        onay['firma_adi'] = firma_adi.split()[0] if firma_adi else 'N/A'  
        yuda_form = yuda_forms.get(onay['yuda_id'])  
        if yuda_form:
            onay['yuda_no'] = yuda_form.YudaNo
            onay['yuda_acan_kisi'] = get_user_full_name(yuda_form.YudaAcanKisi.id)
        else:
            onay['yuda_no'] = 'Unknown'
            onay['yuda_acan_kisi'] = 'Unknown'

        onay['yuda_tarih'] = format_date(onay['yuda_tarih'])

    return results

def get_results(bolum):
    now = datetime.datetime.now() # günlerden pazartesi ise 72 saat 
    start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    two_days_ago = now - datetime.timedelta(hours=48)
    filter_conditions = {
        'kaliphane': Q(kaliphane_onay_durumu=1),
        'mekanik': Q(mekanik_islem_onay_durumu=1),
    }

    if bolum not in filter_conditions:
        return []
    
    results = YudaOnayDurum.objects.filter(Q(yuda_tarih__lte=two_days_ago, yuda_tarih__gte=start_of_year) & filter_conditions[bolum]) \
        .values('yuda_id', 'yuda_tarih', 'firma_adi','kaliphane_onay_durumu', 'satis_onay_durumu', 'mekanik_islem_onay_durumu').order_by('yuda_tarih')

    yuda_ids = [onay['yuda_id'] for onay in results]
    yuda_forms = {yuda.id: yuda for yuda in YudaForm.objects.filter(id__in=yuda_ids)}

    for index, onay in enumerate(results):
        # Assign row class based on even/odd index
        onay['row_class'] = "even-row" if index % 2 == 0 else "odd-row"
        firma_adi = onay.get('firma_adi', '')  
        onay['firma_adi'] = firma_adi.split()[0] if firma_adi else 'N/A'  
        yuda_form = yuda_forms.get(onay['yuda_id'])  
        if yuda_form:
            onay['yuda_no'] = yuda_form.YudaNo
            onay['yuda_acan_kisi'] = get_user_full_name(yuda_form.YudaAcanKisi.id)
        else:
            onay['yuda_no'] = 'Unknown'
            onay['yuda_acan_kisi'] = 'Unknown'

        onay['yuda_tarih'] = format_date(onay['yuda_tarih'])
    return results

def get_satis_groups():
    now = datetime.datetime.now() # günlerden pazartesi ise 72 saat 
    start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    two_days_ago = now - datetime.timedelta(hours=48)
    
    results = YudaOnayDurum.objects.filter(Q(yuda_tarih__lte=two_days_ago, yuda_tarih__gte=start_of_year) & Q(satis_onay_durumu=1)) \
        .values('yuda_id', 'yuda_tarih', 'firma_adi','kaliphane_onay_durumu', 'satis_onay_durumu', 'mekanik_islem_onay_durumu').order_by('yuda_tarih')

    yuda_ids = [onay['yuda_id'] for onay in results]
    yuda_forms = {yuda.id: yuda for yuda in YudaForm.objects.filter(id__in=yuda_ids)}


    grouped_results = defaultdict(list)
    for onay in results:
        # Assign row class based on even/odd index
        yuda_form = yuda_forms.get(onay['yuda_id'])  
        if yuda_form:
            onay['yuda_no'] = yuda_form.YudaNo
            yuda_acan_kisi_id = yuda_form.YudaAcanKisi.id
            onay['yuda_acan_kisi'] = get_user_full_name(yuda_form.YudaAcanKisi.id)
        else:
            yuda_acan_kisi_id = 'Unknown'
            onay['yuda_no'] = 'Unknown'
            onay['yuda_acan_kisi'] = 'Unknown'

        firma_adi = onay.get('firma_adi', '')  
        onay['firma_adi'] = firma_adi.split()[0] if firma_adi else 'N/A'  
        
        onay['yuda_tarih'] = format_date(onay['yuda_tarih'])
        grouped_results[yuda_acan_kisi_id].append(onay)

    grouped_results = dict(grouped_results)
    for id in grouped_results:
        to_mail = User.objects.get(id=id).email
        print(to_mail)

    return results

def send_mail_for_group(to, cc, result):
    subject = f"Yuda Onay Durum Raporu"
    try:
        yudaList = result
        html_message = render_to_string('mail/yuda_onay_durum_raporu.html', {
            'yudaList': yudaList,
        })
        body = html_message # eğer result yok ise Son 48 saat içinde geçikmiş YUDA yoktur.
        send_email(to_addresses=to, cc_recipients=cc, subject= subject, body= body)
    except Exception as e:
        print(f"Error sending email: {e}")

def send_grouped_yudas_email():
    sections = {
        'kaliphane': {
            'to': ['yazilim@arslanaluminyum.com'], # ['songulyurttapan@arslanaluminyum.com', 'hacerbayram@arslanaluminyum.com', 'abdullahmeraki@arslanaluminyum.com']
            'cc': ['ufukizgi@arslanaluminyum.com'], # ['hasanpasa@arslanaluminyum.com', 'faruk@arslanaluminyum.com']
        },
        'mekanik': {
            'to': ['yazilim@arslanaluminyum.com'], # ['feridecakir@arslanaluminyum.com']
            'cc': ['ufukizgi@arslanaluminyum.com'], # []
        }
    }

    for bolum, recipients in sections.items():
        results = get_results(bolum)
        send_mail_for_group(recipients['to'], recipients['cc'], results)

def send_report_email_for_all_yudas():
    to_addresses = ['yazilim@arslanaluminyum.com', 'ufukizgi@arslanaluminyum.com']
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
    