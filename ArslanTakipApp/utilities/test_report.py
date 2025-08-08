import re
from ..models import Location, DiesLocation, KalipMs, SiparisList, MusteriFirma, Hareket
from django.contrib.auth.models import User
from django.db.models import Func, F, Q, Count, Sum, Max
from datetime import datetime, date, timedelta
from django.template.loader import render_to_string
from ..email_utils import send_email

email_mapping = {
    '1100-1': { 
        'to': ['eski1100pres@arslanaluminyum.com', 'planlama1@arslanaluminyum.com',
                'hasanhuseyinkurut@arslanaluminyum.com', 'eloksalkalite@arslanaluminyum.com'],
        'cc': ['nuraydincavdir@arslanaluminyum.com', 'pres1@arslanaluminyum.com',
                'akenanatagur@arslanaluminyum.com', 'umitgursu@arslanaluminyum.com', 'enesozturk@arslanaluminyum.com',
                'kaliphazirlama1ofis@arslanaluminyum.com', 'hasanpasa@arslanaluminyum.com', 'kevsermolla@arslanaluminyum.com', 'serdarfurtuna@arslanaluminyum.com'],
    },
    '1200-1': {
        'to': ['1200pres@arslanaluminyum.com', 'planlama1@arslanaluminyum.com',
                'hasanhuseyinkurut@arslanaluminyum.com', 'eloksalkalite@arslanaluminyum.com'],
        'cc': ['nuraydincavdir@arslanaluminyum.com', 'pres1@arslanaluminyum.com',
                'akenanatagur@arslanaluminyum.com', 'umitgursu@arslanaluminyum.com', 'enesozturk@arslanaluminyum.com',
                'kaliphazirlama1ofis@arslanaluminyum.com', 'hasanpasa@arslanaluminyum.com', 'kevsermolla@arslanaluminyum.com', 'serdarfurtuna@arslanaluminyum.com'],
    },
    '1600-1': {
        'to': ['1600PRES@arslanaluminyum.com', 'planlama1@arslanaluminyum.com',
                'hasanhuseyinkurut@arslanaluminyum.com', 'eloksalkalite@arslanaluminyum.com'],
        'cc': ['nuraydincavdir@arslanaluminyum.com', 'pres1@arslanaluminyum.com',
                'akenanatagur@arslanaluminyum.com', 'umitgursu@arslanaluminyum.com', 'enesozturk@arslanaluminyum.com',
                'kaliphazirlama1ofis@arslanaluminyum.com', 'hasanpasa@arslanaluminyum.com', 'kevsermolla@arslanaluminyum.com', 'serdarfurtuna@arslanaluminyum.com'],
    },
    '2750-1': {
        'to': ['PRES2750@arslanaluminyum.com', 'planlama2@arslanaluminyum.com', 'kalitemuhendisi@arslanaluminyum.com',
               'planlamasaha@arslanaluminyum.com', 'kalitekontrol@arslanaluminyum.com'],
        'cc': ['akenanatagur@arslanaluminyum.com', 'umitgursu@arslanaluminyum.com', 'enesozturk@arslanaluminyum.com',
               'pres2@arslanaluminyum.com', 'mkaragoz@arslanaluminyum.com', 'hasanpasa@arslanaluminyum.com', 'kevsermolla@arslanaluminyum.com', 'serdarfurtuna@arslanaluminyum.com'], 
    },
    'Yeni 1100': {
        'to': ['pres1100@arslanaluminyum.com', 'planlama2@arslanaluminyum.com', 'kalitemuhendisi@arslanaluminyum.com',
               'planlamasaha@arslanaluminyum.com', 'kalitekontrol@arslanaluminyum.com'],
        'cc': ['akenanatagur@arslanaluminyum.com', 'umitgursu@arslanaluminyum.com', 'enesozturk@arslanaluminyum.com',
               'pres2@arslanaluminyum.com', 'mkaragoz@arslanaluminyum.com', 'hasanpasa@arslanaluminyum.com', 'kevsermolla@arslanaluminyum.com', 'serdarfurtuna@arslanaluminyum.com'],
    },
    '1600-2': {
        'to': ['yeni1600pres@arslanaluminyum.com', 'planlama2@arslanaluminyum.com', 'kalitemuhendisi@arslanaluminyum.com',
               'planlamasaha@arslanaluminyum.com', 'kalitekontrol@arslanaluminyum.com'],
        'cc':['akenanatagur@arslanaluminyum.com', 'umitgursu@arslanaluminyum.com', 'enesozturk@arslanaluminyum.com',
               'pres2@arslanaluminyum.com', 'mkaragoz@arslanaluminyum.com', 'hasanpasa@arslanaluminyum.com', 'kevsermolla@arslanaluminyum.com', 'serdarfurtuna@arslanaluminyum.com'],
    },
    '4000-1': {
        'to': ['4000pres@arslanaluminyum.com', 'planlama2@arslanaluminyum.com', 'kalitemuhendisi@arslanaluminyum.com',
               'planlamasaha@arslanaluminyum.com', 'kalitekontrol@arslanaluminyum.com'],
        'cc': ['akenanatagur@arslanaluminyum.com', 'umitgursu@arslanaluminyum.com', 'enesozturk@arslanaluminyum.com',
               'pres2@arslanaluminyum.com', 'mkaragoz@arslanaluminyum.com', 'hasanpasa@arslanaluminyum.com', 'kevsermolla@arslanaluminyum.com', 'serdarfurtuna@arslanaluminyum.com'],
    },
    '4500-1': {
        'to': ['4.fabrikabakim@arslanaluminyum.com', 'fabrika4kalite@arslanaluminyum.com'],
        'cc': ['nuraydincavdir@arslanaluminyum.com', 'akenanatagur@arslanaluminyum.com', 'umitgursu@arslanaluminyum.com', 'enesozturk@arslanaluminyum.com',
                'kaliphazirlama1ofis@arslanaluminyum.com', 'hasanpasa@arslanaluminyum.com', 'kevsermolla@arslanaluminyum.com', 'serdarfurtuna@arslanaluminyum.com'],
    }
}

def send_daily_test_report_for_all():
    # her presin TEST konumunu al (locationNme'i TEST olan konumlar, hangi pres oldukları presKodu'unda yazıyor)
    # her bir konumda kalıp var mı bak varsa kalıpları getir
    # bu kalıpların profillerine ait sipariş durumlarına bak

    # her profil için sadece bir kez sipariş durumu kontrol etmek olacak. 
    # Eğer o profilin siparişlerinden en az birinde 'ACIK' durumu varsa, tüm profil için 'Sipariş Açık' mesajını ekleyeceğiz. 
    # Eğer hiç 'ACIK' sipariş yoksa ve sadece 'BLOKE' veya başka bir durumda olan siparişler varsa, o zaman 'Sipariş Bloke' veya 'Sipariş Açık Değil' ekleyeceğiz.
    
    result_list = []
    kalipList = KalipMs.objects.using('dies').annotate(trimmed_kalipno=Func(F('KalipNo'), function='REPLACE', template="%(function)s(%(expressions)s, ' ', '')"))
    test_locations = Location.objects.filter(locationName="TEST") #.exclude(presKodu='1600-2')

    for location in test_locations:
        dieList = list(DiesLocation.objects.filter(kalipVaris=location).values_list('kalipNo', flat=True))
        if len(dieList)<=0:
            continue
        # replace spaces from dieList
        clean_dieList = [kalip.replace(" ", "") for kalip in dieList]
        dies = kalipList.filter(trimmed_kalipno__in=clean_dieList)
        today = datetime.now().date() 
        for die in dies:
            kalip_no = die.KalipNo
            last_move_date = Hareket.objects.filter(kalipNo=kalip_no).latest('hareketTarihi').hareketTarihi
            move_date = last_move_date.strftime("%d-%m-%Y %H:%M")
            wait_time = (today - last_move_date.date()).days
            if (wait_time) > 3:
                print("burda")
            profil_no = die.ProfilNo
            musteri_obj = MusteriFirma.objects.using('dies').filter(FirmaKodu=die.FirmaKodu).values('MusteriTemsilcisi').first()
            musteri = musteri_obj['MusteriTemsilcisi'] if musteri_obj else "Tanımsız"
            # musteri = MusteriFirma.objects.using('dies').filter(FirmaKodu=die.FirmaKodu).values('MusteriTemsilcisi')[0]['MusteriTemsilcisi']
            siparis_qs = SiparisList.objects.using('dies').filter(Q(ProfilNo=profil_no) & Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE'))
 
            if siparis_qs.exists():
                # 'ACIK' durumu var mı diye kontrol ediyoruz
                has_open_order = siparis_qs.filter(SiparisDurum='ACIK').exists()
                
                if has_open_order:
                    result_list.append({'die': die.KalipNo, 'profile': profil_no, 'press': location.presKodu, 'order_status': 'Sipariş Açık', 'representative':musteri, 'move_date': move_date, 'wait_time': wait_time})
                else: 
                    # Eğer 'ACIK' durumu yoksa, 'BLOKE' durumuna bakıyoruz
                    has_blocked_order = siparis_qs.filter(SiparisDurum='BLOKE').exists()
                    if has_blocked_order:
                        result_list.append({'die': die.KalipNo, 'profile': profil_no, 'press': location.presKodu, 'order_status': 'Sipariş Bloke', 'representative':musteri, 'move_date': move_date, 'wait_time': wait_time})
                    else:
                        result_list.append({'die': die.KalipNo, 'profile': profil_no, 'press': location.presKodu, 'order_status': 'Sipariş Açık Değil', 'representative':musteri, 'move_date': move_date, 'wait_time': wait_time})
            else:
                # Eğer profil ile ilgili hiç sipariş yoksa
                result_list.append({'die': die.KalipNo, 'profile': profil_no, 'press': location.presKodu, 'order_status': 'Sipariş Açık Değil', 'representative':musteri, 'move_date': move_date, 'wait_time': wait_time})

    if len(result_list) >= 1:
        result_list = sorted(result_list, key=lambda x: x['press'])
        to_addresses = ['doganyilmaz@arslanaluminyum.com', 'hasanpasa@arslanaluminyum.com', 'kaliphazirlama1ofis@arslanaluminyum.com', 'mkaragoz@arslanaluminyum.com',
                         'nuraydincavdir@arslanaluminyum.com', 'pres1@arslanaluminyum.com', 'pres2@arslanaluminyum.com', 'kevsermolla@arslanaluminyum.com', 
                         'enesozturk@arslanaluminyum.com', 'akenanatagur@arslanaluminyum.com', 'burakduman@arslanaluminyum.com', 'nilgunhaydar@arslanaluminyum.com']

        cc_addresses =  ['aosman@arslanaluminyum.com', 'ersoy@arslanaluminyum.com', 'haruncan@arslanaluminyum.com', 'pinararslan@arslanaluminyum.com', 'serdarfurtuna@arslanaluminyum.com', 'ufukizgi@arslanaluminyum.com']

        # cc_addresses = ['yazilim@arslanaluminyum.com']
        # to_addresses = ['ai@arslanaluminyum.com']

        subject = f"Güncel Test Raporu - {datetime.now().strftime('%d.%m.%Y')}"
        html_message = render_to_string('mail/daily_test_report.html', {
            'result_list': result_list,
        })

        send_email(to_addresses=to_addresses, cc_recipients=cc_addresses, subject=subject, body=html_message)

# her hareketten sonra gönderilen
def send_test_report(dieList, press, user_info):
    print(f"dieList: {dieList}")
    print(f"press: {press}, user: {user_info}")
    result_list = []
    kalipList = KalipMs.objects.using('dies').annotate(trimmed_kalipno=Func(F('KalipNo'), function='REPLACE', template="%(function)s(%(expressions)s, ' ', '')"))
    clean_dieList = [kalip.replace(" ", "") for kalip in dieList]
    dies = kalipList.filter(trimmed_kalipno__in=clean_dieList)

    recipients = email_mapping[press]
    to_addresses = recipients['to']
    cc_addresses = recipients['cc']

    for die in dies:
        profil_no = die.ProfilNo
        print(f"profile: {profil_no}")
        musteri_obj = MusteriFirma.objects.using('dies').filter(FirmaKodu=die.FirmaKodu).values('MusteriTemsilcisi').first()
        temsilci_adı = musteri_obj['MusteriTemsilcisi'] if musteri_obj else "Tanımsız" # it gives the first and last name as one string
        temsilci = User.objects.get() #??

        siparis_qs = SiparisList.objects.using('dies').filter(Q(ProfilNo=profil_no) & Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE'))
        status = 'Belirsiz'
        if siparis_qs.exists():
            # 'ACIK' durumu var mı diye kontrol ediyoruz
            has_open_order = siparis_qs.filter(SiparisDurum='ACIK').exists()
            
            if has_open_order:
                status = 'Sipariş Açık'
            else: 
                # Eğer 'ACIK' durumu yoksa, 'BLOKE' durumuna bakıyoruz 
                has_blocked_order = siparis_qs.filter(SiparisDurum='BLOKE').exists()
                if has_blocked_order:
                    status = 'Sipariş Bloke'
                else:
                    status = 'Sipariş Açık Değil'
        else:
            # Eğer profil ile ilgili hiç sipariş yoksa
            status ='Sipariş Açık Değil'
        result_list.append({'die': die.KalipNo, 'profile': profil_no, 'order_status': status, 'representative':temsilci_adı})

    result_list = sorted(result_list, key=lambda x: x['representative'])
 
    subject = f"Güncel Test Raporu - {datetime.now().strftime('%d.%m.%Y')}"
    html_message = render_to_string('mail/single_die_report.html', {
        'result_list': result_list,
        'press': press
    })

    send_email(to_addresses=to_addresses, cc_recipients=cc_addresses, subject=subject, body=html_message)


def send_single_die_report(die, press, user_info):
    profile_no = die.ProfilNo
    client_obj = MusteriFirma.objects.using('dies').filter(FirmaKodu=die.FirmaKodu).values('MusteriTemsilcisi').first()
    client_rep = client_obj['MusteriTemsilcisi'] if client_obj else "Tanımsız"
    
    reps = [rep.strip() for rep in client_obj['MusteriTemsilcisi'].split(',')] # ['TUNCAY KURTULMUŞ', 'N.HAYDAR']  ya da ['FATMA DENİZ']

    recipients = email_mapping[press]
    to_addresses = set(recipients['to'])
    cc_addresses = set(recipients['cc'])

    for rep in reps:
        name_parts = rep.split()
        last_name = name_parts[-1].upper()
        if '.' in last_name:
            last_name = last_name.split(".")[-1]
        rep_user = User.objects.filter(last_name__istartswith=last_name, last_name__iendswith=last_name)
        in_group_user = rep_user.filter(Q(groups__name="Yurt Ici Satis Bolumu") | Q(groups__name="Yurt Disi Satis Bolumu"))
        if in_group_user.exists():
            rep_mail = in_group_user.values()[0]['email']
            # to_addresses.append(rep_mail)
            to_addresses.add(rep_mail)

    order_status = ''
    siparis_qs = SiparisList.objects.using('dies').filter(Q(ProfilNo=profile_no) & Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE'))

    if siparis_qs.exists():
        # 'ACIK' durumu var mı diye kontrol ediyoruz
        has_open_order = siparis_qs.filter(SiparisDurum='ACIK').exists()
        
        if has_open_order:
            order_status= 'Sipariş Açık'
        else: 
            # Eğer 'ACIK' durumu yoksa, 'BLOKE' durumuna bakıyoruz
            has_blocked_order = siparis_qs.filter(SiparisDurum='BLOKE').exists()
            if has_blocked_order:
                order_status = 'Sipariş Bloke'
            else:
                order_status = 'Sipariş Açık Değil'
    else:
        # Eğer profil ile ilgili hiç sipariş yoksa
        order_status = 'Sipariş Açık Değil'

    result_list = [{'die': die.KalipNo, 'profile': profile_no, 'order_status': order_status, 'representative':client_rep}]

    subject = f"Test alınması gereken kalıp - {datetime.now().strftime('%d.%m %H:%M')}"
    html_message = render_to_string('mail/single_die_report.html', { # artık bu template değil, kullanılacaksa yeni template gerekli.
        'user_info': user_info,
        'press': press, 
        'result_list': result_list,
    })

    send_email(to_addresses=list(to_addresses), cc_recipients=list(cc_addresses), subject=subject, body=html_message)

def send_new_dies_without_orders_report():
    # son 6 ayda kalipmsye eklenen ve o profil numarasında brüt imalatı 0 olan kalıpları getir
    date_filter = datetime.now() - timedelta(days=183)
    queryset = (
        KalipMs.objects.using('dies')
        .values('ProfilNo', 'FirmaKodu')
        .annotate(
            CountKalip=Count('KalipNo'),
            SumUretim=Sum('UretimToplamKg'),
            CreateTime=Max('Create_Time')
        )
        .filter(SumUretim=0, CreateTime__gt=date_filter)
    )
    
    # profilno_list = list(queryset.values_list('ProfilNo', flat=True))
    # profilno_no_open_order = []

    # for profilno in profilno_list:
    #     open_order_exists = SiparisList.objects.using('dies').filter(
    #         ProfilNo=profilno
    #     ).exists()  # Açılmış herhangi bir sipariş var mı kontrol et

    #     if not open_order_exists:
    #         # Yoksa listeye ekle
    #         profilno_no_open_order.append(profilno)

    profilno_no_open_order = []

    for kalip_data in queryset:
        profilno = kalip_data['ProfilNo']
        firmakodu = kalip_data['FirmaKodu']
        open_order_exists = SiparisList.objects.using('dies').filter(ProfilNo=profilno).exists()

        if not open_order_exists:
            wait_time = (datetime.now().date() - kalip_data['CreateTime'].date()).days
            musteri_obj = MusteriFirma.objects.using('dies').filter(FirmaKodu=firmakodu).values('MusteriTemsilcisi').first()
            temsilci = musteri_obj['MusteriTemsilcisi'] if musteri_obj else "Tanımsız"

            profilno_no_open_order.append({
                'profile': profilno,
                'representative': temsilci,
                'add_date': kalip_data['CreateTime'].strftime('%d.%m.%Y'),
                'wait_time': wait_time
            })
    print(profilno_no_open_order)

    if len(profilno_no_open_order) >= 1:
        profilno_no_open_order.sort(key=lambda x: (not x['profile'][0].isdigit(), re.sub(r'\D', '', x['profile'])))
        to_addresses = ['hasanpasa@arslanaluminyum.com']
        cc_addresses = ['ufukizgi@arslanaluminyum.com', 'yazilim@arslanaluminyum.com']
        # cc_addresses = ['yazilim@arslanaluminyum.com']
        # to_addresses = ['ai@arslanaluminyum.com']

        subject = f"Profil Sipariş Takip Raporu - {datetime.now().strftime('%d.%m.%Y')}"
        html_message = render_to_string('mail/profile_without_orders_report.html', {
            'result_list': profilno_no_open_order,
        })

        send_email(to_addresses=to_addresses, cc_recipients=cc_addresses, subject=subject, body=html_message)
