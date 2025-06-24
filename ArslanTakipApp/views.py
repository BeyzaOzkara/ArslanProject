from collections import Counter, OrderedDict, defaultdict
import csv
import logging
import os
import re
import ssl
import base64, binascii, zlib
import datetime
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from types import NoneType
from itertools import groupby
import time
import math
from urllib.parse import unquote
from django.apps import apps
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View, generic
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView, PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView
from django.utils import timezone
import urllib3
from .models import BilletDepoTransfer, HammaddeBilletCubuk, HammaddeBilletStok, HammaddePartiListesi, LastCheckedUretimRaporu, Location, Hareket, KalipMs, DiesLocation, PlcData, \
    PresUretimRaporu, ProfilMs, Sepet, SiparisList, EkSiparis, LivePresFeed, TestereDepo, UretimBasilanBillet, YudaOnay, Parameter, UploadFile, YudaForm, Comment, Notification, EkSiparisKalip, YudaOnayDurum, PresUretimTakip, \
    QRCode, KartDagilim, KalipMuadil, Termik, Yuda, MusteriFirma, KaliphaneIsEmri
from django.template import loader
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator
from guardian.shortcuts import get_objects_for_user, get_objects_for_group, assign_perm, get_groups_with_perms
from guardian.models import UserObjectPermission, GroupObjectPermission
from django.db.models import CharField, Q, Sum, Avg, Max, Min, ExpressionWrapper, Count, Case, When, OuterRef, Subquery, FloatField, F, Value
from django.db.models.functions import Cast, Replace, Coalesce
from django.db import transaction, IntegrityError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
# from aes_cipher import *
# from Crypto.Cipher import AES
# from Crypto.Util.Padding import pad, unpad
import locale
from .forms import PasswordChangingForm, PasswordResettingForm
from .dxfsvg import dxf_file_area_calculation
from django.core.exceptions import PermissionDenied
from django.utils.dateformat import DateFormat
from django.db.models.functions import ExtractHour, ExtractMinute
from .email_utils import send_email
from django.core.cache import cache
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.forms.models import model_to_dict
from .reports import send_report_email_for_all
from DMS.models import EventData, TemporalData
from .utilities.test_report import send_daily_test_report_for_all, send_single_die_report
from django.db.models import Func
# Create your views here.


locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')
logger = logging.getLogger(__name__)

class IndexView(generic.TemplateView):
    template_name = 'ArslanTakipApp/index.html'

class RegisterView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/register.html"

class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = 'registration/password_reset.html'
    form_class = PasswordResettingForm
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_message ="Girilen E-posta adresi ile bir hesap mevcutsa, " \
                "şifrenizi ayarlamak için size talimatlar gönderdik. Kısa bir süre içinde almış olmanız gerekiyor." \
                "Eğer bir e-posta almadıysanız, lütfen kayıt olduğunuz adresi doğru girdiğinizden emin olun ve spam klasörünüzü kontrol edin."
    success_url = reverse_lazy('ArslanTakipApp:index')

def login_success(request):
    user_g = request.user.groups.all()
    if user_g.filter(name__contains = " Bolumu").exists():
        return redirect("/yudas")
    elif user_g.filter(name__contains = ' Operatoru').exists():
        return redirect("/location")
    else:
        return redirect("/")

class PasswordChangeView(PasswordChangeView):
    form_class = PasswordChangingForm
    success_url = reverse_lazy('ArslanTakipApp:password_success')

def password_success(request):
    return render(request, 'registration/password_change_done.html')

def calculate_pagination(page, size):
    offset = (page - 1) * size
    limit = page * size
    return (offset, limit)

def get_user_full_name(user_id):
    user = User.objects.get(id=user_id)
    return f"{user.first_name} {user.last_name}"

def format_date_time_without_year(date):
    return date.strftime("%d-%m %H:%M")

def format_date_time_s(date):
    return date.strftime("%d-%m-%Y %H:%M:%S")

def format_date_time(date):
    return date.strftime("%d-%m-%Y %H:%M")

def format_date(date):
    return date.strftime("%d-%m-%Y")

def hareketSave(dieList, lRec, dieTo, request):
    for i in dieList:
        k = DiesLocation.objects.get(kalipNo = i)
        if k.kalipVaris.id != 1134: #HURDA
            if k.kalipVaris.id != lRec.id:
                hareket = Hareket()
                hareket.kalipKonum_id = k.kalipVaris.id
                hareket.kalipVaris_id = dieTo
                hareket.kalipNo = i
                hareket.kimTarafindan_id = request.user.id
                hareket.save()
                print("Hareket saved")
            else:
                print("Hareket not saved")


def get_new_unique_dies():
    # son 6 ayda kalipmsye eklenen ve o profil numarasında brüt imalatı 0 olan kalıpları getir
    date_filter = datetime.datetime.now() - datetime.timedelta(days=183)
    queryset = (
        KalipMs.objects.using('dies')
        .values('ProfilNo')
        .annotate(
            CountKalip=Count('KalipNo'),
            SumUretim=Sum('UretimToplamKg'),
            CreateTime=Max('Create_Time')
        )
        .filter(SumUretim=0, CreateTime__gt=date_filter)
    )
    
    profilno_list = list(queryset.values_list('ProfilNo', flat=True))
    profilno_no_open_order = []

    for profilno in profilno_list:
        open_order_exists = SiparisList.objects.using('dies').filter(
            ProfilNo=profilno
        ).exists()  # Açılmış herhangi bir sipariş var mı kontrol et

        if not open_order_exists:
            # Yoksa listeye ekle
            profilno_no_open_order.append(profilno)

    print(profilno_no_open_order)


@permission_required("ArslanTakipApp.view_location") #izin yoksa login sayfasına yönlendiriyor
@login_required #user must be logged in
def location(request):
    profiles = get_new_unique_dies()


    loc = get_objects_for_user(request.user, "ArslanTakipApp.dg_view_location", klass=Location) #Location.objects.all()
    loc_list = list(loc.values().order_by('id'))
    # Create a dictionary for O(1) lookups
    loc_dict = {item['id']: item for item in loc_list}
    root_nodes = []

    for item in loc_list:
        parent_id = item['locationRelationID_id']
        if parent_id:
            parent = loc_dict.get(parent_id)
            if parent:
                parent.setdefault('_children', []).append(item)
        else:
            root_nodes.append(item)
    data = json.dumps(root_nodes)
    gonderData = location_list(request.user)
    if request.method == "POST":
        try:
            dieList = request.POST.get("dieList")
            dieList = dieList.split(",")
            dieTo = request.POST.get("dieTo")
            lRec = Location.objects.get(id = dieTo)
            gozCapacity = Location.objects.get(id = lRec.id).capacity

            notPhysical = ["542", "543", "544", "545", "570", "571", "572", "573", "574", "575", "1079"]
            if dieTo in notPhysical:
                dieTo = Location.objects.get(locationRelationID = dieTo, locationName__contains = "MEYDAN").id
                
            if gozCapacity == None:
                checkList = list(Location.objects.exclude(presKodu=None).values_list('id', flat=True))
                if int(dieTo) in checkList and request.user.id != 1 and lRec.locationName != "TEST":
                    check_last_location_press(request, dieList, dieTo)
                hareketSave(dieList, lRec, dieTo, request)
                # 1.fabrikaya kalıp gönderiliyorsa
            else:
                firinKalipSayisi = DiesLocation.objects.filter(kalipVaris_id = lRec.id).count()
                if firinKalipSayisi < gozCapacity:
                    if not (firinKalipSayisi + len(dieList)) > gozCapacity:
                        hareketSave(dieList, lRec, dieTo, request)
            if lRec.locationName == "TEST":
                user_info = get_user_full_name(request.user.id)
                kalipList = KalipMs.objects.using('dies').annotate(trimmed_kalipno=Func(F('KalipNo'), function='REPLACE', template="%(function)s(%(expressions)s, ' ', '')"))
                clean_dieList = [kalip.replace(" ", "") for kalip in dieList]
                dies = kalipList.filter(trimmed_kalipno__in=clean_dieList)
                for die in dies:
                    send_single_die_report(die, lRec.presKodu, user_info)
            response = JsonResponse({'message': "Kalıplar Başarıyla Gönderildi."})
        except Exception as e:
            response = JsonResponse({'error':  'İşlem gerçekleştirilemedi. ' + str(e)})
        
        return response
    return render(request, 'ArslanTakipApp/location.html', {'location_json':data, 'gonder_json':gonderData})

def check_last_location_press(request, dieList, dieTo):
    dieTo_press = Location.objects.get(id=dieTo).presKodu
    dies = DiesLocation.objects.filter(kalipNo__in=dieList).select_related('kalipVaris')
    dies_to_notify = []

    for die in dies:
        die_press = die.kalipVaris.presKodu
        if die_press != dieTo_press and die_press != None and dieTo_press!= None:
            dies_to_notify.append(die.kalipNo)
    
    if dies_to_notify:
        send_email_notification(request, dies_to_notify, dieTo_press)
    else:
        print("don't send mail")

def send_email_notification(request, dieList, dieTo_press):
    try:
        user_info = get_user_full_name(request.user.id)
        cc_addresses = ['pres2@arslanaluminyum.com', 'pres1@arslanaluminyum.com', 'kaliphazirlama@arslanaluminyum.com' ,
            'kaliphazirlama1@arslanaluminyum.com','mkaragoz@arslanaluminyum.com' ,'kevsermolla@arslanaluminyum.com',
            'nuraydincavdir@arslanaluminyum.com' ,'planlamaofis2@arslanaluminyum.com', 
            'doganyilmaz@arslanaluminyum.com' ,'planlama2@arslanaluminyum.com', 'akenanatagur@arslanaluminyum.com', 
            'ufukizgi@arslanaluminyum.com', 'ersoy@arslanaluminyum.com'] 
        
        email_mapping = {
            '1100-1': 'eski1100pres@arslanaluminyum.com',
            '1200-1': '1200pres@arslanaluminyum.com',
            '1600-1': '1600PRES@arslanaluminyum.com',
            '2750-1': 'PRES2750@arslanaluminyum.com',
            'Yeni 1100': 'pres1100@arslanaluminyum.com',
            '1600-2': 'yeni1600pres@arslanaluminyum.com',
            '4000-1': '4000pres@arslanaluminyum.com',
            '4500-1': '4.fabrikabakim@arslanaluminyum.com',
            '1. Fabrika Kalıp Hazırlama': 'kaliphazirlama1ofis@arslanaluminyum.com',
            '1. Fabrika Kalıp Arşivi': 'kaliphazirlama1ofis@arslanaluminyum.com',
            '2. Fabrika Kalıp Hazırlama': 'kaliphazirlama@arslanaluminyum.com',
            '2. Fabrika Kalıp Arşivi': 'kaliparsivi@arslanaluminyum.com'
        }
        
        to_addresses = [request.user.email, 'hasanpasa@arslanaluminyum.com']
        if dieTo_press in email_mapping:
            to_addresses.append(email_mapping[dieTo_press])

        subject = f"Kalıp Transferi"
        html_message = render_to_string('mail/die_move.html', {
            'dieList': dieList,
            'dieTo_press': dieTo_press,
            'user_info': user_info
        })
        body = html_message

        # Send email
        send_email(to_addresses=to_addresses, cc_recipients=cc_addresses, subject= subject, body= body)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")
    
def location_list(a):
    gonderLoc = get_objects_for_user(a, "ArslanTakipApp.gonder_view_location", klass=Location)
    gonderLoc_list = list(gonderLoc.values().order_by('id'))

    gonder_dict = {item['id']: item for item in gonderLoc_list}
    root_nodes = []

    for item in gonderLoc_list:
        parent_id = item['locationRelationID_id']
        if parent_id:
            parent = gonder_dict.get(parent_id)
            if parent:
                parent.setdefault('_children', []).append(item)
        else:
            root_nodes.append(item)

    childData = root_nodes
    data = json.dumps(childData)
    return data

def filter_locations(locations, target_id, depth=1):
    filtered_ids = []
    for location in locations:
        if location['locationRelationID_id'] == int(target_id):
            if location['isPhysical']:
                filtered_ids.append(location['id'])
            elif depth > 0:
                child_ids = filter_locations(locations, location['id'], depth - 1)
                filtered_ids.extend(child_ids)
    return filtered_ids

def location_kalip(request): #kalıp arşivi sayfasındaki kalıplar
    if request.method == "GET":
        params = json.loads(unquote(request.GET.get('params')))
        size = params["size"]
        page = params["page"]
        filter_list = params["filter"]
        q = {}

        loc = get_objects_for_user(request.user, "ArslanTakipApp.dg_view_location", klass=Location)
        loc_list = list(loc.values())
        locs = [l['id'] for l in loc_list]
        query = DiesLocation.objects.filter(kalipVaris_id__in = locs).order_by('kalipNo')

        if request.user.is_superuser:
            query = DiesLocation.objects.all().order_by('kalipNo')

        if len(filter_list)>0:
            for i in filter_list: # bir lokasyona tıklandığında o lokasyon ve altında kalan her lokasyon içindeki kalıp sayısı dönsün
                if i["type"] == "like": # eğer birden fazla yazılırsa startswith yerine = kullanılacak bulamadığı kalıplara ise 20 karakter olana kadar boşluk ekleyip deneyecek
                    if not "," in i['value']:
                        q[i['field']+"__startswith"] = i['value']
                    else:
                        value_list = i['value'].split(",")
                        matched_items = []
                        for item in value_list:
                            item = item.strip()
                            matched = query.filter(kalipNo=item)
                            if not matched.exists():
                                item = item.ljust(20)
                                matched = query.filter(kalipNo=item)
                            matched_items.extend(matched.values_list('kalipNo', flat=True))
                        q['kalipNo__in'] = matched_items
                elif i["type"] == "=":
                    loca = loc.values().get(id = i['value'])
                    if loca['isPhysical']: 
                        q[i['field']] = i['value']
                    else :
                        filtered_ids = filter_locations(loc.values(), target_id=i['value'], depth=4)
                        q['kalipVaris_id__in'] =filtered_ids

        query = query.filter(**q)
        sayi = query.count()
        kal = KalipMs.objects.using('dies').all()
        a = list(query.values()[(page-1)*size:page*size])
        for b in a:
            if len(kal.filter(KalipNo=b['kalipNo'])) > 0:
                s = kal.get(KalipNo=b['kalipNo'])
                if s.Silindi == 1 or s.AktifPasif == 'Pasif':
                    a.remove(b)
                c = kal.get(KalipNo=b['kalipNo']).Hatali
                if c==1:
                    b['Hatali'] = 1
            else:
                a.remove(b)

        kalip_count = query.count()
        lastData= {'last_page': math.ceil(kalip_count/size), 'data': [], 'sayi': sayi}
        lastData['data'] = a
        data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
        return HttpResponse(data)

def kalip_liste(request):
    #Kalıp Listesi Detaylı
    params = json.loads(unquote(request.GET.get('params')))
    for i in params:
        value = params[i]
        #print("Key and Value pair are ({}) = ({})".format(i, value))
    size = params["size"]
    page = params["page"]
    offset, limit = calculate_pagination(page, size)
    filter_list = params["filter"]
    query = KalipMs.objects.using('dies').all()
    location_list = Location.objects.values()
    q = {} 
    
    if len(filter_list)>0:
        for i in filter_list:
            if i['field'] != 'ProfilNo':
                if i["type"] == "like":
                    q[i['field']+"__startswith"] = i['value']
                elif i["type"] == "=":
                    if i['field'] == 'AktifPasif':
                        if i['value'] == True:
                            i['value'] = 'Aktif'
                        else: i['value'] = 'Pasif'
                    q[i['field']] = i['value']
            else:
                q[i['field']] = i['value']
    
    query = query.filter(**q).order_by('-UretimTarihi') 

    g = list(query.values()[offset:limit])
    for c in g:
        if c['UretimTarihi'] != None:
            c['UretimTarihi'] = format_date(c['UretimTarihi'])
            c['SonTeniferTarih'] = format_date_time_s(c['SonTeniferTarih'])
            c['SonUretimTarih'] = format_date(c['SonUretimTarih'])
        if c['AktifPasif'] == "Aktif":
            c['AktifPasif'] = True
        elif c['AktifPasif'] == "Pasif":
            c['AktifPasif'] = False
        if c['Hatali'] == 1:
            c['Hatali'] = 0
        elif c['Hatali'] == 0:
            c['Hatali'] = 1

        try: 
            b = DiesLocation.objects.get(kalipNo = c['KalipNo']).kalipVaris_id
        except:
            b = 48

        try:
            c['kalipLocation'] = list(location_list.filter(id=list(location_list.filter(id=b))[0]["locationRelationID_id"]))[0]["locationName"] + " <BR>└ " + list(location_list.filter(id=b))[0]["locationName"]
        except:
            try:
                c['kalipLocation'] = list(location_list.filter(id=b))[0]["locationName"]
            except:
                c['kalipLocation'] = ""
        #print(c)
    kalip_count = query.count()
    lastData= {'last_page': math.ceil(kalip_count/size), 'data': []}
    lastData['data'] = g
    data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

def kalip_rapor(request):
    params = json.loads(unquote(request.GET.get('params')))
    size = params["size"]
    page = params["page"]
    offset, limit = calculate_pagination(page, size)
    filter_list = params["filter"]
    q = {} 
    kalip_count = 0
    lastData= {'last_page': math.ceil(kalip_count/size), 'data': []}

    if len(filter_list)>0:
        for i in filter_list:
            if i["type"] == "like":
                q[i['field']+"__startswith"] = i['value']
            elif i["type"] == "=":
                q[i['field']] = i['value']
    
        query = PresUretimRaporu.objects.using('dies').filter(**q) \
        .values('PresKodu', 'Tarih', 'BaslamaSaati', 'BitisSaati', 'HataAciklama', 'Durum').order_by('-Tarih')

        g = list(query[offset:limit])
        for c in g:
            if c['Tarih'] != None:
                c['Tarih'] = format_date(c['Tarih']) + " <BR>└ " + c['BaslamaSaati'].strftime("%H:%M") + " - " + c['BitisSaati'].strftime("%H:%M")
                c['BaslamaSaati'] =c['BaslamaSaati'].strftime("%H:%M")
                c['BitisSaati'] =c['BitisSaati'].strftime("%H:%M")
        kalip_count = query.count()
        lastData= {'last_page': math.ceil(kalip_count/size), 'data': []}
        lastData['data'] = g

    data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

def view_comment(request, cId):
    comment = Comment.objects.get(id=cId)
    user = request.user  # Assuming user is authenticated

    if user:  # Check if user is authenticated
        comment.mark_viewed(user)
        comment.save()

        return JsonResponse({'message': 'Comment viewed successfully.'})
    else:
        return JsonResponse({'error': 'User not authenticated.'}, status=401)

def get_viewed_users(request, cId):
    if request.method == 'GET':
        comment_instance = Comment.objects.get(pk=cId)
        views = comment_instance.ViewedUsers.all()
        users_data = [{'id': user.id, 'name': user.get_full_name()} for user in views]

        # Return the data as JSON
        return JsonResponse(users_data, safe=False)  # safe=False is needed to allow non-dict objects
    else:
        # If the request is not a GET, return a bad request response
        return HttpResponseBadRequest("Invalid request method.")

#gelen id başka konumların parenti ise altındakileri listele??
def location_hareket1(request):
    params = json.loads(unquote(request.GET.get('params')))
    size = params["size"]
    page = params["page"]
    filter_list = params["filter"]

    hareket_count = 0
    lastData= {'last_page': math.ceil(hareket_count/size), 'data': []}

    if len(filter_list)>0:
        for i in filter_list:
            if i['type'] == '=':
                hareketK = i['value']
                hareketQuery = Hareket.objects.all()
                location_list = Location.objects.values()
                hareketQuery = list(hareketQuery.values().filter(kalipNo=hareketK).order_by("-hareketTarihi"))
                kalip_l = list(DiesLocation.objects.filter(kalipNo=hareketK).values())
                harAr = []
                for h in hareketQuery:
                    har ={}
                    har['id'] = h['id']
                    har['kalipNo'] = kalip_l[0]['kalipNo']
                    try:
                        har['kalipKonum'] =list(location_list.filter(id=list(location_list.filter(id=h['kalipKonum_id']))[0]["locationRelationID_id"]))[0]["locationName"] + " <BR>└ " + list(location_list.filter(id=h['kalipKonum_id']))[0]["locationName"]
                    except:
                        try:
                            har['kalipKonum'] = list(location_list.filter(id=h['kalipKonum_id']))[0]["locationName"]
                        except:
                            har['kalipKonum'] = ""
                    try:
                        har['kalipVaris'] =list(location_list.filter(id=list(location_list.filter(id=h['kalipVaris_id']))[0]["locationRelationID_id"]))[0]["locationName"] + " <BR>└ " + list(location_list.filter(id=h['kalipVaris_id']))[0]["locationName"]
                    except:
                        har['kalipVaris'] = list(location_list.filter(id=h['kalipVaris_id']))[0]["locationName"]
                    har['kimTarafindan'] = get_user_full_name(int(h['kimTarafindan_id']))
                    har['hareketTarihi'] = format_date_time_s(h['hareketTarihi'])
                    harAr.append(har)
                hareket_count = len(harAr)
            elif i['type'] == 'like': # konuma tıklandığındaki setfilter 
                # tıklanan konum idsini alıp o konumdaki ve o konuma bağlı diğer konumlardaki bütün kalıp hareketlerini getir
                konumId = i['value']


        lastData= {'last_page': math.ceil(hareket_count/size), 'data': []}
        lastData['data'] = list(harAr[(page-1)*size:page*size])
                
    #print(lastData)
    data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

def location_hareket(request):
    params = json.loads(unquote(request.GET.get('params', '{}')))
    size = params.get("size", 30)
    page = params.get("page", 1)
    filter_list = params.get("filter", [])

    hareket_count = 0
    lastData= {'last_page': math.ceil(hareket_count/size), 'data': []}
    harAr = []

    if filter_list:
        for i in filter_list:
            if i['type'] == '=':
                hareketK = i['value']
                hareket_query = Hareket.objects.filter(kalipNo=hareketK).select_related('kalipKonum', 'kalipVaris', 'kimTarafindan').order_by("-hareketTarihi")

            elif i['type'] == 'like':
                konumId = i['value']
                locations = list(get_objects_for_user(request.user, "ArslanTakipApp.gonder_view_location", klass=Location).values().order_by('id'))
                child_location_ids = filter_locations(locations, konumId, depth=4) # Adjust depth if needed
                hareket_query = Hareket.objects.filter(
                    kalipKonum_id__in=child_location_ids
                ).select_related('kalipKonum', 'kalipVaris', 'kimTarafindan').order_by("-hareketTarihi")

            hareket_count = hareket_query.count()
            hareket_query = hareket_query[(page-1)*size:page*size]
            for h in hareket_query:
                kalipKonumName = ""
                kalipVarisName = ""
                
                if h.kalipKonum:
                    kalipKonumName = f"{h.kalipKonum.locationRelationID.locationName} <BR>└ {h.kalipKonum.locationName}" if h.kalipKonum.locationRelationID else h.kalipKonum.locationName

                if h.kalipVaris:
                    kalipVarisName = f"{h.kalipVaris.locationRelationID.locationName} <BR>└ {h.kalipVaris.locationName}" if h.kalipVaris.locationRelationID else h.kalipVaris.locationName

                har = {
                    'id': h.id,
                    'kalipNo': h.kalipNo,
                    'kalipKonum': kalipKonumName,
                    'kalipVaris': kalipVarisName,
                    'kimTarafindan': get_user_full_name(h.kimTarafindan_id),
                    'hareketTarihi': format_date_time_s(h.hareketTarihi),
                }
                harAr.append(har)
    
    paginated_data = harAr
    lastData = {
        'last_page': math.ceil(hareket_count/size),
        'data': paginated_data
    }

    return JsonResponse(lastData)

def kalip(request):
    return render(request, 'ArslanTakipApp/kalip.html')

class KalipView(generic.TemplateView):
    template_name = 'ArslanTakipApp/kalip.html'

class DenemeView(generic.TemplateView):
    template_name = 'ArslanTakipApp/deneme.html'

def comment_kalip(request, kNo):
    kalipList = list(KalipMs.objects.using('dies').filter(KalipNo = kNo).values())
    for i in kalipList:
        i['ResimDizini'] = "http://arslan/static" + i['ResimDizini'].replace(" ", "")[13:] + "Teknik"
        i['ResimDizini1'] = i['ResimDizini'] + "1.jpg"
        i['ResimDizini2'] = i['ResimDizini'] + "2.jpg"
        if i['UreticiFirma'] == None:
            i['UreticiFirma'] = ""
        i['UretimTarihi'] = format_date_time(i['UretimTarihi'])
        i['SonUretimTarih'] = format_date_time(i['SonUretimTarih'])
        i['SonTeniferTarih'] = format_date_time(i['SonTeniferTarih'])
    return render(request, 'ArslanTakipApp/kalipYorum.html', {'kalip_json':kalipList})

def kalip_tum(request):
    #şimdilik bütün kalıp sayısını döndür
    #asıl istenen filter yapıldığında kaç tane kalıp var o sayı döndürülecek
    kalipSayisi = KalipMs.objects.using('dies').count()
    data = json.dumps(kalipSayisi, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

def kalip_getcomments(request, kId):
    if request.method == "GET":
        yudaComments = getParentComments("KalipMs", kId).order_by("Tarih")
        yudaCList = [process_comment(request.user, comment) for comment in yudaComments]
        comments = json.dumps(yudaCList, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
        data = json.dumps(comments, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
        return HttpResponse(data)

def kalip_comments_post(request):
    if request.method == "POST":
        try:
            req = request.POST
            c = Comment()
            c.Kullanici = request.user
            c.FormModel = "KalipMs"
            c.FormModelId = req['formID']
            c.Tarih = datetime.datetime.now()
            if 'replyID' in req:
                replyID = req['replyID']
                c.ReplyTo = Comment.objects.get(id=replyID)
                c.FormModelId = c.ReplyTo.FormModelId
            c.Aciklama = req['yorum']
            c.save()

            for file in request.FILES.getlist('yfiles'):
                UploadFile.objects.create(
                    File = file,
                    FileModel = "Comment",
                    FileModelId = c.id,
                    FileSize = file.size,
                    UploadedBy = c.Kullanici,
                    Note = "",
                )
            
            yudaComments = getParentComments("KalipMs", c.FormModelId).order_by("Tarih")
            yudaCList = [process_comment(request.user, comment) for comment in yudaComments]
            comments = json.dumps(yudaCList, sort_keys=True, indent=1, cls=DjangoJSONEncoder)

            response = JsonResponse({'message': 'Kayıt başarılı', 'data':comments})
        except Exception as e:
            response = JsonResponse({'error': str(e)})
            response.status_code = 500 #server error
        return response

def kalip_comments_edit(request):
    if request.method == 'POST':
        req = request.POST
        try:
            c = Comment.objects.get(id=req["commentId"])
            c.Aciklama = req["commentText"]
            c.save()
            #dosyalar için olan bölüm de eklenecek
            yudaComments = getParentComments("KalipMs", c.FormModelId).order_by("Tarih")
            yudaCList = [process_comment(request.user, comment) for comment in yudaComments]
            comments = json.dumps(yudaCList, sort_keys=True, indent=1, cls=DjangoJSONEncoder)

            response = JsonResponse({'message': 'Düzenleme başarılı', 'data':comments})
        except Exception as e:
            response = JsonResponse({'error': str(e)})
            response.status_code = 500 #server error
        return response

def kalip_comments_delete(request, cId):
    try:
        comment = Comment.objects.get(id = cId)
        comment.Silindi = True
        comment.save()
        response = JsonResponse({'message': 'Yorum başarıyla silindi.'})
    except Exception as e:
        response = JsonResponse({'error': str(e)})
        response.status_code = 500 #server error
    return response

def kalip_get_info(request, kalip_no):
    try:
        kalip = KalipMs.objects.using('dies').get(KalipNo=kalip_no)
        kalip_data = {
            'KalipNo': kalip.KalipNo,
            'FirmaAdi': kalip.FirmaAdi,
            'Cinsi': kalip.Cinsi,
            'Miktar': kalip.Miktar,
            'Capi': kalip.Capi,
            'UretimTarihi': format_date(kalip.UretimTarihi) if kalip.UretimTarihi else None,  # Convert DateTime to string
            'GozAdedi': kalip.GozAdedi,
            'Silindi': kalip.Silindi,
            'SilinmeSebebi': kalip.SilinmeSebebi,
            'Bolster': kalip.Bolster,
            'KalipCevresi': kalip.KalipCevresi,
            'KaliteOkey': kalip.KaliteOkey,
            'UreticiFirma': kalip.UreticiFirma,
            'TeniferOmruMt': kalip.TeniferOmruMt,
            'TeniferOmruKg': kalip.TeniferOmruKg,
            'TeniferKalanOmurKg': kalip.TeniferKalanOmurKg,
            'TeniferNo': kalip.TeniferNo,
            'SonTeniferTarih': format_date(kalip.SonTeniferTarih) if kalip.SonTeniferTarih else None,
            'SonTeniferKg': kalip.SonTeniferKg,
            'SonUretimTarih': format_date(kalip.SonUretimTarih) if kalip.SonUretimTarih else None,
            'SonUretimGr': kalip.SonUretimGr,
            'UretimTenSonrasiKg': kalip.UretimTenSonrasiKg,
            'UretimToplamKg': kalip.UretimToplamKg,
            'ProfilGramaj': kalip.ProfilGramaj,
            'KalipAciklama': kalip.KalipAciklama,
            'SikayetVar': kalip.SikayetVar,
            'KaliteAciklama': kalip.KaliteAciklama,
            'AktifPasif': kalip.AktifPasif,
            'Hatali': kalip.Hatali,
            'ResimDizini': kalip.ResimDizini,
            'PaketBoyu': kalip.PaketBoyu,
        }

        return JsonResponse(kalip_data)
    except KalipMs.DoesNotExist:
        return JsonResponse({"error": "Kalip not found"}, status=404)
    
def kalip_get_tab(request, kalip_no, tab):
    try:
        if tab == 'uretimraporu':
            # send kalip_no to kalip_rapor
            print("rapor")
        elif tab == 'hareketler':
            print("hareket")
        elif tab == 'yorumlar':
            print("yorum")
        elif tab == 'grafikler':
            print("grafik")
    except KalipMs.DoesNotExist:
        return JsonResponse({"error": "Kalip not found"}, status=404)

def kalip_rapor2(request):
    kalip_no = request.GET.get('KalipNo')
    print(kalip_no)
    params = json.loads(unquote(request.GET.get('params')))
    size = params["size"]
    page = params["page"]
    offset, limit = calculate_pagination(page, size)
    filter_list = params["filter"]
    q = {} 
    kalip_count = 0
    lastData= {'last_page': math.ceil(kalip_count/size), 'data': []}

    if len(filter_list)>0:
        for i in filter_list:
            if i["type"] == "like":
                q[i['field']+"__startswith"] = i['value']
            elif i["type"] == "=":
                q[i['field']] = i['value']
    
    query = PresUretimRaporu.objects.using('dies').filter(KalipNo = kalip_no, **q) \
    .values('PresKodu', 'Tarih', 'BaslamaSaati', 'BitisSaati', 'HataAciklama', 'Durum').order_by('-Tarih')

    g = list(query[offset:limit])
    for c in g:
        if c['Tarih'] != None:
            c['Tarih'] = format_date(c['Tarih']) + " <BR>└ " + c['BaslamaSaati'].strftime("%H:%M") + " - " + c['BitisSaati'].strftime("%H:%M")
            c['BaslamaSaati'] =c['BaslamaSaati'].strftime("%H:%M")
            c['BitisSaati'] =c['BitisSaati'].strftime("%H:%M")
    kalip_count = query.count()
    lastData= {'last_page': math.ceil(kalip_count/size), 'data': []}
    lastData['data'] = g

    data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

def kalip_hareket(request):
    kalip_no = request.GET.get('KalipNo')
    print(kalip_no)
    params = json.loads(unquote(request.GET.get('params', '{}')))
    size = params.get("size", 30)
    page = params.get("page", 1)
    filter_list = params.get("filter", [])

    q = {}
    hareket_count = 0
    lastData= {'last_page': math.ceil(hareket_count/size), 'data': []}
    harAr = []

    if filter_list: # filter list boş gönderiyorum burayı düzelt
        for i in filter_list:
            if i['type'] == 'like':
                konumId = i['value']
                locations = list(get_objects_for_user(request.user, "ArslanTakipApp.gonder_view_location", klass=Location).values().order_by('id'))
                child_location_ids = filter_locations(locations, konumId, depth=4) # Adjust depth if needed
                q["kalipKonum_id__in"] = child_location_ids

    hareket_query = Hareket.objects.filter(kalipNo=kalip_no, **q).select_related('kalipKonum', 'kalipVaris', 'kimTarafindan').order_by("-hareketTarihi")
    hareket_count = hareket_query.count()
    hareket_query = hareket_query[(page-1)*size:page*size]
    for h in hareket_query:
        kalipKonumName = ""
        kalipVarisName = ""
        
        if h.kalipKonum:
            kalipKonumName = f"{h.kalipKonum.locationRelationID.locationName} <BR>└ {h.kalipKonum.locationName}" if h.kalipKonum.locationRelationID else h.kalipKonum.locationName

        if h.kalipVaris:
            kalipVarisName = f"{h.kalipVaris.locationRelationID.locationName} <BR>└ {h.kalipVaris.locationName}" if h.kalipVaris.locationRelationID else h.kalipVaris.locationName

        har = {
            'id': h.id,
            'kalipNo': h.kalipNo,
            'kalipKonum': kalipKonumName,
            'kalipVaris': kalipVarisName,
            'kimTarafindan': get_user_full_name(h.kimTarafindan_id),
            'hareketTarihi': format_date_time_s(h.hareketTarihi),
        }
        harAr.append(har)
    
    paginated_data = harAr
    lastData = {
        'last_page': math.ceil(hareket_count/size),
        'data': paginated_data
    }

    return JsonResponse(lastData)

def kalip_yorum(request):
    kalip_no = request.GET.get('kalipNo')
    if request.method == "GET":
        comments = getParentComments("KalipMs", kalip_no).order_by("-Tarih")
        comment_list = [process_comment(request.user, comment) for comment in comments]
        data = json.dumps(comment_list, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
        return HttpResponse(data)

def build_comment_tree(comments):
    comment_dict = {comment.id: comment for comment in comments}
    tree = []

    for comment in comments:
        comment_data = model_to_dict(comment)  # Convert to dictionary

        # Add the user full name (assuming `get_user_full_name` is a valid function)
        comment_data['KullaniciAdi'] = get_user_full_name(comment.Kullanici.id)
        comment_data['All_Viewed'] = False
        
        comment_data['Tarih'] = format_date_time(comment_data['Tarih'])
        comment_data['Is_Viewed'] = False
        comment_data['cfiles'] = list(getFiles("Comment", comment_data['id']))
        # Handling if comment is deleted
        if comment.Silindi:
            comment_data['Aciklama'] = "Yorum silindi."
            tree.append({'comment': comment_data, 'replies': []})
        else:
            if comment.ReplyTo is None:  # Top-level comment
                tree.append({'comment': comment_data, 'replies': []})
            else:  # This is a reply
                parent = comment_dict.get(comment.ReplyTo.id)
                if parent:
                    for node in tree:
                        if node['comment']['id'] == parent.id:
                            com_dict = {'comment': comment_data}
                            node['replies'].append(com_dict)
                            break

    return tree

def qrcodeRedirect(request, id):
    if request.method == "GET":
        # qr kodundan gelen id'yi getir (qr/id)
        qr_code = QRCode.objects.get(id=id)
        print(f"name: {qr_code.name}")
        print(f"detail: {qr_code.detail}")
        if qr_code.detail == 'kalıp':
            # kalıp sayfasına yönlendir, kalıp/#qr_code.name
            url = f'/kalip/#{qr_code.name}'
        else:
            print("kalıp olmayan durumları sonra yaz")

    return redirect(url)

key = b'arslandenemebyz1'
# def encrypt_aes_ecb(key, plaintext):
#     cipher = AES.new(key, AES.MODE_ECB)
#     padded_plaintext = pad(plaintext.encode('utf8'), AES.block_size)
#     ciphertext = cipher.encrypt(padded_plaintext)
#     return ciphertext
# #sepet numarası S250 olacak şekilde
# def decrypt_aes_ecb(key, ciphertext):
#     cipher = AES.new(key, AES.MODE_ECB)
#     decrypted_data = cipher.decrypt(ciphertext)
#     unpadded_data = unpad(decrypted_data, AES.block_size)
#     return unpadded_data.decode('utf-8')
        #1 ve 9 arasındaysa başına 2 sıfır 10 ve 99 arasındaysa 1 sıfır
        # Şifre çözme
    #     unhexli = binascii.unhexlify('819a7b20eed64469c8adaa3ccf01ad06')
    #     #print(unhexli)
    #     decrypted_text = decrypt_aes_ecb(key, unhexli)
    #     #print("Çözülmüş Veri:", decrypted_text)   

    #     ty = request.GET.get('type', '')
    #     no = request.GET.get('no', '')
        
    #     context = {
    #         "type" : unhexli,
    #         "no" : decrypted_text,
    #     }

    # return render(request, 'ArslanTakipApp/qrKalite.html', context)

    
def qrKalite(request):
    if request.method == "GET":

        context = {
            "no": "denemee"
        }
    
    return render(request, 'ArslanTakipApp/qrKalite.html', context)

def qrKalite_deneme(request):
    try: 
        response = JsonResponse({'message': "gitti"})
    except Exception as e:
        response = JsonResponse({'error': str(e)})
        response.status_code = 500 #server error

    return response

def notif(request, id):
    n = Notification.objects.get(id = id)
    s = n.subject
    if s == "Yeni YUDA" or s == "Yeni YUDA Yorum":
        return HttpResponseRedirect(f"/yudaDetail/{n.where_id}")

class qrKaliteView(generic.TemplateView):
    template_name = 'ArslanTakipApp/qrKalite.html'

class HareketView(generic.TemplateView):
    template_name = 'ArslanTakipApp/hareket.html'

def qrDeneme(request):
    return

class SiparisView(generic.TemplateView):
    template_name = 'ArslanTakipApp/siparisList.html'

class Siparis2View(generic.TemplateView):
    template_name = 'ArslanTakipApp/siparisDeneme.html'

def annotate_siparis2():
    return SiparisList.objects.using('dies').filter(
        Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')) \
    .values('ProfilNo', 'FirmaAdi') \
    .annotate(
        ToplamSiparisKg=Sum('GirenKg'),
        ToplamKalanKg=Sum('Kg'),
        TopTenKg=Subquery(
            KalipMs.objects.using('dies').filter(
                ProfilNo=OuterRef('ProfilNo'),
                AktifPasif='Aktif',
                Hatali=0,
                TeniferKalanOmurKg__gte=0
            ).values('ProfilNo').annotate(
                total=Sum('TeniferKalanOmurKg')
            ).values('total')[:1]
        ),
        AktifKalipSayisi=Subquery(
            KalipMs.objects.using('dies').filter(
                ProfilNo=OuterRef('ProfilNo'),
                AktifPasif='Aktif',
                Hatali=0,
                TeniferKalanOmurKg__gte=0
            ).values('ProfilNo').annotate(
                cnt=Count('*')
            ).values('cnt')[:1]
        ),
        ToplamKalipSayisi=Subquery(
            KalipMs.objects.using('dies').filter(
                ProfilNo=OuterRef('ProfilNo'),
                AktifPasif='Aktif',
                Hatali=0
            ).values('ProfilNo').annotate(
                cnt=Count('*')
            ).values('cnt')[:1]
        )
    ).order_by('ProfilNo', 'FirmaAdi')

def siparis2_list(request):
    siparis = annotate_siparis2()
    siparisValues = siparis.values('ProfilNo', 'FirmaAdi', 'ToplamSiparisKg', 'ToplamKalanKg', 'TopTenKg', 'AktifKalipSayisi', 'ToplamKalipSayisi')
    paginator = Paginator(siparisValues, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for p in page_obj:
        p['ToplamSiparisKg'] = locale.format_string("%.0f", math.ceil(p['ToplamSiparisKg']), grouping=True)
        p['ToplamKalanKg'] = locale.format_string("%.0f", math.ceil(p['ToplamKalanKg']), grouping=True)
        p['TopTenKg'] = locale.format_string("%.0f", math.ceil(p['TopTenKg']), grouping=True)
        p['KalipSayisi'] = f"{p['AktifKalipSayisi']} / {p['ToplamKalipSayisi']}"

    current_page = page_obj.number
    total_pages = paginator.num_pages
    page_range = list(range(max(current_page - 3, 1), min(current_page + 4, total_pages + 1)))

    context = {
        'page_obj': page_obj,
        'page_range': page_range,
    }
    return render(request, 'ArslanTakipApp/siparisDeneme.html', context)

def siparis3_list(request):
    params = json.loads(unquote(request.GET.get('params', '{}')))
    size = params.get("size", 10)  # Default size to 10
    offset, limit = calculate_pagination(params.get("page", 1), size)
    filter_list = params.get("filter", [])
    # sorter_List = params.get("sL", [])

    siparis = annotate_siparis2()

    if len(filter_list)>0:
        for i in filter_list:
            print(i)
    else:
        siparis = siparis.exclude(SiparisTamam='BLOKE')

    siparisList = list(siparis.values('ProfilNo', 'FirmaAdi', 'ToplamSiparisKg', 'ToplamKalanKg', 'TopTenKg', 'AktifKalipSayisi', 'ToplamKalipSayisi'))[offset:limit]
    rowNo = 0
    for s in siparisList:
        rowNo += 1
        s['rowNo'] = rowNo
        s['ToplamSiparisKg'] = locale.format_string("%.0f", math.ceil(s['ToplamSiparisKg']), grouping=True)
        s['ToplamKalanKg'] = locale.format_string("%.0f", math.ceil(s['ToplamKalanKg']), grouping=True)
        if s['TopTenKg'] != None:
            s['TopTenKg'] = locale.format_string("%.0f", math.ceil(s['TopTenKg']), grouping=True)
        else: s['TopTenKg'] = 0
        if s['AktifKalipSayisi'] == None: s['AktifKalipSayisi'] = 0
        if s['ToplamKalipSayisi'] == None: s['ToplamKalipSayisi'] = 0
        s['KalipSayisi'] = f"{s['AktifKalipSayisi']} / {s['ToplamKalipSayisi']}"
    
    sip_count = siparis.count()
    lastData= {'last_page': math.ceil(sip_count/size), 'data': []}
    lastData['data'] = siparisList
    data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

def siparis2_child(request):
    params = json.loads(unquote(request.GET.get('params', '{}')))
    profilNo = params.get("pNo", "")
    firmaAdi = params.get("fAdi", "")

    siparisler = SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')). \
        filter(ProfilNo=profilNo, FirmaAdi=firmaAdi)
    siparisList = list(siparisler.values().order_by('SonTermin'))

    for s in siparisList:
        s['GirenKg'] = locale.format_string("%.0f", s['GirenKg'], grouping=True)
        s['Kg'] = locale.format_string("%.0f", s['Kg'], grouping=True)
        if s['SiparisTamam'] == 'BLOKE':
            s['BlokeDurum'] = False
        else: s['BlokeDurum'] = True
        s['SonTermin'] = format_date(s['SonTermin'])

    data = json.dumps(siparisList, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

# Helper function for aggregation and formatting
def aggregate_and_format(queryset, field):
    max_val = math.ceil(queryset.aggregate(Max(field))[f'{field}__max'])
    return locale.format_string("%.0f", max_val, grouping=True)

def aggregate_multiple_and_format(queryset, fields):
    annotations = {f"{field}__max": Max(field) for field in fields}
    aggregated = queryset.aggregate(**annotations)
    
    formatted = {}
    for field in fields:
        max_key = f"{field}__max"
        max_val = math.ceil(aggregated[max_key])
        formatted[field] = locale.format_string("%.0f", max_val, grouping=True)
        
    return formatted
# Helper function for annotation and initial query
def annotate_siparis():
    return SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')
                                                 ).annotate(
    TopTenKg=Subquery(
        KalipMs.objects.using('dies').filter(
            ProfilNo=OuterRef('ProfilNo'),
            AktifPasif='Aktif',
            Hatali=0,
            TeniferKalanOmurKg__gte=0
        ).values('ProfilNo').annotate(
            total=Sum('TeniferKalanOmurKg')
        ).values('total')[:1]
    ),
    AktifKalipSayisi=Subquery(
        KalipMs.objects.using('dies').filter(
            ProfilNo=OuterRef('ProfilNo'),
            AktifPasif='Aktif',
            Hatali=0,
            TeniferKalanOmurKg__gte=0
        ).values('ProfilNo').annotate(
            cnt=Count('*')
        ).values('cnt')[:1]
    ),
    ToplamKalipSayisi=Subquery(
        KalipMs.objects.using('dies').filter(
            ProfilNo=OuterRef('ProfilNo'),
            AktifPasif='Aktif',
            Hatali=0
        ).values('ProfilNo').annotate(
            cnt=Count('*')
        ).values('cnt')[:1]
    )
    )

def format_item(a):
    #append to the end of the tuple
    #a[20] girenkg, 21 kalankg, 22 sontermin, 23 topten
    ttk = 0
    if a[15]: #aktifkalipsayısı
        ttk = math.ceil(a[14])
    b = (locale.format_string("%.0f", math.ceil(a[3]), grouping=True), 
            locale.format_string("%.0f", math.ceil(a[5]), grouping=True),
            format_date(a[12]),
            locale.format_string("%.0f", ttk, grouping=True))
    a += b
    return a
    
def aggregate_in_parallel(queryset, fields):
    with ThreadPoolExecutor() as executor:
        future_to_field = {executor.submit(aggregate_and_format, queryset, field): field for field in fields}
        return {future_to_field[future]: future.result() for future in concurrent.futures.as_completed(future_to_field)}

def apply_filters(s, filter_list):
    q = {}
    exclude_conditions = {}

    for i in filter_list:
        field = i['field']
        value = i['value']
        filter_type = i['type']

        if field == 'TopTenKg':
            q["ProfilNo__in"] = siparis_TopTenFiltre(i)
        elif filter_type == 'like':
            q[field + "__startswith" if field != 'FirmaAdi' else field + "__contains"] = value
        elif filter_type == '=':
            condition = handle_siparis_tamam_filter(field, value)
            if condition:
                if condition[0] == 'exclude':
                    exclude_conditions[condition[1]] = condition[2]
                else:
                    q[condition[0]] = condition[1]
        elif filter_type != value:
            q[field + "__gte"] = filter_type
            q[field + "__lt"] = value
        else:
            q[field] = value

    return (q, exclude_conditions)

def handle_siparis_tamam_filter(field, value):
    if field == 'SiparisTamam':
        if value == 'BLOKE':
            return (field, value)
        elif value == 'degil':
            return ('exclude', field, 'BLOKE')
    else:
        return (field, value)

def siparis_list(request):
    params = json.loads(unquote(request.GET.get('params', '{}')))
    for i in params:
        value = params[i]
        print("Key and Value pair are ({}) = ({})".format(i, value))
    size = params.get("size", 10)  # Default size to 10
    offset, limit = calculate_pagination(params.get("page", 1), size)
    filter_list = params.get("filter", [])
    sorter_List = params.get("sL", [])
    hesap = params.get("h", {})
    
    s = annotate_siparis() # toplam ve aktif kalıp sayısı, toplam kalan tenifer ömrü kg
    q={}
    e ={}
    
    if len(filter_list)>0:
        q, exclude_cond = apply_filters(s, filter_list)
        if exclude_cond:
            s = s.exclude(**exclude_cond)

        s = s.filter(**q).order_by('-SonTermin')
    else:
        s = s.exclude(SiparisTamam='BLOKE')

    sor =[]
    if len(sorter_List)>0:
        for j in sorter_List:
            if j['field'] != 'TopTenKg':
                if j['type'] == 'Azalan':
                    sor.append( "-"+j['field'])
                else: sor.append(j['field'])
            else: 
                if j['type'] == 'Azalan':
                    sor.append( "-TopTenKg")
                else: sor.append("TopTenKg")
        s = s.order_by(*sor)
    else: s= s.order_by('-SonTermin')

    e['TopTenSum'] = ""

    if hesap == 1:
        TenVList = list(s.values_list('TopTenKg',flat=True).order_by('-TopTenKg'))
        out = [sum(g) for t, g in groupby(TenVList, type)if t is not NoneType]
        e['TopTenSum'] =locale.format_string("%.0f", math.ceil(out[0]), grouping=True)
    
    sval = s.values('KartNo','ProfilNo','FirmaAdi', 'GirenKg', 'GirenAdet', 'Kg', 'Adet', 'PlanlananMm', 'Siparismm', 'KondusyonTuru', 'PresKodu','SiparisTamam','SonTermin','BilletTuru', 'TopTenKg', 'AktifKalipSayisi', 'ToplamKalipSayisi', 'Kimlik', 'Profil_Gramaj')[offset:limit]
    svalueslist = s.values_list('KartNo','ProfilNo','FirmaAdi', 'GirenKg', 'GirenAdet', 'Kg', 'Adet', 'PlanlananMm', 'Siparismm', 'KondusyonTuru', 'PresKodu','SiparisTamam','SonTermin','BilletTuru', 'TopTenKg', 'AktifKalipSayisi', 'ToplamKalipSayisi', 'Kimlik', 'Profil_Gramaj')[offset:limit]

    with ThreadPoolExecutor() as executor:
        svalueslist = list(executor.map(format_item, svalueslist))

    sip_count = s.count()
    lastData= {'last_page': math.ceil(sip_count/size), 'data': [], 'e':e}
    lastData['data'] = svalueslist
    data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

def siparis_TopTenFiltre(i):
    sProfil = list(SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')).values_list('ProfilNo', flat=True).distinct())
    k= KalipMs.objects.using('dies').filter(ProfilNo__in = sProfil, AktifPasif="Aktif", Hatali=0)
    kal = k.values('ProfilNo').filter(TeniferKalanOmurKg__gte = 0).annotate(pcount=Sum('TeniferKalanOmurKg'))
    kPList = set(list(kal.values_list('ProfilNo', flat=True).distinct()))
    if i['type'] != i['value']:
        profilList = list(kal.filter(pcount__gte = i['type'], pcount__lt = i['value']).values_list('ProfilNo', flat=True))
    else: profilList = list(kal.filter(pcount__gte = i['type']-1, pcount__lt = i['value']+1).values_list('ProfilNo', flat=True))
    diff = [x for x in sProfil if x not in kPList]
    if len(diff)>0 :
        profilList += diff #azalan sıralarken böyle artan sıralarken diff +=profilList return diff
    
    return profilList

def siparis_max(request):
    params = json.loads(unquote(request.GET.get('params', '{}')))
    filter_list = params.get("filter", [])

    base_s = SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE'))
    k= KalipMs.objects.using('dies').filter(TeniferKalanOmurKg__gte = 0, AktifPasif="Aktif", Hatali=0)
    
    if len(filter_list)>0:
        q, exclude_cond = apply_filters(base_s, filter_list)
        if exclude_cond:
            base_s = base_s.exclude(**exclude_cond)

        base_s = base_s.filter(**q).order_by('-SonTermin')
    else:
        base_s = base_s.exclude(SiparisTamam='BLOKE')
    
    # Perform aggregation once and access values
    aggr = base_s.aggregate(
        giren_max = Max('GirenKg'),
        kg_max = Max('Kg'),
        giren_sum = Sum('GirenKg'),
        kg_sum = Sum('Kg')
    )
    
    e = {
        'GirenMax':  locale.format_string("%.0f", math.ceil(aggr['giren_max'] or 0), grouping=True),
        'KgMax':  locale.format_string("%.0f", math.ceil(aggr['kg_max'] or 0), grouping=True),
        'GirenSum':  locale.format_string("%.0f", math.ceil(aggr['giren_sum'] or 0), grouping=True),
        'KgSum':  locale.format_string("%.0f", math.ceil(aggr['kg_sum'] or 0), grouping=True),
    }
    
    sProfil = list(base_s.values_list('ProfilNo', flat=True).distinct())
    proTop = k.filter(ProfilNo__in = sProfil).values('ProfilNo').annotate(psum = Sum('TeniferKalanOmurKg'))
    sonuc = proTop.aggregate(Max('psum'))['psum__max']
    e['TopTenMax']  = math.ceil(sonuc)
    
    return JsonResponse(e)

def siparis_child(request, pNo):
    #Kalıp Listesi Detaylı
    kalip = KalipMs.objects.using('dies').values('KalipNo','UreticiFirma', 'TeniferKalanOmurKg', 'UretimToplamKg', 'PresKodu', 'Capi')
    child = kalip.filter(ProfilNo=pNo, AktifPasif="Aktif", Hatali=0)
    location_list = Location.objects.values()
    gonder = list(child)
    for c in gonder:
        pkodu = PresUretimRaporu.objects.using('dies') \
                        .filter(KalipNo=c["KalipNo"]).order_by("-Tarih", "-BitisSaati").values("PresKodu","Tarih", "BitisSaati")
        k = DiesLocation.objects.get(kalipNo = c['KalipNo']).kalipVaris_id
        if pkodu:
            c['SonPresKodu'] = pkodu[0]['PresKodu']
        try:
            c['Konum'] = list(location_list.filter(id=list(location_list.filter(id=k))[0]["locationRelationID_id"]))[0]["locationName"] + " <BR>└ " + list(location_list.filter(id=k))[0]["locationName"]
        except:
            try:
                c['Konum'] = list(location_list.filter(id=k))[0]["locationName"]
            except:
                c['Konum'] = ""

    data = json.dumps(gonder)
    return HttpResponse(data)

def siparis_presKodu(request, pNo):
    kalip = KalipMs.objects.using('dies').values('KalipNo', 'PresKodu', 'Capi')
    child = kalip.filter(ProfilNo=pNo, AktifPasif="Aktif", Hatali=0)
    kodlar = {}
    kalipNoList = list(child.order_by().values_list('KalipNo', flat=True).distinct())

    kalipPresKodu = list(child.order_by().values_list('PresKodu', flat=True).distinct())
    uRaporuPresKodu = list(PresUretimRaporu.objects.using('dies')
                        .filter(KalipNo__in = kalipNoList).order_by().values_list('PresKodu', flat=True).distinct())
    uRaporuPresKodu = [x.strip(' ') for x in uRaporuPresKodu]

    diff = [x for x in uRaporuPresKodu if x not in kalipPresKodu]

    kodlar = kalipPresKodu + diff
    return JsonResponse(kodlar, safe=False)

def siparis_ekle(request):
    if request.method == "POST":
        e = EkSiparis.objects.all()
        siparis = SiparisList.objects.using('dies').all()
        siparisGet = siparis.get(Kimlik = request.POST['sipKimlik'])
        ekSiparis = EkSiparis()
        ekSiparis.SipKimlik = request.POST['sipKimlik']
        ekSiparis.SipKartNo = siparisGet.KartNo
        ekSiparis.EkAdet = request.POST['planlananAdet']
        ekSiparis.EkPresKodu = request.POST['presKodu']
        ekSiparis.EkTermin = request.POST['ekTermin']
        ekSiparis.EkKg = request.POST['sipEkleKg']
        ekSiparis.KimTarafindan_id = request.user.id
        ekSiparis.Silindi = False
        ekSiparis.MsSilindi = False
        ekSiparis.Sira = e.count()+1
        ekSiparis.EkBilletTuru = siparisGet.BilletTuru
        ekSiparis.EkYuzeyOzelligi = siparisGet.YuzeyOzelligi
        ekSiparis.ProfilNo = siparisGet.ProfilNo

        if not e.filter(SipKartNo = ekSiparis.SipKartNo):
            ekSiparis.EkNo = 1
        else: 
            lastEk = e.filter(SipKartNo = ekSiparis.SipKartNo).order_by('EkNo').latest('EkNo')
            ekSiparis.EkNo = lastEk.EkNo +1

        ekSiparis.save()

    return HttpResponseRedirect("/siparis")
 
def siparis_eksorgu(request, sipKimlik):
    print(sipKimlik)
    ekSiparis = EkSiparis.objects.all().values()
    ekList = list(ekSiparis)
    ekSiparis.filter(sipKimlik__in=sipKimlik)
    #ekSiparisdeki kimlikleri göndermek daha mantıklı yukarıdaki gibi yapmak yerine
    return


class EkSiparisView(generic.TemplateView):
    template_name = 'ArslanTakipApp/eksiparis.html'

def filter_method(i, a):
    if i["type"] == "like":
        a[i['field'] + "__istartswith"] = i['value']
    elif i["type"] == "=":
        a[i['field']] = i['value']
    elif i["type"] == "has":
        a[i['field'] + "__icontains"] = i['value']
    return a

presler = { # eğer 1 ve 2. fabrikada sadece pres adları olacaksa değiştirilecek
    '1100-1': '550', '1100-2': '783', '1100-3': '797',
    '1200-1': '555', '1600-1': '568', '1600-2': '803',
    '2750-1': '808', '4000-1': '816', '4500-1': '1104'
}

firinlar = {
    '1100-1': '1089', '1100-2': '1082', '1100-3': '1084',
    '1200-1': '1088', '1600-1': '1087', '1600-2': '1086',
    '2750-1': '1085', '4000-1': '1081', '4500-1': '1106'
}

meydanlar = {
    '1100-1': '551', '1100-2': '789', '1100-3': '799',
    '1200-1': '556', '1600-1': '569', '1600-2': '804',
    '2750-1': '809', '4000-1': '817', '4500-1': '1105'
}

gozler = {
    '1100-1': [548, 549], '1100-2': [777, 778, 779, 780, 781, 782], '1100-3': [791, 792, 793, 794, 795, 796],
    '1200-1': [552, 553, 554], '1600-1': [562, 563, 564, 565, 566, 567], '1600-2': [801, 802],
    '2750-1': [805, 806, 807], '4000-1': [810, 811, 812, 813, 814, 815], '4500-1': [1109, 1110, 1111, 1112, 1113, 1114, 1115, 1116, 1119, 1120]
}

hatalar = [{'HataKodu': 101, 'HataTuru': 'Uygun'}, {'HataKodu': 102, 'HataTuru': 'Ölçü Bozuk'}, {'HataKodu': 103, 'HataTuru': 'Ekstrüzyon İzi'}, 
        {'HataKodu': 104, 'HataTuru': 'Çizgi Var'}, {'HataKodu': 105, 'HataTuru': 'Kulak Düşük'}, {'HataKodu': 106, 'HataTuru': 'Isı Farkı İzi'}, 
        {'HataKodu': 107, 'HataTuru': 'Sıyırma Yapıyor'}, {'HataKodu': 108, 'HataTuru': 'Çizgi Yaptı'}, {'HataKodu': 109, 'HataTuru': 'Pislik Geldi Yırttı'}, 
        {'HataKodu': 110, 'HataTuru': 'Yüzeyde Kırılmalar Var'}, {'HataKodu': 111, 'HataTuru': 'Yüzeyde Dalgalanmalar var'}, {'HataKodu': 112, 'HataTuru': 'Boy Farkı Var'}, 
        {'HataKodu': 113, 'HataTuru': 'Hava Kabarcığı'}, {'HataKodu': 114, 'HataTuru': 'Bombe'}, {'HataKodu': 115, 'HataTuru': 'Dönüklük'}, 
        {'HataKodu': 116, 'HataTuru': "90'ı Açı Bozuk"}, {'HataKodu': 117, 'HataTuru': 'Yüzey Bozuk'}, {'HataKodu': 118, 'HataTuru': 'Yüzey Bozuldu'}, 
        {'HataKodu': 119, 'HataTuru': 'Et Kalınlığı Düşük'}, {'HataKodu': 120, 'HataTuru': 'Et Kalınlığı Fazla'}, {'HataKodu': 121, 'HataTuru': 'Arka Parçaya Sürtüyor'}, 
        {'HataKodu': 122, 'HataTuru': 'Bolstere Sürtüyor'}, {'HataKodu': 123, 'HataTuru': 'Kalıp Kırıldı'}, {'HataKodu': 124, 'HataTuru': 'İçe Kasıyor'}, 
        {'HataKodu': 125, 'HataTuru': 'Dışa Kasıyor'}, {'HataKodu': 126, 'HataTuru': 'Yukarı Kasıyor'}, {'HataKodu': 127, 'HataTuru': 'Set var'}, 
        {'HataKodu': 128, 'HataTuru': 'Dirençli Kalıp (Yüksek Barda Çıkıyor )'}, {'HataKodu': 129, 'HataTuru': 'Damar Var'}, {'HataKodu': 130, 'HataTuru': 'Dalgalı'}, 
        {'HataKodu': 131, 'HataTuru': 'Çökük İçe'}, {'HataKodu': 132, 'HataTuru': 'Zıvana Kaçık'}, {'HataKodu': 133, 'HataTuru': 'Günyesi Bozuk'}, 
        {'HataKodu': 134, 'HataTuru': 'Boy Kurtarmadı'}, {'HataKodu': 136, 'HataTuru': 'Kalıp Tıkandı'}, {'HataKodu': 137, 'HataTuru': 'Kalıp Doldu'}, 
        {'HataKodu': 138, 'HataTuru': 'Kulak Düşük'}, {'HataKodu': 139, 'HataTuru': 'Kulak Kalkık'}, {'HataKodu': 140, 'HataTuru': 'Isı Hatası'}, 
        {'HataKodu': 141, 'HataTuru': 'Eloksal Sonrsı İz Var'}, {'HataKodu': 142, 'HataTuru': 'Kasıntı Var Son Kısmında'}, {'HataKodu': 143, 'HataTuru': 'Kalıp Resmi Hatalı'}, 
        {'HataKodu': 145, 'HataTuru': 'Hatalı Verilen Kalıp'}, {'HataKodu': 146, 'HataTuru': 'Boy Farkı Var'}, {'HataKodu': 147, 'HataTuru': 'Kalıp Kırıldı'}, 
        {'HataKodu': 149, 'HataTuru': 'Kulak Kalkık'}, {'HataKodu': 150, 'HataTuru': 'Test İmalat'}, {'HataKodu': 151, 'HataTuru': 'Gramaj Düşük'}, 
        {'HataKodu': 152, 'HataTuru': 'Gramaj Yüksek'}, {'HataKodu': 153, 'HataTuru': 'Hız Verince Sıyırma Yapıyor'}, {'HataKodu': 154, 'HataTuru': 'Dalga yapmaya başladı'}, {'HataKodu': 180, 'HataTuru': 'Alaşım Yanlış'}]

def kalipPresCheck(sId): # EkSiparisKalip kontrol edilsin ona göre butonlar getirilsin.
    eksiparis = EkSiparis.objects.get(id=sId)
    pNo = eksiparis.ProfilNo
    pKodu = eksiparis.PresKodu
    presId = presler[pKodu]
    firinId = firinlar[pKodu]
    # Fetch locations and dies once, outside loop
    pres = Location.objects.filter(id=presId).first()
    location_data = DiesLocation.objects.filter(kalipVaris=pres)
    gozler = Location.objects.filter(locationRelationID=firinId)
    kalipList = DiesLocation.objects.filter(kalipVaris__in=gozler).values_list('kalipNo', flat=True)
    kaliplar = KalipMs.objects.using('dies').filter(KalipNo__in=list(kalipList), ProfilNo=pNo).values_list('KalipNo', flat=True)

    if pres:
        location = location_data.first()  # Reuse filtered data
        if location:
            # Check die once instead of filtering each time
            die = KalipMs.objects.using('dies').filter(KalipNo=location.kalipNo, ProfilNo=pNo).first()
            if die:  # This already confirms that it's the correct die
                return 1  # üretimi bitir
            elif kaliplar:
                return 4  # Kalıp exists in Gözler
            return 2  # Boş
    if kaliplar:
        return 3  # Kalıp exists in Fırında, start production

    return 2  # Boş
    
def eksiparis_uretim(request): # Üretime Başla
    params = json.loads(unquote(request.GET.get('params')))
    sId = params["sId"] #siparişteki pres koduna göre o presin fırınlarında siparişteki profil noya uygun kalıp varsa listele
    kalipNo = params["kalipNo"]
    eksiparis = EkSiparis.objects.get(id=sId)
    pNo = eksiparis.ProfilNo
    pKodu = eksiparis.EkPresKodu

    if kalipNo == "":
        firinId = firinlar[pKodu]
        gozler = Location.objects.filter(locationRelationID=firinId)
        kalipList = DiesLocation.objects.filter(kalipVaris__in=gozler).values_list('kalipNo', flat=True)
        kaliplar = KalipMs.objects.using('dies').filter(KalipNo__in= list(kalipList), ProfilNo=pNo).values_list('KalipNo', flat=True)

        if len(kaliplar) == 1: #bir taneyse hemen üretime al ve cevap olarak hangi kalıbın prese eklendiğini döndür
            k = DiesLocation.objects.get(kalipNo=kaliplar[0])
            Hareket.objects.create(
                kalipKonum_id=k.kalipVaris.id,
                kalipVaris_id=presler[pKodu],
                kalipNo=kaliplar[0],
                kimTarafindan_id=request.user.id
            )
            EkSiparisKalip.objects.create(
                EkSiparisBilgi_id = sId,
                KalipNo = kalipNo,
                Uretim = "Basla",
            )
            response = JsonResponse({'message': f"{kaliplar[0]} No'lu kalıp başarıyla gönderildi."})
        elif len(kaliplar) > 1: #birden fazla o profil noda kalıp var ise hangi kalıplar olduğunu gönder, modalda göster. seçilen kalıbı o prese kaydet.
            data = list(kaliplar)
            response = JsonResponse({'message': "", 'kaliplar':data})
        elif len(kaliplar) < 1:
            response = JsonResponse({'message': f"Fırında {pNo} No'lu kalıp bulunmamaktadır."}) # kalıp olmayan durumlarda buton yok zaten bunu göstermeye gerek yok. ya da burda dursun sayfa yenilenmezse ve 
            # ilk başta fırında olan kalıp sonradan başka yere gönderilirse burada yakalamış oluruz. 
    else:
        k = DiesLocation.objects.get(kalipNo=kalipNo)
        Hareket.objects.create(
            kalipKonum_id=k.kalipVaris.id,
            kalipVaris_id=presler[pKodu],
            kalipNo=kalipNo,
            kimTarafindan_id=request.user.id
        )
        EkSiparisKalip.objects.create(
            EkSiparisBilgi_id = sId,
            KalipNo = kalipNo,
            Uretim = "Basla",
        )
        response = JsonResponse({'message': f"{kalipNo} No'lu kalıp ile üretim başladı."})
    return response

def eksiparis_uretimbitir(request): # Üretim Bitir Kaydet
    req = request.POST
    kalipNo = DiesLocation.objects.filter(kalipVaris__id=presler[req['EkSiparisPresKodu']]).values_list('kalipNo', flat=True)
    if req['uretimBitirmeSebebi'] == "Kalıbı Sök": #meydana gnder
        kalipVaris = meydanlar[req['EkSiparisPresKodu']]
    elif req['uretimBitirmeSebebi'] == "Kalıbı Fırına At": #göze gönder
        kalipVaris = req['kalipGozleri']

    Hareket.objects.create(
        kalipKonum_id=presler[req['EkSiparisPresKodu']],
        kalipVaris_id=kalipVaris,
        kalipNo=kalipNo,
        kimTarafindan_id=request.user.id
    )

    EkSiparisKalip.objects.create(
        EkSiparisBilgi_id = req['EkSiparisId'],
        KalipNo = kalipNo,
        Uretim = "Bitir",
        HataKodu = req.get('HataKodu', None),
        UretimBitirmeSebebi = req['uretimBitirmeSebebi'],
        UretimBitirmeSebebiAciklama = req['kalipAciklama'],
    )
    return JsonResponse({'message': "İşlem Başarıyla Gerçekleştirildi."})

def eksiparis_selectgetir(request): # Üretim Bitirme Sebebine Göre Açıklamalar
    params = json.loads(unquote(request.GET.get('params')))
    secim = params["secim"]
    pres = params["pres"]
    if secim == "Kalıbı Sök": #Kalıbı Sök seçilmiş. Açıklamaları getir.
        hataList = [{'HataKodu': 101, 'HataTuru': 'Uygun'}, {'HataKodu': 102, 'HataTuru': 'Ölçü Bozuk'}, {'HataKodu': 103, 'HataTuru': 'Ekstrüzyon İzi'}, 
        {'HataKodu': 104, 'HataTuru': 'Çizgi Var'}, {'HataKodu': 105, 'HataTuru': 'Kulak Düşük'}, {'HataKodu': 106, 'HataTuru': 'Isı Farkı İzi'}, 
        {'HataKodu': 107, 'HataTuru': 'Sıyırma Yapıyor'}, {'HataKodu': 108, 'HataTuru': 'Çizgi Yaptı'}, {'HataKodu': 109, 'HataTuru': 'Pislik Geldi Yırttı'}, 
        {'HataKodu': 110, 'HataTuru': 'Yüzeyde Kırılmalar Var'}, {'HataKodu': 111, 'HataTuru': 'Yüzeyde Dalgalanmalar var'}, {'HataKodu': 112, 'HataTuru': 'Boy Farkı Var'}, 
        {'HataKodu': 113, 'HataTuru': 'Hava Kabarcığı'}, {'HataKodu': 114, 'HataTuru': 'Bombe'}, {'HataKodu': 115, 'HataTuru': 'Dönüklük'}, 
        {'HataKodu': 116, 'HataTuru': "90'ı Açı Bozuk"}, {'HataKodu': 117, 'HataTuru': 'Yüzey Bozuk'}, {'HataKodu': 118, 'HataTuru': 'Yüzey Bozuldu'}, 
        {'HataKodu': 119, 'HataTuru': 'Et Kalınlığı Düşük'}, {'HataKodu': 120, 'HataTuru': 'Et Kalınlığı Fazla'}, {'HataKodu': 121, 'HataTuru': 'Arka Parçaya Sürtüyor'}, 
        {'HataKodu': 122, 'HataTuru': 'Bolstere Sürtüyor'}, {'HataKodu': 123, 'HataTuru': 'Kalıp Kırıldı'}, {'HataKodu': 124, 'HataTuru': 'İçe Kasıyor'}, 
        {'HataKodu': 125, 'HataTuru': 'Dışa Kasıyor'}, {'HataKodu': 126, 'HataTuru': 'Yukarı Kasıyor'}, {'HataKodu': 127, 'HataTuru': 'Set var'}, 
        {'HataKodu': 128, 'HataTuru': 'Dirençli Kalıp (Yüksek Barda Çıkıyor )'}, {'HataKodu': 129, 'HataTuru': 'Damar Var'}, {'HataKodu': 130, 'HataTuru': 'Dalgalı'}, 
        {'HataKodu': 131, 'HataTuru': 'Çökük İçe'}, {'HataKodu': 132, 'HataTuru': 'Zıvana Kaçık'}, {'HataKodu': 133, 'HataTuru': 'Günyesi Bozuk'}, 
        {'HataKodu': 134, 'HataTuru': 'Boy Kurtarmadı'}, {'HataKodu': 136, 'HataTuru': 'Kalıp Tıkandı'}, {'HataKodu': 137, 'HataTuru': 'Kalıp Doldu'}, 
        {'HataKodu': 138, 'HataTuru': 'Kulak Düşük'}, {'HataKodu': 139, 'HataTuru': 'Kulak Kalkık'}, {'HataKodu': 140, 'HataTuru': 'Isı Hatası'}, 
        {'HataKodu': 141, 'HataTuru': 'Eloksal Sonrsı İz Var'}, {'HataKodu': 142, 'HataTuru': 'Kasıntı Var Son Kısmında'}, {'HataKodu': 143, 'HataTuru': 'Kalıp Resmi Hatalı'}, 
        {'HataKodu': 145, 'HataTuru': 'Hatalı Verilen Kalıp'}, {'HataKodu': 146, 'HataTuru': 'Boy Farkı Var'}, {'HataKodu': 147, 'HataTuru': 'Kalıp Kırıldı'}, 
        {'HataKodu': 149, 'HataTuru': 'Kulak Kalkık'}, {'HataKodu': 150, 'HataTuru': 'Test İmalat'}, {'HataKodu': 151, 'HataTuru': 'Gramaj Düşük'}, 
        {'HataKodu': 152, 'HataTuru': 'Gramaj Yüksek'}, {'HataKodu': 153, 'HataTuru': 'Hız Verince Sıyırma Yapıyor'}, {'HataKodu': 154, 'HataTuru': 'Dalga yapmaya başladı'}, {'HataKodu': 180, 'HataTuru': 'Alaşım Yanlış'}]

        response = JsonResponse({'data': hataList})
    elif secim == "Kalıbı Fırına At":
        optionList = [{'Sebep': 'Arıza'}, {'Sebep': 'Vardiya Sonu'}]
        gozList = list(Location.objects.filter(id__in = gozler[pres]).values())
        response = JsonResponse({'data': optionList, 'gozler': gozList})
    
    return response

def eksiparis_timeline(request):
    ekSiparis = EkSiparis.objects.exclude(MsSilindi=True).exclude(Silindi=True).order_by("Sira")
    raporlar = ekSiparis.values().order_by('Sira')
    raporList = list(raporlar)

    last_year = datetime.datetime.now() - datetime.timedelta(days=365)
    pres_raporlar = PresUretimRaporu.objects.using('dies') \
                    .filter(Tarih__gte=last_year, IslemGoren_Kg__gt=0) \
                    .values('StokCinsi', 'PresKodu') \
                    .annotate(toplam_sure=Cast(Sum('Sure', default=0), FloatField()),
                            toplam_kg=Sum('IslemGoren_Kg', default=0))
    # pres_raporlar_map = {(rapor['StokCinsi'], rapor['PresKodu']): {'toplam_kg': rapor['toplam_kg'], 'toplam_sure': rapor['toplam_sure']} for rapor in pres_raporlar}
    # data = pres_raporlar_map.get(key, {'toplam_kg': 0, 'toplam_sure': 0})
    # key = (i['EkBilletTuru'], i['EkPresKodu'])
    shifts = []
    current_shift = []
    current_shift_duration = 0
    for i in raporList:
        query = pres_raporlar.filter(StokCinsi=i['EkBilletTuru'], PresKodu=i['EkPresKodu'])
        if query:
            query = query[0]
            toplam_kg = query['toplam_kg']
            toplam_sure = query['toplam_sure']
            ortalama_hiz = toplam_kg / toplam_sure if toplam_sure != 0 else 0

            if ortalama_hiz != 0:
                i['TahminiSure'] = str(math.ceil(i['EkKg'] / ortalama_hiz)) + " dk"
            else:
                i['TahminiSure'] = 0

            ek_siparis_duration = int(i['TahminiSure'].split()[0])
            if current_shift_duration + ek_siparis_duration <= 720: # bir vardiya 720 dk 8-20 şeklinde ise, 8-8 ise 1440 dk olacak.
                current_shift.append(i)
                current_shift_duration += ek_siparis_duration
            else:
                break
            # shifts.append(current_shift)
            # current_shift = [i]
            # current_shift_duration = ek_siparis_duration
    
    # if current_shift:
    #     shifts.append(current_shift)

    data = json.dumps(raporList, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

def eksiparis_hammadde(request):
    ekSiparis = EkSiparis.objects.exclude(MsSilindi = True).exclude(Silindi = True).order_by("Sira")
    raporlar = ekSiparis.values('EkBilletTuru')\
                        .annotate(Net=Sum('EkKg'))\
                        .order_by('EkBilletTuru')
    ek_raporlar = raporlar.order_by('-Net')
    last_year = datetime.datetime.now() - datetime.timedelta(days=365)
    billet_types = [r['EkBilletTuru'] for r in ek_raporlar]

    pres_raporlar = PresUretimRaporu.objects.using('dies')\
                        .filter(StokCinsi__in=billet_types, Tarih__gte=last_year)\
                        .values('StokCinsi')\
                        .annotate(TotalIslemGorenKg=Sum('IslemGoren_Kg'), TotalBilletKg=Sum('ToplamBilletKg'))
    pres_data_map = {item['StokCinsi']: item for item in pres_raporlar}

    for ek in ek_raporlar:
        billet_type = ek['EkBilletTuru']
        net = ek['Net']
        pres_data = pres_data_map.get(billet_type, {})
        total_islem_goren_kg = pres_data.get('TotalIslemGorenKg', 0)
        total_billet_kg = pres_data.get('TotalBilletKg', 0)
        fire = 1 - (total_islem_goren_kg / total_billet_kg if total_billet_kg else 0)
        ek['Brut'] = math.ceil(net / (1 - fire)) if fire < 1 else net

    data = json.dumps(list(ek_raporlar), sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)
    
def eksiparis_yuzey(request):
    ekSiparis = EkSiparis.objects.exclude(MsSilindi = True).exclude(Silindi = True).order_by("Sira")
    raporlar = ekSiparis.values('EkYuzeyOzelligi')\
                        .annotate(Net=Sum('EkKg'))\
                        .order_by('EkYuzeyOzelligi')
    raporList = list(raporlar.order_by('-Net'))
    data = json.dumps(raporList, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)


class PresSiparisListView(generic.TemplateView):
    template_name = 'ArslanTakipApp/presSiparisList.html'
    
    # eğer preste kalıp var ise uyarı versin ve yeni üretime başlanamasın
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pres_grubu = '4500-1'
        location_ids = gozler.get(pres_grubu, [])

        die_numbers = list(DiesLocation.objects.filter(kalipVaris__in=location_ids).values_list('kalipNo', flat=True))
        profil_list = set(KalipMs.objects.using('dies')
                      .filter(KalipNo__in=list(die_numbers))
                      .exclude(Silindi=1)
                      .values_list('ProfilNo', flat=True))
        orders = (
            SiparisList.objects.using('dies')
            .filter(Adet__gt=0, KartAktif=1, BulunduguYer__in=['DEPO', 'TESTERE'], ProfilNo__in=profil_list)
            .only('ProfilNo', 'Kimlik', 'Kg', 'KartNo', 'SonTermin', 'BilletTuru', 'KondusyonTuru', 'YuzeyOzelligi') 
        )
        
        grouped_orders = {}
        for order in orders:
            profil_no = order.ProfilNo
            if profil_no not in grouped_orders:
                grouped_orders[profil_no] = []
            grouped_orders[profil_no].append({
                'Kimlik': order.Kimlik,
                'KartNo': order.KartNo,
                'Kg': order.Kg,
                'Termin': format_date(order.SonTermin),
                'BilletTuru': order.BilletTuru,
                'KondusyonTuru': order.KondusyonTuru,
                'YuzeyOzelligi': order.YuzeyOzelligi,
            })

        context['grouped_orders'] = grouped_orders
        return context
    
    def post(self, request, *args, **kwargs):
        kimlik = request.POST.get('kimlik')
        die_number = request.POST.get('die_number')

        try:
            production_id = self.start_production(kimlik, die_number) # oluşturduğumuz presuretimtakip entrysinin idsini döndür
            
            return JsonResponse({'status': 'success', 'message': 'Üretim başarıyla başlatıldı.', 'id': production_id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        
    def start_production(self, kimlik, die_number):
        print(f"kimlik: {kimlik}, kalıp no: {die_number}")
        # pres_kodu = '4500-1' olan pres_takipi bul ve değiştir, yoksa yarat
        pres_kodu = '4500-1' # parametre olarak gönder
        try: 
            pres_takip = PresUretimTakip.objects.get(pres_kodu=pres_kodu)
            pres_takip.siparis_kimlik = kimlik
            pres_takip.kalip_no = die_number
            pres_takip.baslangic_datetime = datetime.datetime.now()
            pres_takip.save()

        except PresUretimTakip.DoesNotExist:
            pres_takip = PresUretimTakip.objects.create(
                siparis_kimlik=kimlik,
                kalip_no=die_number,
                pres_kodu=pres_kodu,
                baslangic_datetime=datetime.datetime.now()
            )
        return pres_takip.id 

def get_die_numbers_for_production(request):
    profil_no = request.GET.get('profil_no')
    pres_grubu = '4500-1' 
    location_ids = gozler.get(pres_grubu, [])

    kalip_nos = set(KalipMs.objects.using('dies').filter(ProfilNo=profil_no).exclude(Silindi=1).values_list('KalipNo', flat=True))

    die_numbers = list(DiesLocation.objects.filter(kalipVaris__in=location_ids, kalipNo__in=kalip_nos).values_list('kalipNo', flat=True))
    return JsonResponse({'dieNumbers': die_numbers})

def pres_siparis_takip(request, id):
    presuretim = get_object_or_404(PresUretimTakip, id=id)
    siparis = SiparisList.objects.using('dies').filter(Kimlik=presuretim.siparis_kimlik)[0]
    print(siparis)
    kalip = KalipMs.objects.using('dies').filter(KalipNo=presuretim.kalip_no)[0]
    resim_dizini = kalip.ResimDizini.replace(" ", "")
    resim_yol = "http://arslan/static" + resim_dizini[13:]
    teknik1 = resim_yol + "Teknik1.jpg"
    teknik2 = resim_yol + "Teknik2.jpg"

    siparis.SonTermin = format_date(siparis.SonTermin)

    comments = Comment.objects.filter(FormModel='KalipMs', FormModelId=kalip.KalipNo).order_by("Tarih")
    # def build_comment_tree(comments):
    #     comment_dict = {comment.id: comment for comment in comments}
    #     tree = []

    #     for comment in comments:
    #         comment.KullaniciAdi = get_user_full_name(comment.Kullanici.id)
    #         if comment.Silindi == True:
    #             if comments.filter(ReplyTo_id=comment.id):
    #                 comment.Aciklama = "Yorum silindi."
    #                 tree.append({'comment': comment, 'replies': []})
    #         else:
    #             if comment.ReplyTo is None:  # Top-level comment
    #                 tree.append({'comment': comment, 'replies': []})
    #             else:  # This is a reply
    #                 parent = comment_dict.get(comment.ReplyTo.id)
    #                 if parent:
    #                     for node in tree:
    #                         if node['comment'] == parent or (parent.Silindi and node['comment'].id == parent.id):
    #                             com_dict = {'comment': comment}
    #                             node['replies'].append(com_dict)
    #                             break
    #     return tree
    
    comment_tree = build_comment_tree(comments)
    context = {
        'kalip_no': kalip.KalipNo,
        'teknik1': teknik1,
        'teknik2': teknik2,
        'siparis': siparis,
        'comment_tree': comment_tree,
    }
    return render(request, 'ArslanTakipApp/presUretimTakip.html', context)

def pres_siparis_takip_rapor(request):
    params = json.loads(unquote(request.GET.get('params')))
    size = params["size"]
    page = params["page"]
    offset, limit = calculate_pagination(page, size)
    filter_list = params["filter"]
    q = {} 
    kalip_count = 0
    lastData= {'last_page': math.ceil(kalip_count/size), 'data': []}

    if len(filter_list)>0:
        for i in filter_list:
            if i["type"] == "like":
                q[i['field']+"__startswith"] = i['value']
            elif i["type"] == "=":
                q[i['field']] = i['value']
    
        query = PresUretimRaporu.objects.using('dies').filter(**q) \
        .values('PresKodu', 'Tarih', 'BaslamaSaati', 'BitisSaati', 'HataAciklama', 'Durum').order_by('-Tarih')

        g = list(query[offset:limit])
        for c in g:
            if c['Tarih'] != None:
                c['Tarih'] = format_date(c['Tarih']) + " <BR>└ " + c['BaslamaSaati'].strftime("%H:%M") + " - " + c['BitisSaati'].strftime("%H:%M")
                c['BaslamaSaati'] =c['BaslamaSaati'].strftime("%H:%M")
                c['BitisSaati'] =c['BitisSaati'].strftime("%H:%M")
        kalip_count = query.count()
        lastData= {'last_page': math.ceil(kalip_count/size), 'data': []}
        lastData['data'] = g

    data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

class PresUretimTakipView(generic.TemplateView):
    template_name = 'ArslanTakipApp/presUretimTakipList.html'

def firin_kalip_list(request, pNo):
    pres_grubu = '4500-1'
    
    kalip_nos = list(KalipMs.objects.using('dies').filter(ProfilNo=pNo).values_list('KalipNo', flat=True))
    kalip_numbers = DiesLocation.objects.filter(kalipVaris__in=gozler[pres_grubu], kalipNo__in=kalip_nos).values_list('kalipNo', flat=True)

    return JsonResponse(list(kalip_numbers), safe=False, json_dumps_params={'indent': 2})

def uretim_kalip_firin(request):
    params = json.loads(unquote(request.GET.get('params')))
    size = params['size']
    page = params['page']
    filter_list = params['filter']
    offset, limit = calculate_pagination(page, size)
    pres_grubu = '4500-1' # şimdilik default 4500-1 olsun sonradan kullanıcının grubuna göre belirlenecek
    pres = presler.get(pres_grubu)

    kalip_numbers = DiesLocation.objects.filter(kalipVaris__in=gozler[pres_grubu]).values_list('kalipNo', flat=True)
    profil_list = set(KalipMs.objects.using('dies')
                      .filter(KalipNo__in=list(kalip_numbers))
                      .exclude(Silindi=1)
                      .values_list('ProfilNo', flat=True))
    tum_siparis = SiparisList.objects.using('dies').filter(
        Adet__gt=0, KartAktif=1, BulunduguYer__in=['DEPO', 'TESTERE']
    ).only('Kimlik', 'Kg', 'PlanlananMm', 'Siparismm', 'FirmaAdi', 'KondusyonTuru', 'SonTermin')
    pres_siparis = tum_siparis.filter(PresKodu=pres_grubu, ProfilNo__in=profil_list).order_by('SonTermin')
    pres_data_paginate = list(pres_siparis.values()[offset:limit])

    location = DiesLocation.objects.filter(kalipVaris_id=pres).first()
    active_production = PresUretimTakip.objects.filter(pres_kodu=pres_grubu, bitis_datetime__isnull=True)
    active_siparis_ids = set(active_production.values_list('siparis_kimlik', flat=True))
    active_production_map = {
        p.siparis_kimlik: p.kalip_no for p in active_production
    }
    active_profil_nos = set(KalipMs.objects.using('dies').filter(
        KalipNo__in=[active_production_map.get(kimlik) for kimlik in active_siparis_ids]
    ).values_list('ProfilNo', flat=True))
    uretim = False
    for p in pres_data_paginate:
        p['SonTermin'] = format_date(p['SonTermin'])
        p['KalipUretimDurumu'] = 2
        # p['KalipUretimDurumu'] = 3  # Buton yok
        # if not active_siparis_ids: # presin içinde klaıp var mı onu kontrol et varsa boş buton olacak
        #     p['KalipUretimDurumu'] = 2  # Üretime Başla 
        #     if location:
        #         p['KalipUretimDurumu'] = 3
        # elif p['Kimlik'] in active_siparis_ids:
        #     p['KalipUretimDurumu'] = 1  # Üretimi Bitir
        #     p['KalipNo'] = active_production_map.get(p['Kimlik'])
        #     uretim = True
        # elif p['ProfilNo'] in active_profil_nos and  not p['Kimlik']in active_siparis_ids:
        #     p['KalipUretimDurumu'] = 4
    total_count = pres_siparis.count()
    last_data = {'last_page': math.ceil(total_count / size), 'data': pres_data_paginate, 'uretim':uretim}
    return JsonResponse(last_data, safe=False, json_dumps_params={'indent': 2})

def presuretimbasla(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            siparis_kimlik = data.get('kimlik')
            kalip_no = data.get('kalip_no')

            siparis = SiparisList.objects.using('dies').filter(Kimlik=siparis_kimlik).first()
            if siparis:
                # pres_u = PresUretimTakip.objects.create(
                #     siparis_kimlik = siparis_kimlik,
                #     kalip_no = kalip_no,
                #     baslangic_datetime = datetime.datetime.now(),
                #     pres_kodu = siparis.PresKodu,
                # )
                kalip = DiesLocation.objects.get(kalipNo=kalip_no)
                pres_u_id = 2
                # Hareket.objects.create(
                #     kalipKonum_id=kalip.kalipVaris.id,
                #     kalipVaris_id=presler[siparis.PresKodu],
                #     kalipNo=kalip_no,
                #     kimTarafindan_id=request.user.id
                # )
                return JsonResponse({"message": "Üretim başarıyla başlatıldı!", "presuretimid": pres_u_id})
            else:
                return JsonResponse({"message": "Sipariş bulunamadı."})
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'message': 'Bir hata oluştu. Lütfen tekrar deneyin.'})
    return JsonResponse({'message': 'Geçersiz istek metodu.'})

def uretim_get_locations(request):
    cache_key = f'location_data_{request.user.id}'
    data = cache.get(key=cache_key)
    if data is None:  # If not in cache, fetch from DB
        location_tree = location_list(request.user)
        reasons = list(PresUretimRaporu.objects.using('dies')
                       .exclude(HataTuru=None)
                       .values_list('HataTuru', flat=True)
                       .distinct())

        # Cache the data for a reasonable duration
        cache.set(cache_key, {"locations": location_tree, "reasons": reasons}, timeout=60*5)

    return JsonResponse(data, safe=False)

def presuretimbitir(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            siparis_kimlik = data.get('kimlik')
            pres_kodu = data.get('presKodu')
            reason = data.get('reason')
            destination = data.get('destination')
            
            takip = PresUretimTakip.objects.filter(siparis_kimlik=siparis_kimlik, pres_kodu=pres_kodu).first()
            if takip:
                kalip = DiesLocation.objects.get(kalipNo=takip.kalip_no)
                Hareket.objects.create(
                    kalipKonum_id=kalip.kalipVaris.id,
                    kalipVaris_id=presler[pres_kodu],
                    kalipNo=takip.kalip_no,
                    kimTarafindan_id=request.user.id
                )
                takip.bitis_datetime = datetime.datetime.now()
                takip.finish_reason = reason
                takip.destination_id = destination
                takip.save()
            return JsonResponse({"message": "Üretim başarıyla bitirildi!"})
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'message': 'Bir hata oluştu. Lütfen tekrar deneyin.'})
    return JsonResponse({'message': 'Geçersiz istek metodu.'})

class eksiparisDenemeView(generic.TemplateView):
    template_name = 'ArslanTakipApp/eksiparisdeneme.html'

def checkKalip(id):
    ek_siparis_instance = EkSiparis.objects.get(id=id)
    return ek_siparis_instance.production_started()

def check_eksiparis(request):
    user_id = request.user.id 
    user_pres_dict = {1: '4500-1', 2: '4500-1'}  # Example mapping; adjust as needed
    pres_grubu = user_pres_dict.get(user_id)
    # her kullanıcı için mapping yerine kullanıcılara grup ata ona göre filtrele
    exists = EkSiparis.objects.filter(PresGrubu=pres_grubu, Aktif=True).exists()

    return JsonResponse({'exists': exists})

def eksiparis_get_data(request):
    params = json.loads(unquote(request.GET.get('params')))
    size = params["size"]
    page = params["page"]
    filter_list = params["filter"]
    offset, limit = calculate_pagination(page, size)
    uretim_kalip_firin(request)
    
    user_id = request.user.id
    user_pres_dict = {1: '4500-1', 2: '4500-1'}
    pres_grubu = user_pres_dict[user_id]
    
    siparis_query = SiparisList.objects.using('dies').filter(
        Adet__gt=0, KartAktif=1, BulunduguYer__in=['DEPO', 'TESTERE']
    ).only('Kimlik', 'Kg', 'PlanlananMm', 'Siparismm', 'FirmaAdi', 'KondusyonTuru', 'SonTermin')

    eksiparis_query = EkSiparis.objects.all()
    pres_eksiparis = eksiparis_query.filter(PresGrubu=pres_grubu, Aktif=True).exclude(MsSilindi=True)

    if pres_eksiparis.exists():
        pres_eksiparis_paginate = list(pres_eksiparis.values()[offset:limit])
        siparis_kimliks = {e['Kimlik'] for e in pres_eksiparis_paginate}
        siparis_dict = {s.Kimlik: s for s in siparis_query.filter(Kimlik__in=siparis_kimliks)}
        ek_siparis_dict = {ek.id: ek for ek in eksiparis_query.filter(id__in=[e['id'] for e in pres_eksiparis_paginate])}

        if pres_eksiparis_paginate:
            first_e = pres_eksiparis_paginate[0]
            pKodu = first_e['PresKodu']
            presId = presler.get(pKodu)
            firinId = firinlar.get(pKodu)
            pres = Location.objects.filter(id=presId).first()
            location_data = DiesLocation.objects.filter(kalipVaris=pres) if pres else []
            gozler = Location.objects.filter(locationRelationID=firinId) if firinId else []
            kalipList = DiesLocation.objects.filter(kalipVaris__in=gozler).values_list('kalipNo', flat=True)
            kaliplar = KalipMs.objects.using('dies').filter(KalipNo__in=list(kalipList), ProfilNo__in=[e['ProfilNo'] for e in pres_eksiparis_paginate]).values_list('KalipNo', flat=True)
            if pres:
                location = location_data.first()
                
        for e in pres_eksiparis_paginate:
            sip = siparis_dict.get(e['Kimlik'])
            if not sip:
                a = ek_siparis_dict.get(e['id'])
                if a and not a.MsSilindi:
                    a.MsSilindi = True
                    a.save()
                pres_eksiparis_paginate.remove(e)
                continue
            
            kalip_sokme_durum = 2 # default 2 BOŞ
            if location:
                die = KalipMs.objects.using('dies').filter(KalipNo=location.kalipNo, ProfilNo=e['ProfilNo']).first()
                if die:
                    kalip_sokme_durum = 1  # üretimi bitir
                elif kaliplar:
                    kalip_sokme_durum = 4  # Kalıp exists in Gözler
            elif kaliplar:
                kalip_sokme_durum = 3  # Kalıp exists in Fırında, start production

            e.update({
                'KartNo': f"{e['KartNo']}-{e['EkNo']}",
                'Termin': format_date(e['Termin']),
                'KalanSiparisKg': sip.Kg,
                'PlanlananMm': sip.PlanlananMm,
                'Mm': sip.Siparismm,
                'FirmaAdi': sip.FirmaAdi,
                'KondusyonTuru': sip.KondusyonTuru,
                'SonTermin': format_date(sip.SonTermin),
                'UretimDurum': checkKalip(e['id']),
                'KalipSokmeDurum': kalip_sokme_durum,
            })
    
    else:
        pres_eksiparis = siparis_query.filter(PresKodu=pres_grubu)
        pres_eksiparis_paginate = list(pres_eksiparis.values()[offset:limit])

        for s in pres_eksiparis_paginate:
            s.update({
                'SonTermin': format_date(s['SonTermin']),
                'KalanKg': s['Kg'],
                'KalanAdet': s['Adet'],
                'Mm': s['Siparismm'],
            })

    ek_count = pres_eksiparis.count()
    last_data = {'last_page': math.ceil(ek_count / size), 'data': pres_eksiparis_paginate}

    return JsonResponse(last_data, safe=False, json_dumps_params={'indent': 2})

def eksiparis_save_data(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        is_siparis_list = data.get('isSiparisList', False)
        items = data.get('data', [])
        fark = data.get('fark', [])
        silinenler = data.get('silinenler', [])
        
        pres_grubu = '4500-1'
        e = EkSiparis.objects.filter(PresGrubu=pres_grubu, Aktif=True)

        if is_siparis_list:
            # Handle SiparisList data
            for item in items:
                kimlik = item.get('Kimlik')
                if kimlik in silinenler:
                    # Skip items marked for deletion
                    continue
                siparis = SiparisList.objects.using('dies').filter(Kimlik=item.get('Kimlik')).first()
                if siparis:
                    eksiparis = EkSiparis()
                    if not e.filter(KartNo = item.get('KartNo')):
                        eksiparis.EkNo = 1
                    else: 
                        lastEk = e.filter(KartNo = item.get('KartNo')).order_by('EkNo').latest('EkNo')
                        eksiparis.EkNo = lastEk.EkNo +1
                    eksiparis.KartNo = item.get('KartNo')
                    eksiparis.Kimlik = item.get('Kimlik')
                    eksiparis.ProfilNo = item.get('ProfilNo')
                    eksiparis.PresKodu = item.get('PresKodu')
                    eksiparis.KimTarafindan = request.user
                    eksiparis.Termin = datetime.datetime.strptime(item.get('SonTermin'), '%d-%m-%Y').strftime('%Y-%m-%d')
                    eksiparis.BilletTuru = item.get('BilletTuru')
                    eksiparis.Kg = item.get('KalanKg')
                    eksiparis.Adet = item.get('KalanAdet')
                    eksiparis.YuzeyOzelligi = item.get('YuzeyOzelligi')
                    eksiparis.PresGrubu = pres_grubu
                    eksiparis.Aktif = True
                    eksiparis.Sira = e.count()+1
                    eksiparis.save()
        else:
            # Handle EkSiparis data
            for item in items:
                eksiparis_id = item.get('id')
                if eksiparis_id in silinenler:
                    # Update Silindi field for deleted items
                    eksiparis = EkSiparis.objects.filter(id=eksiparis_id).first()
                    if eksiparis:
                        eksiparis.Silindi = True
                        eksiparis.save()
                else:
                    eksiparis = EkSiparis.objects.filter(id=item.get('id')).first()
                    if not eksiparis:
                        eksiparis = EkSiparis()
                    eksiparis.PresKodu = item.get('PresKodu')
                    eksiparis.Termin = datetime.datetime.strptime(item.get('Termin'), '%d-%m-%Y').strftime('%Y-%m-%d')
                    eksiparis.Kg = item.get('EkKg')
                    eksiparis.Adet = item.get('EkAdet')
                    eksiparis.BilletTuru = item.get('EkBilletTuru')
                    eksiparis.YuzeyOzelligi = item.get('YuzeyOzelligi')
                    for f in fark:
                        print(f"f:{f}")
                        ek = EkSiparis.objects.get(id=f['id'])
                        ek.Sira = f['Sira']
                        ek.save()
                    eksiparis.save()
        
        return HttpResponse(status=200)
    
    return HttpResponse(status=400)

def eksiparis_list(request):
    params = json.loads(unquote(request.GET.get('params')))
    size = params["size"]
    page = params["page"]
    filter_list = params["filter"]
    offset, limit = calculate_pagination(page, size)
    
    q={}
    w={}
    sipFields = ["ProfilNo", "FirmaAdi", "GirenKg", "Kg", "GirenAdet", "Adet", "PlanlananMm", "Mm", "KondusyonTuru", "SiparisTamam", "SonTermin", "BilletTuru", "TopTenKg"]

    if len(filter_list)>0:
        for i in filter_list:
            if i['field'] in sipFields:
                w = filter_method(i, w)
            else:
                q = filter_method(i, q)
    ekSiparis = EkSiparis.objects.filter(**q).exclude(MsSilindi = True).exclude(Silindi = True).order_by("Sira")
    siparis = SiparisList.objects.using('dies').filter(Adet__gt=0, KartAktif=1, BulunduguYer__in=['DEPO', 'TESTERE']).annotate(
        AktifKalip=Subquery(
            KalipMs.objects.filter(
                ProfilNo=OuterRef('ProfilNo'), AktifPasif='Aktif', Hatali=False, TeniferKalanOmurKg__gte=0
            ).values('ProfilNo').annotate(count_die=Count('KalipNo')).values('count_die')
        )
    ).filter(**w).order_by('Kimlik')

    sip_filter = list(siparis.values_list('Kimlik', flat=True))
    ek_siparis_list = list(ekSiparis.filter(Kimlik__in=sip_filter)[offset:limit].values())

    for e in ek_siparis_list:
        siparis1 = siparis.get(Kimlik=e['Kimlik'])
        e['EkTermin'] = format_date(e['Termin'])
        e['SipKartNo'] = f"{e['KartNo']}-{e['EkNo']}"
        e['KimTarafindan'] = get_user_full_name(int(e['KimTarafindan_id']))
        e.update({
            'FirmaAdi': siparis1.FirmaAdi,
            'GirenKg': siparis1.GirenKg,
            'Kg': siparis1.Kg,
            'GirenAdet': siparis1.GirenAdet,
            'Adet': siparis1.Adet,
            'PlanlananMm': siparis1.PlanlananMm,
            'Mm': siparis1.Siparismm,
            'KondusyonTuru': siparis1.KondusyonTuru,
            'SiparisTamam': siparis1.SiparisTamam,
            'SonTermin': format_date(siparis1.SonTermin),
            'AktifKalip': siparis1.AktifKalip,
            'KalipSokmeDurum': kalipPresCheck(e['id']),
            'UretimDurum' : checkKalip(e['id']), 
        })
    ek_count = ekSiparis.count()
    lastData= {'last_page': math.ceil(ek_count/size), 'data': []}
    lastData['data'] = ek_siparis_list
    data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

def eksiparis_acil(request): # planlama listesi düzenleme
    siparis = SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')).extra(
        select={
            "TopTenKg": "(SELECT SUM(TeniferKalanOmurKg) FROM View020_KalipListe WHERE (View020_KalipListe.ProfilNo = View051_ProsesDepoListesi.ProfilNo AND View020_KalipListe.AktifPasif='Aktif' AND View020_KalipListe.Hatali=0 AND View020_KalipListe.TeniferKalanOmurKg>= 0))",
            "AktifKalipSayisi":"(SELECT COUNT(KalipNo) FROM View020_KalipListe WHERE (View020_KalipListe.ProfilNo = View051_ProsesDepoListesi.ProfilNo AND View020_KalipListe.AktifPasif='Aktif' AND View020_KalipListe.Hatali=0 AND View020_KalipListe.TeniferKalanOmurKg>= 0))",
            "ToplamKalipSayisi":"(SELECT COUNT(KalipNo) FROM View020_KalipListe WHERE (View020_KalipListe.ProfilNo = View051_ProsesDepoListesi.ProfilNo AND View020_KalipListe.AktifPasif='Aktif' AND View020_KalipListe.Hatali=0))"
        },
    )

    ekSiparis = EkSiparis.objects.order_by("Sira").exclude(MsSilindi = True).exclude(Silindi=True)
    ekSiparisList = list(ekSiparis.values())

    for e in ekSiparisList:
        if siparis.filter(Kimlik = e['Kimlik']).exists() == False :
            a = ekSiparis.get(SipKimlik = e['Kimlik'], EkNo = e['EkNo'])
            if a.MsSilindi != True:
                a.MsSilindi = True
                a.save()
            ekSiparisList.remove(e)
        else:
            siparis1 = siparis.get(Kimlik = e['Kimlik'])
            e['EkTermin'] = format_date(e['Termin'])
            e['SipKartNo'] = str(e['KartNo']) + "-" +str(e['EkNo'])
            e['KimTarafindan'] = get_user_full_name(int(e['KimTarafindan_id']))
            if siparis1:
                e['ProfilNo'] = siparis1.ProfilNo
                e['FirmaAdi'] = siparis1.FirmaAdi
                e['GirenKg'] = siparis1.GirenKg
                e['Kg'] = siparis1.Kg
                e['GirenAdet'] = siparis1.GirenAdet
                e['Adet'] = siparis1.Adet
                e['PlanlananMm'] = siparis1.PlanlananMm
                e['Mm'] = siparis1.Siparismm
                e['KondusyonTuru'] = siparis1.KondusyonTuru
                e['SiparisTamam'] = siparis1.SiparisTamam
                e['SonTermin'] = format_date(siparis1.SonTermin)
                e['BilletTuru'] = siparis1.BilletTuru
                e['TopTenKg'] = siparis1.TopTenKg

    if request.method == "GET":
        lastData= []
        lastData = ekSiparisList
        data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
        return HttpResponse(data)
    elif request.method == "POST":
        fark = request.POST['fark']
        fark = json.loads(fark)
        silinenler = json.loads(request.POST['silinenler'])
        for s in silinenler:
            sil = EkSiparis.objects.get(id=s)
            sil.Silindi = True
            sil.save()
            #Silindi True olsun MsSilindi exclude yapılırken bunu da excludela 

        for f in fark:
            ek = EkSiparis.objects.get(id=f['id'])
            ek.Sira = f['Sira']
            ek.save()
        return HttpResponseRedirect("/eksiparis")

class KalipFirinView(PermissionRequiredMixin, generic.TemplateView):
    permission_required = "ArslanTakipApp.kalipEkran_view_location"
    template_name = 'ArslanTakipApp/kalipFirinEkrani.html'

    def get(self, request, *args, **kwargs):
        if self.request.user.is_superuser:
            raise PermissionDenied("Superuserların sayfayı kullanımı yasaktır.")
        
        context = self.get_context_data(**kwargs)  # Assuming get_context_data is properly setting up the context
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loc = get_objects_for_user(self.request.user, "ArslanTakipApp.goz_view_location", klass=Location)
        loc_list = list(loc.values('id', 'locationName'))
        loc_list.sort(key=lambda x: int(re.search(r'\d+', x['locationName']).group()))

        gozler = {l['locationName']: [] for l in loc_list}
        gozKalip = DiesLocation.objects.filter(kalipVaris__in=loc).select_related('kalipVaris')
        
        for kalip in gozKalip:
            gozler[kalip.kalipVaris.locationName].append({
                'kalipNo': kalip.kalipNo,
                'hareketTarihi': DateFormat(kalip.hareketTarihi).format('Y-m-d H:i:s'),
                'locationName': kalip.kalipVaris.locationName,
            })
        gozData = [{'locationName': k, 'kalıplar': v} for k, v in gozler.items() if v]

        total_locations = len(gozler)
        context['totalLocations'] = total_locations
        context['gozData'] = gozData

        return context
    
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.is_superuser:
            return JsonResponse({"error": "Unauthorized access."}, status=403)
        
        try:
            data = request.POST
            kalipNo = data['kalipNo']
            firinGoz = data['firinNo']

            if not kalipNo or not firinGoz:
                return JsonResponse({"error": "Missing required data."}, status=400)
            
            loc = get_objects_for_user(self.request.user, "ArslanTakipApp.goz_view_location", klass=Location)
            gonder = loc.get(locationName__contains=firinGoz)
            gozCapacity = gonder.capacity

            if gozCapacity == None:
                k = DiesLocation.objects.get(kalipNo = kalipNo)
                if k.kalipVaris.id != gonder:
                    hareket = Hareket()
                    hareket.kalipKonum_id = k.kalipVaris.id
                    hareket.kalipVaris_id = gonder.id
                    hareket.kalipNo = kalipNo
                    hareket.kimTarafindan_id = request.user.id
                    hareket.save()
                    response = JsonResponse({"message": "Kalıp Fırına Eklendi!"})
                else:
                    response = JsonResponse({"error": "Kalıp fırına gönderilemedi."}, status=400)
                return response
            else:
                firinKalipSayisi = DiesLocation.objects.filter(kalipVaris_id = gonder.id).count()
                if firinKalipSayisi < gozCapacity:
                    k = DiesLocation.objects.get(kalipNo = kalipNo)
                    if k.kalipVaris.id != gonder:
                        hareket = Hareket()
                        hareket.kalipKonum_id = k.kalipVaris.id
                        hareket.kalipVaris_id = gonder.id
                        hareket.kalipNo = kalipNo
                        hareket.kimTarafindan_id = request.user.id
                        hareket.save()
                        response = JsonResponse({"message": "Kalıp Fırına Eklendi!"})
                    else:
                        response = JsonResponse({"error": "Kalıp fırına gönderilemedi."}, status=400)
                    return response
                else:
                    response = JsonResponse({"error": "Fırın kalıp kapasitesini doldurdu, kalıp eklenemez!"})
                    response.status_code = 500
                    
            firinKalipSayisi = DiesLocation.objects.filter(kalipVaris=gonder).count()
            if firinKalipSayisi < gozCapacity:
                return self.infoBoxEkle(kalipNo, gonder.id, request)
            else:
                return JsonResponse({"error": "Capacity full, cannot add more dies."}, status=400)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        
    def infoBoxEkle(self, kalipNo, gonderId, request):
        k = DiesLocation.objects.get(kalipNo=kalipNo)
        if k.kalipVaris.id != gonderId:
            Hareket.objects.create(
                kalipKonum_id=k.kalipVaris.id,
                kalipVaris_id=gonderId,
                kalipNo=kalipNo,
                kimTarafindan_id=request.user.id
            )
            return JsonResponse({"message": "Die successfully added to the furnace."})
        return JsonResponse({"error": "Failed to add die to the furnace."}, status=500)
  
def kalipfirini_meydan(request):
    params = json.loads(unquote(request.GET.get('params')))
    size = params["size"]
    page = params["page"]
    filter_list = params.get("filter", [])
    offset, limit = calculate_pagination(page, size)

    loc = get_objects_for_user(request.user, "ArslanTakipApp.meydan_view_location", klass=Location)
    
    if not request.user.is_superuser:
        loc_id = loc.get(locationName__contains = "MEYDAN").id
        meydanKalip = DiesLocation.objects.filter(kalipVaris_id = loc_id).order_by('kalipNo')
    else:
        loc_list = list(loc.values())
        locs = [l['id'] for l in loc_list]
        meydanKalip = DiesLocation.objects.filter(kalipVaris_id__in = locs).order_by('kalipNo')

    q = {}
    if len(filter_list) > 0:
        for i in filter_list:
            q = filter_method(i, q)
    meydanData = list(meydanKalip.filter(**q).values('kalipNo')[offset:limit])

    meydan_count = meydanKalip.count()
    lastData= {'last_page': math.ceil(meydan_count/size), 'data': []}
    lastData['data'] = meydanData
    data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

class BaskiGecmisiView(generic.TemplateView):
    template_name = 'ArslanTakipApp/baskiGecmisi.html'

def baskigecmisi_list(request):
    params = json.loads(unquote(request.GET.get('params')))
    for i in params:
        value = params[i]
        print("Key and Value pair are ({}) = ({})".format(i, value))
    size = params["size"]
    page = params["page"]
    offset, limit = calculate_pagination(page, size)
    filter_list = params["filter"]
    q= {}

    baskiL = ["MakineKodu", "Start", "Stop", "Events"]

    #filterlist şeklinde olan filterlar eklenecek
    baskiQS = LivePresFeed.objects.filter(Events = "extrusion").order_by('-id')
    if len(filter_list) > 0:
        for i in filter_list:
            if not i["field"] in baskiL:
                i["field"] = "Parameters__" + i["field"]
            q = filter_method(i, q)
            
    baskiList = list(baskiQS.filter(**q).values()[offset:limit])

    for b in baskiList:
        b['Start'] = format_date_time_s(b['Start'])
        b['Stop'] = format_date_time_s(b['Stop'])
        b['BilletCount'] = b['Parameters']['billetCount']
        b['dieNumber'] = b['Parameters']['dieNumber']
        b['extTime'] = b['Parameters']['extTime']
        b['stroke'] = b['Parameters']['stroke']
        b['peakPreassure'] = b['Parameters']['peakPreassure']
        b['extSpeed'] = b['Parameters']['extSpeed']
        b['billetTempOK'] =b['Parameters']['billetTempOK']
        b['billetRequestTime'] =b['Parameters']['billetRequestTime']
        b['billetLength'] = b['Parameters']['billetLength']
        try:
            b['timeLoss'] = b['Parameters']['timeLoss']
        except:
            b['timeLoss'] = None
        

    baski_count = baskiQS.count()
    lastData= {'last_page': math.ceil(baski_count/size), 'data': []}
    lastData['data'] = baskiList
    data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)


class HammaddeBilletView(generic.TemplateView):
    template_name = 'ArslanTakipApp/hammaddebillet.html'

def get_transfer_billets(request):
    one_week = timezone.now() - timezone.timedelta(days=7)
    billet_kimlikler = BilletDepoTransfer.objects.using('dies').filter(Create_Time__gte=one_week, GirenDepoKodu='4.FAB.PRES.').values_list('Kimlik', flat=True)
    hammadde_kimlikler = HammaddeBilletStok.objects.filter(kayit_tarihi__gte=one_week).values_list('gelen_kimlik', flat=True)

    available_kimlikler = set(billet_kimlikler) - set(hammadde_kimlikler)
    transfer_info = list(BilletDepoTransfer.objects.using('dies').filter(Kimlik__in=available_kimlikler).values(
        'Kimlik', 'Create_Time', 'GirenPartiNo', 'GirenBoy', 'GirenAdet', 'GirenKg', 'GirenDepoKodu', 'StokCinsi', 'Aciklama'
    ))

    for s in transfer_info:
        s['Create_Time']=format_date(s['Create_Time'])
    
    if transfer_info:
        return JsonResponse(transfer_info, safe=False)
    else:
        return JsonResponse({"error": "Billet information not found"}, status=404)
    
def get_stok_billets(request):
    stok_info = list(HammaddeBilletStok.objects.values().exclude(adet = 0))
    for item in stok_info:
        item['firin_aktif'] = HammaddeBilletCubuk.objects.filter(stok_id=item['id']).exclude(sira = 0).count()
        item['firin_pasif'] = HammaddeBilletCubuk.objects.filter(stok_id=item['id'], sira=0).count()

    if stok_info:
        return JsonResponse(stok_info, safe=False)
    else:
        return JsonResponse({"error": "Stok information not found"}, status=404)

def get_firin_billets(request):
    firin_info = list(HammaddeBilletCubuk.objects.values().exclude(sira = 0).order_by('sira'))
    for f in firin_info:
        stok_info = HammaddeBilletStok.objects.get(id=f["stok_id"])
        f['parti_no'] = stok_info.parti_no
        f['billet_cinsi'] = stok_info.stok_cinsi
    if firin_info:
        return JsonResponse(firin_info, safe=False)
    else:
        return JsonResponse({"error": "Fırın information not found"}, status=404)
    
def save_hammadde_billets(request):
    if request.method == 'POST':
        kimlik = int(request.POST.get('Kimlik'))
        print(kimlik)

        try:
            transfer = BilletDepoTransfer.objects.using('dies').filter(Kimlik=kimlik).values('GirenPartiNo', 'GirenBoy', 'GirenAdet', 'GirenKg', 'StokCinsi', 'Aciklama', 'Kimlik')[0]
            print(transfer)
            HammaddeBilletStok.objects.create(
                parti_no=transfer['GirenPartiNo'],
                boy=transfer['GirenBoy']*10,
                adet=transfer['GirenAdet'],
                kg=transfer['GirenKg'],
                stok_cinsi=transfer['StokCinsi'],
                aciklama=transfer['Aciklama'],
                gelen_kimlik=kimlik,
                konum_id=1102
            )

            return JsonResponse({'success': True, 'message': 'Hammadde eklendi.'})
        except HammaddeBilletStok.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'id not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
        
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

def billet_firina_at(request):
    if request.method == 'POST':
        stok_id = request.POST.get('id')
        adet = int(request.POST.get('adet'))

        try:
            stok_info = HammaddeBilletStok.objects.get(id=stok_id)
            last_billet = HammaddeBilletCubuk.objects.filter(stok=stok_info).order_by('-sira').first()
            next_sira = (last_billet.sira + 1) if last_billet else 1
            
            last_billet_parti_no = HammaddeBilletCubuk.objects.filter(parti_no=stok_info.parti_no).order_by('-sira').first()
            if last_billet_parti_no:
                last_billet_no = last_billet_parti_no.billet_no
                last_number = int(last_billet_no.split('-')[-1])
                next_number = last_number + 1
            else:
                next_number = 1

            for i in range(adet):
                HammaddeBilletCubuk.objects.create(
                    billet_no=f"{stok_info.parti_no}-{next_number + i}",
                    stok=stok_info,
                    parti_no=stok_info.parti_no,
                    guncel_boy=stok_info.boy,
                    sira=next_sira + i,
                    tarih=datetime.datetime.now()
                )

            stok_info.adet -= adet  # adet değiştiğinde kgde değişmeli (adet*boy*1.367 mi?)
            stok_info.kg = stok_info.adet * stok_info.boy * 1.367
            stok_info.save()
            return JsonResponse({'success': True, 'message': 'Fırına atıldı.'})
        except HammaddeBilletStok.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'id not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

class YudaView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'ArslanTakipApp/yuda2.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if the user is a member of either group
        is_in_group = (
            self.request.user.groups.filter(name="Yurt Disi Satis Bolumu").exists() or
            self.request.user.groups.filter(name="Yurt Ici Satis Bolumu").exists()
        )
        # Add the is_in_group variable to the context
        context['is_in_group'] = is_in_group
        return context

#for getting the select options 
@login_required
def yuda(request, objId):
    try: 
        int(objId)
        allParams = Parameter.objects.all()
        parameters = list(allParams.filter(ParentId = objId).values())
    except:
        allParams = Parameter.objects.all()
        parameters = list(allParams.filter(Tag = objId).values())

    data = json.dumps(parameters, indent=1)
    return HttpResponse(data)

def yuda_profil(request):
    query = request.GET.get('query', '')  # Get the search term
    profiles = ProfilMs.objects.using('dies').filter(ProfilNo__startswith=query).values('Kimlik', 'ProfilNo')[:200]  # Limit to 200 results for performance
    
    profiles_data = [{'id': profile['ProfilNo'], 'name': profile['ProfilNo']} for profile in profiles]
    
    return JsonResponse({'profiles': profiles_data})

def yuda_kaydet(request):
    if request.method == "POST":
        for attempt in range(3):
            try:
                today = datetime.datetime.now().strftime('%j')
                year = datetime.datetime.now().strftime('%y')
                with transaction.atomic():
                    lastOfDay = YudaForm.objects.filter(YudaNo__startswith=year + '-' + today).select_for_update(skip_locked=True).order_by('-YudaNo').first() # select for update
                    if lastOfDay:
                        # Extract the sequential number part from the latest YudaNo and increment it
                        latest_seq_number = int(lastOfDay.YudaNo[-2:]) + 1
                        sequential_number = f'{latest_seq_number:02}'  # Convert to two-digit string
                    else:
                        # If no YudaNo exists for today, start from 01
                        sequential_number = '01'
                    
                    y = YudaForm()
                    y.YudaNo = f'{year}-{today}-{sequential_number}' #year+"-"+today+"-NN"
                    y.ProjeYoneticisi = User.objects.get(id=44) # proje yöneticisi harun bey olacak
                    y.YudaAcanKisi = request.user
                    y.Tarih = datetime.datetime.now()
                    y.OnayDurumu = 'Kalıphane Onayı Bekleniyor'
                    
                    is_old_profile = False # if True: Kalıphane bolumu Onay oyu versin
                    has_mekanik = 0 # mekanik işlem yok
                    yetki_group = "" 
                    for key, value in request.POST.items():
                        if hasattr(y, key):
                            if key == "BirlikteCalisan":
                                value_list = value.split(',')
                                setattr(y, key, value_list)
                            else:
                                setattr(y, key, value)
                                if key == "TalasliImalat" and value == "Var":
                                    has_mekanik = 1
                        if key == "Yetki":
                            yetki_group = value
                        elif key == "ProjeTipi" or key == "MevcutProfil":
                            if y.meta_data is None:
                                y.meta_data = {}
                            y.meta_data[key] = value
                            if key == "ProjeTipi" and value == "Mevcut Profil":
                                is_old_profile = True
                    if is_old_profile:
                        durumlar = {'kaliphane': 2, 'mekanik': has_mekanik, 'satis': 1}
                        onay_durumu = determine_onay_durumu(durumlar)
                        y.OnayDurumu = onay_durumu
                            
                    y.save()

                    group_names = [
                        'Ust Yonetim Bolumu',
                        'Planlama Bolumu',
                        'Kalite Bolumu',
                        'Kaliphane Bolumu',
                        'Pres Bolumu',
                        'Yurt Disi Satis Bolumu',
                        'Yurt Ici Satis Bolumu',
                        'Proje Bolumu',
                    ]

                    group_mapping = {
                        'Paketleme': 'Paketleme Bolumu',
                        'YuzeyEloksal': 'Eloksal Bolumu',
                        'YuzeyAhsap': 'Ahsap Kaplama Bolumu',
                        'YuzeyBoya': 'Boyahane Bolumu',
                        'TalasliImalat': 'Mekanik Islem Bolumu',
                    }

                    groups = [Group.objects.get(name=name) for name in group_names]

                    assign_perm("gorme_yuda", request.user, y) # Assign permission to the current user
                    assign_perm("acan_yuda", request.user, y) # Yudayı açan kişiye değiştirme ve görme yetkisi ver
                    
                    if y.MusteriFirmaAdi != "DENEME":
                        assign_perm("gorme_yuda", y.ProjeYoneticisi, y) # Assign permission to the current user
                        assign_perm("acan_yuda", y.ProjeYoneticisi, y) # Assign permission to the current user
                        for group in groups: #groups içinde olanların hepsinin bütün projeleri görme yetkisi var
                            if group.name == "Yurt Ici Satis Bolumu" or group.name == "Yurt Disi Satis Bolumu":
                                if group in request.user.groups.all():
                                    assign_perm("gorme_yuda", group, y)
                                if yetki_group == group.name:
                                    assign_perm("gorme_yuda", group, y)
                            else:
                                assign_perm("gorme_yuda", group, y)

                        # Check field values and assign permissions based on conditions
                        for field in y._meta.fields:
                            fname = field.name
                            fvalue = getattr(y, fname)
                            if fname in group_mapping and fvalue is not None and fvalue != "" and fname != "TalasliImalat" and fname != "Paketleme":
                                group = Group.objects.get(name=group_mapping[fname])
                                assign_perm("gorme_yuda", group, y)
                            if fname == "TalasliImalat" and fvalue == "Var":
                                group = Group.objects.get(name=group_mapping[fname])
                                assign_perm("gorme_yuda", group, y)
                            if fname == "Paketleme" and fvalue == "Ozel Paketleme":
                                group = Group.objects.get(name=group_mapping[fname])
                                assign_perm("gorme_yuda", group, y)

                    if is_old_profile:
                        YudaOnay.objects.create(
                            Group=Group.objects.get(name='Kaliphane Bolumu'),
                            Yuda_id=y.id,
                            OnayDurumu=True
                        )

                        mevcut_profil = y.meta_data['MevcutProfil']
                        profil=f"'{mevcut_profil}' numaralı mevcut profil"
                        if ',' in y.meta_data['MevcutProfil']:
                            mevcut_profil = mevcut_profil.replace(",", "', '")
                            profil=f"'{mevcut_profil}' numaralı mevcut profiller"

                        Comment.objects.create(
                            Kullanici_id = 57,
                            FormModel = "YudaForm",
                            FormModelId = y.id,
                            Tarih = datetime.datetime.now(),
                            Aciklama = f"Yeni proje, {profil} için açıldığından, sistem tarafından otomatik olarak Kalıphane onayı verilmiştir."
                        )

                    # Dosyaları ve başlıkları işleyin
                    file_titles = request.POST.getlist('fileTitles[]')
                    for file, title in zip(request.FILES.getlist('files[]'), file_titles):
                        UploadFile.objects.create(
                            File = file,
                            FileTitle = title,
                            FileSize = file.size,
                            FileModel = "YudaForm",
                            FileModelId = y.id,
                            UploadedBy = y.ProjeYoneticisi,
                            Note = "",
                        )
                    
                    # for user in User.objects.exclude(id=request.user.id):
                    allowed_groups = [group for group, perms in get_groups_with_perms(y, attach_perms=True).items() if 'gorme_yuda' in perms]

                    if request.user.id != 1:
                        for u in User.objects.filter(groups__in=allowed_groups).exclude(id=request.user.id):
                            notification = Notification.objects.create(
                                user=u,
                                message=f'{y.MusteriFirmaAdi[:11]}.. için bir YUDA ekledi.',
                                subject=f"Yeni YUDA",
                                where_id=y.id,
                                new_made_by = request.user,
                                col_marked = "#E9ECEF",
                            )
                            logger.debug(f"YUDA Notification is created. ID: {notification.id}, Time: {notification.timestamp.strftime('%d-%m-%y %H:%M')}")
                        
                            channel_layer = get_channel_layer()
                            async_to_sync(channel_layer.group_send)(
                                f'notifications_{request.user.id}',
                                {
                                    'type': 'send_notification',
                                    'notification': {
                                        'id': notification.id,
                                        'subject': notification.subject,
                                        'made_by': get_user_full_name(notification.new_made_by_id),
                                        'message': notification.message,
                                        'where_id': notification.where_id,
                                        'is_read': notification.is_read,
                                        'timestamp': notification.timestamp.strftime('%d-%m-%y %H:%M'),
                                        'is_marked': notification.is_marked,
                                    },
                                }
                            )
                            logger.debug(f"YUDA Notification is sent. ID: {notification.id}, Time: {notification.timestamp.strftime('%d-%m-%y %H:%M')}")
                        

                return JsonResponse({'message': 'Kayıt başarılı', 'id': y.id})
            except json.JSONDecodeError:
                response = JsonResponse({'error': 'Geçersiz JSON formatı'})
                response.status_code = 500 #server error
                break
            except IntegrityError:
                time.sleep(0.1)
                continue
            except Exception as e:
                response = JsonResponse({'error': str(e)})
                response.status_code = 500 #server error
                break

    return response
        
class YudasView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'ArslanTakipApp/yudaList.html'

def yuda_filter(i):
    q = {}
    if i['field'] == 'Islem': # eski adı bölüm, işlem var mı kontrol etmek için
        for islem in i['value']:
            if islem == 'Boya':
                q['YuzeyBoya__gt'] = ""
            elif islem == 'Eloksal':
                q['YuzeyEloksal__gt'] = ""
            elif islem == 'Mekanik Islem':
                q['TalasliImalat__exact'] = 'Var'  # Filter where TalasliImalat is 'Var'
    elif i['field']  == 'Dosya':
        file_ids = UploadFile.objects.filter(File__icontains=i['value']).values_list('FileModelId', flat=True)
        q['id__in'] = list(file_ids)
    elif i['field'] == 'Tarih' or i['field'] == 'GüncelTarih': #type = start date, value=finish date
        if i['type'] != i['value']:
            q[i['field'] + "__gte"] = i['type']
            q[i['field'] + "__lt"] = i['value'] + ' 23:59:59'
        else:
            q[i['field'] + "__startswith"] = i['value']
    else:
        q = filter_method(i, q)
    return q

def bolumOnayFilter(q, val, group):
    if val is not None and group:
        if val == "True":
            q['yudaonay__OnayDurumu'] = True
            q['yudaonay__Group'] = group
        elif val == "False":
            q['yudaonay__OnayDurumu'] = False
            q['yudaonay__Group'] = group
        
    return q

def yudas_list(request):
    params = json.loads(unquote(request.GET.get('params', '{}')))
    for i in params:
        value = params[i]
        # print("Key and Value pair are ({}) = ({})".format(i, value))
    size = params.get("size", 7)  # Default size to 7
    page = params.get("page", 1)  # Default page to 1
    offset, limit = calculate_pagination(page, size)
    filter_list = params.get("filter", [])
    q = {}

    temsilciler = User.objects.filter(Q(groups__name = "Yurt Ici Satis Bolumu") | Q(groups__name = "Yurt Disi Satis Bolumu"))
    temsilci_data = [{'id': user.id, 'full_name': get_user_full_name(user.id)} for user in temsilciler]

    y = get_objects_for_user(request.user, "gorme_yuda", YudaForm.objects.all()) #user görme yetkisinin olduğu yudaları görsün

    if len(filter_list) > 0:
        for i in filter_list:
            if i['type'] == "BolumOnayFilter":
                print(i)
                filter_group = Group.objects.get(name=i['field'])
                if i['value'] == "None": # 
                    y = get_objects_for_group(filter_group, "gorme_yuda", y)
                    y = y.exclude(yudaonay__Group=filter_group)
                else:
                    q = bolumOnayFilter(q, i['value'], filter_group)
            else:
                q = yuda_filter(i)

    y = y.filter(Silindi__isnull = True).filter(**q).order_by('-Tarih', '-YudaNo')
    
    filtered_yudas = y.values()
    yudaList = list(filtered_yudas[offset:limit])

    for o in yudaList:
        o['Tarih'] = format_date_time(o['Tarih'])
        if o['GüncelTarih'] != None:
            o_comment = Comment.objects.filter(FormModel='YudaForm', FormModelId=o['id']).exclude(Silindi=True).order_by('-Tarih').values()[0]
            o_comment_user = get_user_full_name(o_comment['Kullanici_id'])
            o['GüncelTarih'] = o_comment_user + "<br>" + format_date_time_without_year(o['GüncelTarih'])
        else: o['GüncelTarih'] = ""
        o['MusteriTemsilcisi'] = get_user_full_name(int(o['YudaAcanKisi_id']))
        o['durumlar'] = {}
        for group in [group.name.split(' Bolumu')[0] for group, perms in get_groups_with_perms(y.get(id=o['id']), attach_perms=True).items() if perms == ['gorme_yuda'] and group.name != 'Proje Bolumu']:
            yuda_onay = YudaOnay.objects.filter(Yuda=o['id'], Group__name=group+' Bolumu').first()
            if yuda_onay:
                if yuda_onay.OnayDurumu is True:
                    o['durumlar'][group] = 'success'
                elif yuda_onay.OnayDurumu is False:
                    o['durumlar'][group] = 'danger'
            else: o['durumlar'][group] = 'warning'
    
    yudas_count = filtered_yudas.count()
    last_page = math.ceil(yudas_count / size)
    response_data = {
        'last_page' : last_page,
        'data' : yudaList,
        'temsil': temsilci_data
    }
    data = json.dumps(response_data, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

def process_comment(user, comment): #biri parent yorumu silerse reply olan yorum gözükmemiş olur bunu düzelt
    comment_instance = Comment.objects.get(pk=comment['id'])
    views = comment_instance.ViewedUsers.all()
    # görmesi gerekenler kullanıcı grubu oluşturup bu gruptaki herkes görmüş mü kontrol edilsin allViewed = True False
    must_view_user_ids = [1, 2, 29]
    for user_id in must_view_user_ids:
        if user_id not in [view.id for view in views]:
            comment['All_Viewed'] = False
            break
        else: comment['All_Viewed'] = True

    comment['KullaniciAdi'] = get_user_full_name(int(comment['Kullanici_id']))
    comment['Tarih'] = format_date_time(comment['Tarih'])
    comment['Is_Viewed'] = user in views
    comment['cfiles'] = list(getFiles("Comment", comment['id']))
    comment['replies'] = [process_comment(user, comment) for comment in Comment.objects.filter(ReplyTo = comment['id'], Silindi=False).values()] 
    return comment

def format_yuda_details2(yList):
    for i in yList:
        i['Tarih'] = format_date(i['Tarih'])
        if i['AlasimKondusyon'] != '': 
            alasimJson = json.loads(i['AlasimKondusyon'])
            alasim = ""
            Sayac = 0
            for a in alasimJson:
                alasim += "Alaşım: "+ a['Alasim'] + ",  Kondüsyon: "+ a['Kondusyon']
                Sayac += 1
                if Sayac != len(alasimJson):
                    alasim += "; "
            i['AlasimKondusyon'] = alasim

        if i['YuzeyPres'] != '': 
            presJson = json.loads(i['YuzeyPres'])
            Sayac = 0
            pres = ""
            for a in presJson:
                pres += "Yuzey Detay: "+ a['YuzeyDetay'] +",  Boy: "+ a['YuzeyPresBoy']
                Sayac += 1
                if Sayac != len(presJson):
                    pres += "; "
            i['YuzeyPres'] = pres

        if i['YuzeyEloksal'] != '': 
            eloksalJson = json.loads(i['YuzeyEloksal'])
            Sayac = 0
            eloksal = ""
            for a in eloksalJson:
                eloksal += "Matlaştırma: "+ a['Matlastirma'] + ",  Renk: "+ a['Renk'] + ",  Kaplama Kalınlığı: "+ a['KaplamaKalinligi'] +",  Boy: "+ a['EloksalBoy']+ ",  "+ a['EloksalTemizKesim']
                Sayac += 1
                if Sayac != len(eloksalJson):
                    eloksal += "; "
            i['YuzeyEloksal'] = eloksal

        if i['YuzeyBoya'] != '': 
            boyaJson = json.loads(i['YuzeyBoya'])
            Sayac = 0
            boya = ""
            for a in boyaJson:
                boya += "Tür: "+ a['Tur']+ ",  Marka: "+ a['Marka']+ ",  Renk Kodu: "+ a['MarkaRenkKodu']+ ",  Class: "+ a['BoyaClass']+ ",  RAL: "+ a['Ral']+ ",  Kalınlık: "+ a['BoyaKalinlik']+ ",  Boy: "+ a['BoyaBoy']+ ",  "+ a['BoyaTemizKesim']
                Sayac += 1
                if Sayac != len(boyaJson):
                    boya += "; "
            i['YuzeyBoya'] = boya

        if i['YuzeyAhsap'] != '': 
            ahsapJson = json.loads(i['YuzeyAhsap'])
            Sayac = 0
            ahsap = ""
            for a in ahsapJson:
                ahsap += "Ahşap Kaplama: "+ a['AhsapKaplama']+ ",  Boy: "+ a['AhsapBoy']+ ",  "+ a['AhsapTemizKesim']
                Sayac += 1
                if Sayac != len(ahsapJson):
                    ahsap += ";  "
            i['YuzeyAhsap'] = ahsap
    return yList

def process_alasim(alasim):
    return "; <br>".join([f"Alaşım: {item['Alasim']}, Kondüsyon: {item['Kondusyon']}" for item in alasim])

def process_yuzey(json_data, keys, key_names):
    processed_data = []
    for data in json_data:
        details = []
        for key in keys:
            if 'Boy' in key_names[key]:
                details.append(f"{key_names[key]}: {data[key]} mm")
            elif key == 'BoyaKalinlik':
                if 'BoyaKalinlik' in data:
                    details.append(f"{key_names[key]}: {data[key]}")
            else:
                details.append(f"{key_names[key]}: {data[key]}")
        processed_data.append(", ".join(details))
    return "; <br>".join(processed_data)

def format_yuda_details(yList):
    key_name_map = {
        'YuzeyDetay': 'Yuzey Detay', 'YuzeyPresBoy': 'Boy',
        'Matlastirma': 'Matlaştırma', 'Renk': 'Renk', 'KaplamaKalinligi': 'Kaplama Kalınlığı', 'EloksalBoy': 'Boy', 'EloksalTemizKesim': 'Temiz Kesim',
        'Tur': 'Tür', 'Marka': 'Marka', 'MarkaRenkKodu': 'Marka Renk Kodu', 'BoyaClass': 'Boya Class', 'Ral': 'RAL', 'BoyaKalinlik': 'Kalınlık', 'BoyaBoy': 'Boy', 'BoyaTemizKesim': 'Temiz Kesim',
        'AhsapKaplama': 'Ahşap Kaplama', 'AhsapBoy': 'Boy', 'AhsapTemizKesim': 'Temiz Kesim',
    }
    for i in yList:
        i['Tarih'] = format_date(i['Tarih'])
        for key in ['AlasimKondusyon', 'YuzeyPres', 'YuzeyEloksal', 'YuzeyBoya', 'YuzeyAhsap']:
            if i[key]:
                json_data = json.loads(i[key])
                if key == 'AlasimKondusyon':
                    i[key] = process_alasim(json_data)
                elif key == 'YuzeyPres':
                    i[key] = process_yuzey(json_data, ['YuzeyDetay', 'YuzeyPresBoy'], key_name_map)
                elif key == 'YuzeyEloksal':
                    i[key] = process_yuzey(json_data, ['Matlastirma', 'Renk', 'KaplamaKalinligi', 'EloksalBoy', 'EloksalTemizKesim'], key_name_map)
                elif key == 'YuzeyBoya':
                    i[key] = process_yuzey(json_data, ['Tur', 'Marka', 'MarkaRenkKodu', 'BoyaClass', 'Ral', 'BoyaKalinlik', 'BoyaBoy', 'BoyaTemizKesim'], key_name_map)
                elif key == 'YuzeyAhsap':
                    i[key] = process_yuzey(json_data, ['AhsapKaplama', 'AhsapBoy', 'AhsapTemizKesim'], key_name_map)
    return yList

def format_yuda_tab(yD):
    yuda_details = yD[0]
    al = [{"Baslik": "Alaşım ve Kondüsyon", "Icerik": f"Alasim: {item['Alasim']} Kondüsyon: {item['Kondusyon']}"} for item in json.loads(yuda_details['AlasimKondusyon'])]
    
    yp = [{"Baslik": item['YuzeyDetay'], "Icerik": f"Boy: {item['YuzeyPresBoy']}"} for item in json.loads(yuda_details.get('YuzeyPres', '[]'))] if yuda_details['YuzeyPres'] else []
    
    ye = [{"Baslik": 'Eloksal', "Icerik": index + 1, "_children": [{"Baslik": "", "Icerik": value} for key, value in item.items() if key not in ['ID', 'YuzeyDetay']]} for index, item in enumerate(json.loads(yuda_details.get('YuzeyEloksal', '[]')))] if yuda_details['YuzeyEloksal'] else []
    
    yb = [{"Baslik": 'Boya', "Icerik": index + 1, "_children": [{"Baslik": "", "Icerik": value} for key, value in item.items() if key not in ['ID', 'YuzeyDetay']]} for index, item in enumerate(json.loads(yuda_details.get('YuzeyBoya', '[]')))] if yuda_details['YuzeyBoya'] else []
    
    ya = [{"Baslik": 'Ahşap Kaplama', "Icerik": f"{item['AhsapKaplama']} Boy: {item['AhsapBoy']}"} for item in json.loads(yuda_details.get('YuzeyAhsap', '[]'))] if yuda_details['YuzeyAhsap'] else []
    
    data = [
        {"Baslik": "Sipariş", "Icerik": "hh", "_children": [
            {"Baslik": "Müşteri Firma Adı", "Icerik": yuda_details.get('MusteriFirmaAdi', '')},
            {"Baslik": "Son Kullanıcı Firma", "Icerik": yuda_details.get('SonKullaniciFirma', '')},
            {"Baslik": "Kullanım Alani", "Icerik": yuda_details.get('KullanimAlani', '')},
            {"Baslik": "Miktar", "Icerik": f"{yuda_details.get('YillikProfilSiparisiMiktar', '')} {yuda_details.get('ProfilMiktarBirim', '')} / {yuda_details.get('ProfilSip', '')}"},
            {"Baslik": "Müşteri Ödeme Vadesi", "Icerik": yuda_details.get('MusteriOdemeVadesi', '')},
            {"Baslik": "Çizim No", "Icerik": yuda_details.get('CizimNo', '')},
        ]},
        {"Baslik": "Alaşım Kondüsyon", "Icerik": "hh", "_children": al},
        {"Baslik": "Tolerans", "Icerik": "hh", "_children": [
            {"Baslik": "DIN Tolerans", "Icerik": yuda_details.get('DinTolerans', '')},
            {"Baslik": "Birlikte Çalışan Aparatı Var mı", "Icerik": ', '.join(yuda_details.get('BirlikteCalisan', []))},
            {"Baslik": "Metre Ağırlık Talebi", "Icerik": f"{yuda_details.get('MATmin', '')} - {yuda_details.get('MATmax', '')} kg/m"},
            {"Baslik": "Önemli Ölçüler", "Icerik": yuda_details.get('OnemliOlculer', '')}
        ]},
        {"Baslik": "Yüzey Detay", "Icerik": "hh", "_children": [
            {"Baslik": "Yuzey Pres", "Icerik": "", "_children": yp},
            {"Baslik": "Yuzey Eloksal", "Icerik": "", "_children": ye},
            {"Baslik": "Yuzey Boya", "Icerik": "", "_children": yb},
            {"Baslik": "Yuzey Ahşap Kaplama", "Icerik": "", "_children": ya},
        ]},
        {"Baslik": "Talaşlı İmalat", "Icerik": "hh", "_children": [
            {"Baslik": "", "Icerik": yuda_details.get('TalasliImalat', '')},
            {"Baslik": "", "Icerik": yuda_details.get('TalasliImalatAciklama', '')}
        ]},
        {"Baslik": "Paketleme", "Icerik": "hh", "_children": [
            {"Baslik": "", "Icerik": yuda_details.get('Paketleme', '')},
            {"Baslik": "", "Icerik": yuda_details.get('PaketlemeAciklama', '')}
        ]},
        {"Baslik": "Dosyalar", "Icerik": "", "_children": [
            {"Baslik": "Teknik Resim", "Icerik": "", "_children": []},
            {"Baslik": "Şartnama", "Icerik": "", "_children": []},
            {"Baslik": "Paketleme Talimatı", "Icerik": "", "_children": []},
            {"Baslik": "Diğer", "Icerik": "", "_children": []},
            {"Baslik": ".DXF Kesit Çizimi", "Icerik": "", "_children": []},
        ]}
    ]

    return data

def format_row(row):
    formatted_data = []
    olmaz = ["id", "YudaNo", "YudaAcanKisi_id", "ProjeYoneticisi_id", "Tarih", "RevTarih", "Silindi", "ProfilSip", "ProfilMiktarBirim", "YillikProfilSiparisiMiktar", "Metre Ağırlık Talebi", "MATmin", "MATmax"]

    key_mapping = {
        "MusteriFirmaAdi": "Müşteri Firma Adı", "SonKullaniciFirma": "Son Kullanıcı Firma", "KullanımAlani": "Kullanım Alanı", "CizimNo": "Çizim Numarası", 
        "MusteriOdemeVadesi": "Müşteri Ödeme Vadisi", "AlasimKondusyon": "Alaşım ve Kondüsyon", "DinTolerans": "DIN Toleransı", "BirlikteCalisan": "Birlikte Çalışan",
        "OnemliOlculer": "Önemli Ölçüler", "YuzeyPres": "Yüzey Pres", "YuzeyEloksal": "Yüzey Eloksal", "YuzeyBoya": "Yüzey Boya", "YuzeyAhsap": "Yüzey Ahşap",
        "TalasliImalat": "Talaşlı İmalat", "TalasliImalatAciklama": "Açıklama", "Paketleme": "Paketleme", "PaketlemeAciklama": "Açıklama"
    }
    main_rows = {
        "Sipariş": ["MusteriFirmaAdi", "SonKullaniciFirma", "KullanımAlani", "CizimNo","ProfilSip", "ProfilMiktarBirim", "YillikProfilSiparisiMiktar", "MusteriOdemeVadesi"],
        "Alaşım ve Kondüsyon": ["AlasimKondusyon"],
        "Tolerans": ["DIN Tolerans", "Birlikte Çalışan Aparatı Var mı", "Metre Ağırlık Talebi", "MATmin", "MATmax","Önemli Ölçüler"],
        "Yüzey Detayları": ["YuzeyPres", "YuzeyEloksal", "YuzeyBoya", "YuzeyAhsap"],
        "Talaşlı İmalat": ["TalasliImalat", "TalasliImalatAciklama"],
        "Paketleme": ["Paketleme", "PaketlemeAciklama"]
    }

    for main_row_title, main_row_keys in main_rows.items():
        main_row_data = {"Baslik": main_row_title, "Icerik": "", "_children": []}
        if main_row_title == "Sipariş": # miktar girilmesi zorunlu olduğu için başka kontrol yok, zorunlu olma durumu değişirse burası da değişecek
            miktar_content = f"{row['YillikProfilSiparisiMiktar']} {row['ProfilMiktarBirim']} / {row['ProfilSip']}"
            main_row_data["_children"].append({"Baslik": "Miktar", "Icerik": miktar_content})
        if main_row_title == "Tolerans":
            if row['MetreAgirlikTalebi'] == "Yok":
                mat_content = f"{row['MetreAgirlikTalebi']}"
            else:
                mat_content = f"{row['MetreAgirlikTalebi']} min: ({row['MATmin']} kg/m) - max: ({row['MATmax']} kg/m)"
            main_row_data["_children"].append({"Baslik": "Metre Ağırlık Talebi", "Icerik": mat_content})

        for key in main_row_keys:
            if key in row and key not in olmaz and row[key]:
                if key == "AlasimKondusyon":
                    alaşım_kondüsyon_data = json.loads(row[key])
                    for item in alaşım_kondüsyon_data:
                        item_row = {"Baslik": alaşım_kondüsyon_data.index(item)+1, "Icerik": f"Alaşım: {item['Alasim']} - Kondüsyon: {item['Kondusyon']}"}
                        main_row_data["_children"].append(item_row)
                elif key in ["YuzeyPres", "YuzeyEloksal", "YuzeyBoya", "YuzeyAhsap"]:
                    yuzey_data = json.loads(row[key])
                    parent_item = {"Baslik": key_mapping[key], "Icerik": "", "_children": []}

                    child_item = []
                    for i in yuzey_data:
                        if  len(yuzey_data) == 1:
                            if key == 'YuzeyPres':
                                child_item = [{'Baslik':i['YuzeyDetay'], 'Icerik':  f"Boy: {i['YuzeyPresBoy']}mm"}]
                            elif key == 'YuzeyEloksal':
                                child_item = [{'Baslik':"", 'Icerik':  f"{i['Renk']}, {i['KaplamaKalinligi']}µ {i['EloksalBoy']}mm, {i['EloksalTemizKesim']}"}]
                            elif key == 'YuzeyBoya':
                                child_item = [{'Baslik':"", 'Icerik':  f"{i['Marka']} {i['MarkaRenkKodu']} {i['BoyaClass']} RAL {i['Ral']} {i['Tur']} </br> {i['BoyaKalinlik']}µ {i['BoyaBoy']}mm, {i['BoyaTemizKesim']}"}]
                            elif key == 'YuzeyAhsap':
                                child_item = [{'Baslik': "", 'Icerik': f"{i['AhsapKaplama']}, Boy: {i['AhsapBoy']}mm"}]
                        else:
                            if key == 'YuzeyPres':
                                child_item.append({'Baslik':i['YuzeyDetay'], 'Icerik':  f"Boy: {i['YuzeyPresBoy']}mm"})
                            elif key == 'YuzeyEloksal':
                                child_item.append({'Baslik':"", 'Icerik':  f"{i['Renk']}, {i['KaplamaKalinligi']}µ {i['EloksalBoy']}mm, {i['EloksalTemizKesim']}"})
                            elif key == 'YuzeyBoya':
                                child_item.append({'Baslik':"", 'Icerik':  f"{i['Marka']} {i['MarkaRenkKodu']} {i['BoyaClass']} RAL {i['Ral']} {i['Tur']} </br> {i['BoyaKalinlik']}µ {i['BoyaBoy']}mm, {i['BoyaTemizKesim']}"})
                            elif key == 'YuzeyAhsap':
                                child_item.append({'Baslik': "", 'Icerik': f"{i['AhsapKaplama']}, Boy: {i['AhsapBoy']}mm"})
                            
                    parent_item['_children'] = child_item
                    main_row_data["_children"].append(parent_item)
                else:
                    child_row = {"Baslik": key_mapping[key], "Icerik": row[key]}
                    main_row_data["_children"].append(child_row)
        if main_row_data["_children"]:
            formatted_data.append(main_row_data)

    return formatted_data

@login_required
def yudaDetail(request, yId):
    yudaD = YudaForm.objects.filter(id=yId)
    
    if yudaD.exists() and yudaD[0].Silindi:
        return render(request, 'ArslanTakipApp/yuda_error_page.html', {
            'error_message': 'Bu Yuda kaydı silinmiş ve artık kullanılamaz.'
        })
    
    yudaFiles = getFiles("YudaForm", yId)
    files = json.dumps(list(yudaFiles), sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    
    yudaComments = getParentComments("YudaForm", yId).order_by("Tarih")
    yudaCList = [process_comment(request.user, comment) for comment in yudaComments]
    comments = json.dumps(yudaCList, sort_keys=True, indent=1, cls=DjangoJSONEncoder)

    yudaDetails = yudaD.values()
    
    yList = list(yudaDetails)
    formatted_yuda_details = format_yuda_details(yList)
    data = json.dumps(formatted_yuda_details, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    
    onayCount = YudaOnay.objects.filter(Yuda_id=yId, OnayDurumu=True).count()
    retCount = YudaOnay.objects.filter(Yuda_id=yId, OnayDurumu=False).count()
    user_group = request.user.groups.first()
    if not YudaOnay.objects.filter(Yuda_id = yId, Group = user_group).first():
        secim =""
    else:
        secim = YudaOnay.objects.get(Yuda_id = yId, Group = user_group).OnayDurumu
    
    satis_onay = YudaOnay.objects.filter(Q(Group=19) | Q(Group=20),Yuda_id=yId,OnayDurumu=True).exists()
    if satis_onay and yudaDetails[0]['YeniKalipNo'] != None:
        satis_onay == False
    
    kaliphane_grup = request.user.groups.filter(name='Kaliphane Bolumu').exists()
    kaliphane_onay = YudaOnay.objects.filter(Group__name='Kaliphane Bolumu', Yuda_id=yId, OnayDurumu=True).exists()

    kalip_onay = False #satis_onay and kaliphane_grup and kaliphane_onay
    # return render(request, 'ArslanTakipApp/yudaDetail.html', {'yuda_json':data, 'data2':formatted_data2, 'files_json':files, 'comment_json':comments, 'onay':onayCount, 'ret': retCount, 'Selected':secim})
    return render(request, 'ArslanTakipApp/yudaDetail.html', {'yuda_json':data, 'files_json':files, 'comment_json':comments, 'onay':onayCount, 'ret': retCount, 'Selected':secim, 'kalip_onay':kalip_onay})

def yudaDetail_kalipno(request):
    kalip_no = request.POST.get('kalip_no')
    yuda_id = request.POST.get('yuda_id')
    print(kalip_no)
    
    try:
        yuda = YudaForm.objects.get(id=yuda_id)
        print(yuda)
        if yuda.meta_data is None:
            yuda.meta_data = {}
        yuda.meta_data['KalipNo'] = kalip_no
        # yuda.save()
        return JsonResponse({'status': 'success'})
    except YudaForm.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Yuda bulunamadı'})

@login_required
def yudaDetail2(request, yId):
    #veritabanından yuda no ile ilişkili dosyaların isimlerini al
    yudaFiles = getFiles("YudaForm", yId)
    files = json.dumps(list(yudaFiles), sort_keys=True, indent=1, cls=DjangoJSONEncoder)

    svgData = ""
    if yudaFiles.filter(FileTitle = "Şartname").exists():
        fi = UploadFile.objects.get(Q(FileModel = "YudaForm") & Q(FileModelId = yId) & Q(FileTitle = 'Şartname'))
        svgData = yudaDetailSvg(request, fi.File.path)
        
    yudaComments = getParentComments("YudaForm", yId).order_by("Tarih")
    yudaCList = [process_comment(request.user, comment) for comment in yudaComments]
    comments = json.dumps(yudaCList, sort_keys=True, indent=1, cls=DjangoJSONEncoder)

    yudaDetails = YudaForm.objects.filter(id = yId).values()

    formatted_data = format_row(yudaDetails[0])
    
    yList = list(yudaDetails)
    formatted_yuda_details = format_yuda_details(yList)
    data = json.dumps(formatted_yuda_details, sort_keys=True, indent=1, cls=DjangoJSONEncoder)

    onayCount = YudaOnay.objects.filter(Yuda_id=yId, OnayDurumu=True).count()
    retCount = YudaOnay.objects.filter(Yuda_id=yId, OnayDurumu=False).count()
    if not YudaOnay.objects.filter(Yuda_id = yId, Group = request.user.groups.first()).first():
        secim =""
    else:
        secim = YudaOnay.objects.get(Yuda_id = yId, Group = request.user.groups.first()).OnayDurumu
    
    formatted_data2 = json.dumps(formatted_data, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    svgData = json.dumps(svgData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return render(request, 'ArslanTakipApp/yudaDetail2.html', {'yuda_json':data, 'svgData': svgData, 'data2':formatted_data2, 'files_json':files, 'comment_json':comments, 'onay':onayCount, 'ret': retCount, 'Selected':secim})

@transaction.atomic
def yudaDetailComment(request):
    if request.method == 'POST':
        try:
            req = request.POST
            c = Comment()
            c.Kullanici = request.user
            c.FormModel = "YudaForm"
            c.FormModelId = req['formID']
            c.Tarih = datetime.datetime.now()
            c.Aciklama = req['yorum']
            if 'replyID' in req:
                replyID = req['replyID']
                c.ReplyTo = Comment.objects.get(id=replyID)
            c.save()

            y = YudaForm.objects.get(id=req['formID'])
            y.GüncelTarih = datetime.datetime.now()
            y.save()

            for file in request.FILES.getlist('yfiles'):
                UploadFile.objects.create(
                    File = file,
                    FileModel = "Comment",
                    FileModelId = c.id,
                    FileSize = file.size,
                    UploadedBy = c.Kullanici,
                    Note = "",
                )

            allowed_groups = [group for group, perms in get_groups_with_perms(y, attach_perms=True).items() if 'gorme_yuda' in perms]

            if request.user.id != 1:
                for u in User.objects.filter(groups__in=allowed_groups).exclude(id=request.user.id):
                    notification = Notification.objects.create(
                        user=u,
                        message=f'{y.MusteriFirmaAdi[:11]}.. projesine yorum yaptı.',
                        subject=f"Yeni YUDA Yorum",
                        where_id=y.id,
                        new_made_by = request.user,
                        col_marked = "#E9ECEF",
                    )
                    logger.debug(f"Comment Notification is created. ID: {notification.id}, Time: {notification.timestamp.strftime('%d-%m-%y %H:%M')}")
                    
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'notifications_{request.user.id}',
                        {
                            'type': 'send_notification',
                            'notification': {
                                'id': notification.id,
                                'subject': notification.subject,
                                'made_by': get_user_full_name(notification.new_made_by_id),
                                'message': notification.message,
                                'where_id': notification.where_id,
                                'is_read': notification.is_read,
                                'timestamp': notification.timestamp.strftime('%d-%m-%y %H:%M'),
                                'is_marked': notification.is_marked,
                            },
                        }
                    )
                    logger.debug(f"Comment Notification is sent. ID: {notification.id}, Time: {notification.timestamp.strftime('%d-%m-%y %H:%M')}")
                
            response = JsonResponse({'message': 'Kayıt başarılı'})
        except json.JSONDecodeError:
            response = JsonResponse({'error': 'Geçersiz JSON formatı'})
            response.status_code = 400 #bad request
        except Exception as e:
            response = JsonResponse({'error': str(e)})
            response.status_code = 500 #server error
    return response

def yudaDCEdit(request):
    if request.method == 'POST':
        req = request.POST
        try:
            c = Comment.objects.get(id=req["commentId"])
            c.Aciklama = req["commentText"]
            c.save()
            #dosyalar için olan bölüm de eklenecek
            response = JsonResponse({'message': 'Kayıt başarılı'})
        except Exception as e:
            response = JsonResponse({'error': str(e)})
            response.status_code = 500 #server error
        return response

def yudaDCDelete(request, cId):
    try:
        print(cId)
        comment = Comment.objects.get(id = cId)
        comment.Silindi = True
        comment.save()
        response = JsonResponse({'message': 'Yorum başarıyla silindi.'})
    except Exception as e:
        response = JsonResponse({'error': str(e)})
        response.status_code = 500 #server error
    return response

def determine_onay_durumu(durumlar):
    kaliphane = durumlar.get('kaliphane')
    mekanik = durumlar.get('mekanik')
    satis = durumlar.get('satis')

    if kaliphane == 3 or mekanik == 3 or satis == 3:
        return 'Reddedildi'
    if kaliphane == 1:
        return 'Kalıphane Onayı Bekleniyor'
    elif kaliphane == 2 and mekanik == 0 and satis == 1:
        return 'Satış Onayı Bekleniyor'
    elif kaliphane == 2 and mekanik == 0 and satis == 2:
        return 'Onaylandı'
    elif kaliphane == 2 and mekanik == 1:
        return 'Mekanik İşlem Onayı Bekleniyor'
    elif kaliphane == 2 and mekanik == 2 and satis == 1:
        return 'Satis Onayi Bekleniyor'
    elif kaliphane == 2 and mekanik == 2 and satis == 2:
        return 'Onaylandı'
    
    return 'Bilinmeyen Durum'

def checkYudaOnayDurum(request):
    yudas = YudaForm.objects.values().order_by('id')
    for y in yudas:
        yuda = YudaForm.objects.get(id=y['id'])
        yuda_onay = YudaOnayDurum.objects.filter(yuda_id=y['id']).values('yuda_id', 'kaliphane_onay_durumu', 'satis_onay_durumu', 'mekanik_islem_onay_durumu')
        if yuda_onay:
            yuda_onay_durumu = yuda_onay[0]
            
            kh_durum = yuda_onay_durumu['kaliphane_onay_durumu'] # değer 1 ise null, 2 ise True, 3 ise False
            satis_durum = yuda_onay_durumu['satis_onay_durumu'] # değer 1 ise null, 2 ise True, 3 ise False
            mekanik_durum = yuda_onay_durumu['mekanik_islem_onay_durumu'] # değer 0 ise mekanik işlem yok, 1 ise null, 2 ise True, 3 ise False
            durumlar = {'kaliphane': kh_durum, 'mekanik': mekanik_durum, 'satis': satis_durum}
            
            onay_durumu = determine_onay_durumu(durumlar)
            # print(f"yudaNo: {y['YudaNo']} onay_durumu: {onay_durumu}")
            yuda.OnayDurumu = onay_durumu
            yuda.save()

def yudaDetailAnket(request):
    params = json.loads(unquote(request.GET.get('params', '{}')))
    yudaId = params.get("yId")
    secim = params.get("secim")
    if secim == "onay":
        secim = True
    else:
        secim = False
    predefined_group_names = [
        'Ust Yonetim Bolumu',
        'Planlama Bolumu',
        'Kalite Bolumu',
        'Kaliphane Bolumu',
        'Pres Bolumu',
        'Paketleme Bolumu',
        'Yurt Disi Satis Bolumu',
        'Yurt Ici Satis Bolumu',
        'Eloksal Bolumu',
        'Ahsap Kaplama Bolumu',
        'Boyahane Bolumu',
        'Mekanik Islem Bolumu',
    ]

    user_group = None
    for group_name in predefined_group_names:
        group = Group.objects.get(name=group_name)
        if request.user.groups.filter(name=group_name).exists():
            user_group = group
            break

    if user_group is None:
        return JsonResponse({'error': 'User does not belong to any predefined group'}, status=400)

    # groups.first() şeklinde yapmak çok sağlıklı olmayabilir.
    # Update or create YudaOnay entry
    try:
        # Check if the users group has already voted for this Yuda_id
        group_vote = YudaOnay.objects.filter(Yuda_id=yudaId, Group=user_group).first()

        if group_vote:
            # If the group has already voted, update their vote
            group_vote.OnayDurumu = secim
            group_vote.save()
        else:
            # If the group hasn't voted, create a new vote record
            YudaOnay.objects.create(
                Group=user_group,
                Yuda_id=yudaId,
                OnayDurumu=secim
            ) # 
        
        yuda = YudaForm.objects.get(id=yudaId)
        yuda_onay_durumu = YudaOnayDurum.objects.filter(yuda_id=yudaId).values("kaliphane_onay_durumu", "mekanik_islem_onay_durumu", "satis_onay_durumu")[0]
        
        kh_durum = yuda_onay_durumu["kaliphane_onay_durumu"] # değer 1 ise null, 2 ise True, 3 ise False
        satis_durum = yuda_onay_durumu["satis_onay_durumu"] # değer 1 ise null, 2 ise True, 3 ise False
        mekanik_durum = yuda_onay_durumu["mekanik_islem_onay_durumu"] # değer 0 ise mekanik işlem yok, 1 ise null, 2 ise True, 3 ise False
        durumlar = {'kaliphane': kh_durum, 'mekanik': mekanik_durum, 'satis': satis_durum}
        
        onay_durumu = determine_onay_durumu(durumlar) # 
        # print(f"yuda: {yuda.YudaNo}, durumlar: {durumlar}, onay_durumu: {onay_durumu}")
        yuda.OnayDurumu = onay_durumu
        yuda.save()

        # Calculate counts for true and false votes for the Yuda_id
        onay_count = YudaOnay.objects.filter(Yuda_id=yudaId, OnayDurumu=True).count()
        ret_count = YudaOnay.objects.filter(Yuda_id=yudaId, OnayDurumu=False).count()

        return JsonResponse({'onay': onay_count, 'ret': ret_count})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
   
def yudaDetailSvg(request, path):
    areas, perimeters, paths = dxf_file_area_calculation(path)
    # print(f"areas: {areas} \nperimeters: {perimeters} \npaths: {paths}")
    kalipTip =""
    zivana = 0
    if len(areas)>1:
        # print ("Portol Kalıp")
        # print (f"Zıvana Sayısı : {len(areas) - 1}")
        kalipTip = "Portol Kalıp"
        zivana = len(areas) - 1
    else:
        # print("Solid Kalıp")
        kalipTip = "Solid Kalıp"
    # for i in range(len(areas)):
    #     print(f"Alan: {areas[i]}, Çevre: {perimeters[i]}")
    l = areas.index(max(areas))
    outer_area = areas[l]
    areas.remove(outer_area)
    inner_area = sum(areas) 
    section_area = outer_area - inner_area
    outer_perimeter = perimeters[l]
    perimeters.remove(outer_perimeter)
    inner_perimeter = sum(perimeters)
    total_perimeter = outer_perimeter + inner_perimeter
    gramaj = section_area*2.7/1000
    # print(f"Kesit Alanı: {section_area:.2f} mm²")
    # print(f"Gramaj: {gramaj:.2f} kg/m")
    # print(f"Dış Çevre: {outer_perimeter:.2f} mm")
    # print(f"İç Çevre: {inner_perimeter:.2f} mm")
    # print(f"Şekil Faktörü: {total_perimeter/(gramaj*10):.2f}")

    
    svg = ""
    for i in range(len(paths)):
        if i == l:
            svg = svg + paths[i] + f'id = "po" class="ciz" />' + '\n'
        else:
            svg = svg + paths[i] + f'id = "p{i}" class="ciz" />' + '\n'
    
    data = {
        'svg': svg, 
        'printed_info': {
            'kalip_tip': kalipTip,
            'zivana': zivana,
            'section_area': section_area,
            'gramaj': gramaj,
            'outer_perimeter': outer_perimeter,
            'inner_perimeter': inner_perimeter,
            'total_perimeter': total_perimeter,
            'shape_factor': total_perimeter / (gramaj * 10)
        }
    }


    return data

def yudaDelete(request, yId):
    yuda = YudaForm.objects.get(id = yId)
    yuda.Silindi = True
    yuda.Silindi_by = request.user
    yuda.save()
    return HttpResponseRedirect("/yudas")

@login_required
def yudaEdit(request, yId):
    yudaFiles = getFiles("YudaForm", yId)
    files = json.dumps(list(yudaFiles), sort_keys=True, indent=1, cls=DjangoJSONEncoder)

    yuda = YudaForm.objects.filter(id = yId).values()
    yudaList = list(yuda)

    for i in yudaList:
        i['Tarih'] = format_date(i['Tarih'])

    yudaData = json.dumps(yudaList, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return render(request, 'ArslanTakipApp/yudaEdit.html', {'yuda_json':yudaData, 'files_json':files})

def upload_files(request, y):
    file_titles = request.POST.getlist('fileTitles[]')
    for file, title in zip(request.FILES.getlist('files'), file_titles):
        UploadFile.objects.create(
            File = file,
            FileTitle = title,
            FileSize = file.size,
            FileModel = "YudaForm",
            FileModelId = y.id,
            UploadedBy = y.ProjeYoneticisi,
            Note = "",
        )

def delete_file(fId):
    try:
        file = UploadFile.objects.get(id = fId)
        file.delete()
        print(f"{file.File} silindi")
        return True
    except UploadFile.objects.get(id = fId).DoesNotExist:
        return False
    
def changeFiles(fId, fTitle):
    try:
        file = UploadFile.objects.get(id = fId)
        if file.FileTitle != fTitle:
            file.FileTitle = fTitle
            file.save()
        return True
    except UploadFile.objects.get(id = fId).DoesNotExist:
        return False

def yudachange(request, yId):
    if request.method == 'POST':
        changeYuda = YudaForm.objects.get(id = yId)
        changeYuda.RevTarih = datetime.datetime.now()
        group_mapping = {
            'YuzeyEloksal': 'Eloksal Bolumu',
            'YuzeyAhsap': 'Ahsap Kaplama Bolumu',
            'YuzeyBoya': 'Boyahane Bolumu',
            'TalasliImalat': 'Mekanik Islem Bolumu',
        }

        for key, value in request.POST.items():
            if hasattr(changeYuda, key):
                print(f"key: {key}, value: {value}")
                if key == "BirlikteCalisan":
                    value_list = value.split(',')
                    setattr(changeYuda, key, value_list)
                else:
                    setattr(changeYuda, key, value)

            # Check field values and assign permissions based on conditions
            for field in changeYuda._meta.fields:
                fname = field.name
                fvalue = getattr(changeYuda, fname)
                if fname in group_mapping and fvalue is not None and fvalue != "" and fname != "TalasliImalat":
                    group = Group.objects.get(name=group_mapping[fname])
                    assign_perm("gorme_yuda", group, changeYuda)
                if fname == "TalasliImalat" and fvalue == "Var":
                    group = Group.objects.get(name=group_mapping[fname])
                    assign_perm("gorme_yuda", group, changeYuda)
            
            if key == "oldFileNewTitle" and value != '':
                for v in json.loads(value):
                    if not changeFiles(v['id'], v['title']):
                        response = JsonResponse({"error": "Dosya başlığı değiştirilemedi."})
                        response.status_code = 500  # Server error
                        return response
            
            if key == "deletedId" and value != '':
                deleteList = value.split(",")
                for f in deleteList:
                    if not delete_file(f):
                        response = JsonResponse({"error": "Dosya silinemedi."})
                        response.status_code = 500  # Server error
                        return response
        
        upload_files(request, changeYuda)
        changeYuda.save()
    
    response = JsonResponse({'message': 'Değişiklikler başarıyla kaydedildi.\nDetay sayfasına yönlendiriliyorsunuz.'})
    return response

@login_required
def yudaCopy(request, yId):
    yudaFiles = getFiles("YudaForm", yId)
    files = json.dumps(list(yudaFiles), sort_keys=True, indent=1, cls=DjangoJSONEncoder)

    yuda = YudaForm.objects.filter(id = yId).values()
    yudaList = list(yuda)

    for i in yudaList:
        i['Tarih'] = format_date(i['Tarih'])

    yudaData = json.dumps(yudaList, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return render(request, 'ArslanTakipApp/yudaCopy.html', {'yuda_json':yudaData, 'files_json':files})

class DeletedYudasView(generic.TemplateView):
    template_name = 'ArslanTakipApp/deletedYudas.html'

def deletedYudas_list(request):
    print("delete")
    params = json.loads(unquote(request.GET.get('params', '{}')))
    for i in params:
        value = params[i]
        print("Key and Value pair are ({}) = ({})".format(i, value))

    size = params.get("size", 7)  # Default size to 7
    page = params.get("page", 1)  # Default page to 1
    offset, limit = calculate_pagination(page, size)
    filter_list = params.get("filter", [])
    q = {}

    temsilciler = User.objects.filter(Q(groups__name = "Yurt Ici Satis Bolumu") | Q(groups__name = "Yurt Disi Satis Bolumu"))
    temsilci_data = [{'id': user.id, 'full_name': get_user_full_name(user.id)} for user in temsilciler]

    y = get_objects_for_user(request.user, "gorme_yuda", YudaForm.objects.filter(Silindi=True, Silindi_by=request.user)) #user görme yetkisinin olduğu yudaları görsün

    if len(filter_list) > 0:
        for i in filter_list:
            if i['field'] == 'Bolum':
                for bolum in i['value']:
                    if bolum == 'Boya':
                        q['YuzeyBoya__gt'] = ""
                    elif bolum == 'Eloksal':
                        q['YuzeyEloksal__gt'] = ""
                    elif bolum == 'Mekanik Islem':
                        q['TalasliImalat__exact'] = 'Var'  # Filter where TalasliImalat is 'Var'
            elif i['field'] == 'Dosya':
                file_ids = UploadFile.objects.filter(File__icontains=i['value']).values_list('FileModelId', flat=True)
                q['id__in'] = list(file_ids)
            elif i['field'] == 'Tarih' or i['field'] == 'GüncelTarih': #type = start date, value=finish date
                if i['type'] != i['value']:
                    q[i['field'] + "__gte"] = i['type']
                    q[i['field'] + "__lt"] = i['value'] + ' 23:59:59'
                else:
                    q[i['field'] + "__startswith"] = i['value']
            else:
                q = filter_method(i, q)

    filtered_yudas = y.filter(**q).order_by("-Tarih", "-YudaNo")
    yudaList = list(filtered_yudas.values()[offset:limit])
    
    for o in yudaList:
        o['Tarih'] = format_date_time(o['Tarih'])
        if o['GüncelTarih'] != None:
            o['GüncelTarih'] = format_date_time(o['GüncelTarih'])
        else: o['GüncelTarih'] = ""
        o['MusteriTemsilcisi'] = get_user_full_name(int(o['YudaAcanKisi_id']))
        o['durumlar'] = {}
        for group in [group.name.split(' Bolumu')[0] for group, perms in get_groups_with_perms(y.get(id=o['id']), attach_perms=True).items() if perms == ['gorme_yuda'] and group.name != 'Proje Bolumu']:
            yuda_onay = YudaOnay.objects.filter(Yuda=o['id'], Group__name=group+' Bolumu').first()
            if yuda_onay:
                if yuda_onay.OnayDurumu is True:
                    o['durumlar'][group] = 'success'
                elif yuda_onay.OnayDurumu is False:
                    o['durumlar'][group] = 'danger'
            else: o['durumlar'][group] = 'warning'
        
    yudas_count = filtered_yudas.count()
    last_page = math.ceil(yudas_count / size)
    response_data = {
        'last_page' : last_page,
        'data' : yudaList,
        'temsil': temsilci_data
    }
    data = json.dumps(response_data, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

def yudaDeleteCancel(request, yId):
    try:
        yuda = YudaForm.objects.get(id=yId)
        yuda.RevTarih = datetime.datetime.now()
        yuda.Silindi = None
        yuda.Silindi_by = None
        yuda.save()
        response = JsonResponse({'message': 'YUDA başarıyla kurtarıldı.\nDetay sayfasına yönlendiriliyorsunuz.'})
    except Exception as e:
        response = JsonResponse({'error': str(e)})
        response.status_code = 500 #server error

    return response

class AllNotificationsView(generic.TemplateView):
    template_name = 'notifications/notification_list.html'

def notifications_all(request):
    params = json.loads(unquote(request.GET.get('params', '{}')))

    size = params.get("size", 7)  # Default size to 7
    page = params.get("page", 1)  # Default page to 1
    offset, limit = calculate_pagination(page, size)
    filter_list = params.get("filter", [])
    q = {}

    notis = Notification.objects.filter(user=request.user)

    if len(filter_list) > 0:
        for i in filter_list:
            if i['field'] == 'Kisi':
                userIds = User.objects.filter(username__icontains = i['value']).values_list('id', flat=True) # get the ids
                q["new_made_by_id__in"] = userIds
            elif i['field'] == 'CizimNo':
                cizimIds = YudaForm.objects.filter(CizimNo__icontains = i['value']).values_list('id', flat=True)
                q["where_id__in"] = cizimIds
            else:
                q = filter_method(i, q)
    
    filtered_notis = notis.filter(**q).order_by('-timestamp')
    notiList = list(filtered_notis.values()[offset:limit])

    yudaNoti = []
    ycommentNoti = []
    for n in notiList:
        n["Kisi"] = get_user_full_name(n['new_made_by_id'])
        n['timestamp'] = format_date_time(n['timestamp'])
        n['CizimNo'] = ""
        if n['subject'] == "Yeni YUDA":
            y = YudaForm.objects.get(id = n['where_id'])
            n['message'] = y.MusteriFirmaAdi + n['message'].split("..")[1]
            n['CizimNo'] = y.CizimNo
            yudaNoti.append(n)
        elif n['subject'] == "Yeni YUDA Yorum":
            c = Comment.objects.filter(Kullanici_id=n['new_made_by_id'], FormModel='YudaForm', FormModelId=n['where_id']).latest('Tarih')
            cleaned_message = re.sub(r'<p>\s*<br>\s*</p>', '', c.Aciklama)
            n['comment']=cleaned_message
            n['CizimNo'] = YudaForm.objects.get(id = n['where_id']).CizimNo
            ycommentNoti.append(n)
    
    notis_count = filtered_notis.count()
    last_page = math.ceil(notis_count / size)
    response_data = {
        'last_page' : last_page,
        'data' : notiList
    }
    data = json.dumps(response_data, sort_keys=True, indent=1, cls=DjangoJSONEncoder)

    return HttpResponse(data)

def notifReadAll(request):
    try:
        notifications = Notification.objects.filter(user=request.user)
        notifications.update(is_read=True)
        response = JsonResponse({'message': 'Tümü okundu işaretlendi.'})
    except Exception as e:
        response = JsonResponse({'error': str(e)})

    return response

# Her bir özelliği kontrol etmek için yazdırın değişiklikler doğru mu kontrol et aynı şeyi birden fazla 
""" for field in changeYuda._meta.fields:
    print(f"{field.name}: {getattr(changeYuda, field.name)}") """

def getFiles(ref, mId):
    allFiles = UploadFile.objects.all()
    filteredFiles = allFiles.filter(Q(FileModel = ref) & Q(FileModelId = mId)).values()

    return filteredFiles

def getParentComments(ref, mId):
    allComments = Comment.objects.all()
    filteredComments = allComments.filter(Q(FormModel = ref) & Q(FormModelId = mId) & Q(ReplyTo__isnull = True) & Q(Silindi= False)).values()
    
    return filteredComments

class UretimPlanlamaView(generic.TemplateView):
    template_name = 'ArslanTakipApp/uretimPlani.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sip = SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')).exclude(SiparisTamam='BLOKE')

        distinct_values = {
            'press_codes': sip.values_list('PresKodu', flat=True).distinct(),
        }
        context_data = {field: json.dumps(list(values)) for field, values in distinct_values.items()}
        context.update(context_data)
        return context

    def get(self, request, *args, **kwargs):
        if 'press_code' in request.GET:
            return self.get_data_by_press_code(request)
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)
    
    def get_data_by_press_code(self, request):
        press_code = request.GET.get('press_code')
        sip = SiparisList.objects.using('dies').filter(
            Q(Adet__gt=0) & 
            ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & 
            Q(Adet__gte=1)) & 
            Q(BulunduguYer='TESTERE') & 
            Q(PresKodu=press_code)
        ).exclude(SiparisTamam='BLOKE')

        data = {
            'siparisler': list(sip.values_list('KartNo', flat=True).distinct()),
            'profiller': list(sip.values_list('ProfilNo', flat=True).distinct()),
            'firmalar': list(sip.values_list('FirmaAdi', flat=True).distinct()),
            'billetler': list(sip.values_list('BilletTuru', flat=True).distinct()),
            'kondusyonlar': list(sip.values_list('KondusyonTuru', flat=True).distinct()),
            'yuzeyler': list(sip.values_list('YuzeyOzelligi', flat=True).distinct()),
            'gramajlar': list(sip.values_list('Profil_Gramaj', flat=True).distinct()),
        }
        return JsonResponse(data)
    
    def post(self, request, *args, **kwargs):
        data = request.POST
        pres_kodu = data.get('pres_kodu') # kullanıcıdan alınacak
        kriterData = json.loads(data['kriterData'])
        if not kriterData:
            return JsonResponse({"error": "Missing data."}, status=400)
        
        order_plan = self.production_plan(pres_kodu, kriterData)
        order_plan = self.transform_plan(order_plan)
        return JsonResponse({'order_plan': order_plan})

    def production_plan(self, pres_kodu, kriterler):
        sip = SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')).exclude(SiparisTamam='BLOKE')
        orders = sip.filter(PresKodu=pres_kodu, Kg__gt=0).order_by("SonTermin")
        kaliplar = KalipMs.objects.using('dies').filter(AktifPasif='Aktif', Hatali=False, TeniferKalanOmurKg__gt=0).exclude(Silindi=1)
        kapasiteler = {kalip.KalipNo: kalip.TeniferKalanOmurKg * 0.85 for kalip in kaliplar}
        
        exclude_list = [item['kriter'] for item in kriterler if item['type'] == 'Hariç Tut']
        priority_list = [item['kriter'] for item in kriterler if item['type'] == 'Öncelik']
        limit_list = [item for item in kriterler if item['type'] == 'Limit']

        transformations = {
            'Sipariş': 'KartNo',
            'Yüzey': 'YuzeyOzelligi',
            'Billet': 'BilletTuru',
            'Firma': 'FirmaAdi',
            'Kondüsyon': 'KondusyonTuru',
            'Profil': 'ProfilNo',
            'Gramaj': 'Profil_Gramaj',
            'Termin Başlangıç': 'SonTermin__gte',
            'Termin Bitiş': 'SonTermin__lte',
        }

        def transform_element(element):
            for key, value in transformations.items():
                if key in element:
                    return element.replace(key, value)
            return element

        for item in exclude_list:
            pairs = item.split(", ")
            e_conditions = {}
            for pair in pairs:
                field, value = pair.split(": ", 1)
                field = transform_element(field)
                if field == 'SonTermin__gte' or field == 'SonTermin__lte':
                    value = datetime.datetime.strptime(value, '%d/%m/%y').strftime('%Y-%m-%d')
                e_conditions[field] = value
            orders = orders.exclude(**e_conditions)
        
        # Initialize the order plan and planned_kg
        order_plan = []
        planned_kg = 0
        limit_order = []
        # Process limits and add minimum amounts to planned_kg
        for item in limit_list:
            pairs = item['kriter'].split(", ")
            l_conditions = {}
            for pair in pairs:
                field, value = pair.split(": ", 1)
                field = transform_element(field)
                if field == 'SonTermin__gte' or field == 'SonTermin__lte':
                    value = datetime.datetime.strptime(value, '%d/%m/%y').strftime('%Y-%m-%d')
                l_conditions[field] = value
            min_kg = float(item['min']) if item['min'] else 0
            max_kg = float(item['max']) if item['max'] else float('inf')
            limited_orders = orders.filter(**l_conditions)
            print(f"l_conditions: {l_conditions}, min: {min_kg},, max: {max_kg}")

            current_kg = 0
            for order in limited_orders:
                for order in limited_orders:
                    if current_kg >= min_kg:
                        break
                    if current_kg + order.Kg <= min_kg:
                        add_kg = order.Kg
                    else:
                        add_kg = min_kg - current_kg
                    current_kg += add_kg
                    planned_kg += add_kg

                    limit_order.append({
                        'press_code': pres_kodu,
                        'production_date': datetime.datetime.now().date(),
                        'order': order.Kimlik,
                        'planned_kg': add_kg,
                        'fixed_production': True
                    })
            
        pri_ids = []
        for item in priority_list:
            pairs = item.split(", ")
            p_conditions = {}
            for pair in pairs:
                field, value = pair.split(": ", 1)
                field = transform_element(field)
                if field == 'SonTermin__gte' or field == 'SonTermin__lte':
                    value = datetime.datetime.strptime(value, '%d/%m/%y').strftime('%Y-%m-%d')
                p_conditions[field] = value
            priority_orders = orders.filter(**p_conditions)
            pri_ids += [pri.Kimlik for pri in priority_orders]
            
            for order in priority_orders:
                if planned_kg + order.Kg <= 13000:
                    planned_kg += order.Kg
                    order_plan.append({
                        'press_code': pres_kodu,
                        'production_date': datetime.datetime.now().date(),
                        'order': order.Kimlik,
                        'planned_kg': order.Kg,
                        'fixed_production': False
                    })
                else:
                    remaining_kg = 13000 - planned_kg
                    if remaining_kg > 0:
                        order_plan.append({
                            'press_code': pres_kodu,
                            'production_date': datetime.datetime.now().date(),
                            'order': order.Kimlik,
                            'planned_kg': remaining_kg,
                            'fixed_production': False
                        })
                        planned_kg += remaining_kg
                    break
                
            for li in limit_order:
                order_plan.append(li)


        # pri_query = orders.filter(Kimlik__in = pri_ids)
        # non_pri_query = orders.exclude(Kimlik__in = pri_ids).order_by('SonTermin')
        # gunluk_max_uretim = 13000

        # def planlama(sips):
        #     nonlocal planned_kg
        #     for siparis in sips:
        #         kalan_miktar = siparis.Kg
        #         kalip_uretim = {}
        #         for kalip in kaliplar:
        #             if siparis.ProfilNo == kalip.ProfilNo and planned_kg < gunluk_max_uretim:
        #                 uretim_miktari = min(kalip.TeniferKalanOmurKg * 0.85, kalan_miktar, gunluk_max_uretim - planned_kg)
        #                 if uretim_miktari > 0:
        #                     if kalip.KalipNo in kalip_uretim:
        #                         kalip_uretim[kalip.KalipNo] += uretim_miktari
        #                     else:
        #                         kalip_uretim[kalip.KalipNo] = uretim_miktari
        #                     kalan_miktar -= uretim_miktari
        #                     planned_kg += uretim_miktari
        #                 if planned_kg >= gunluk_max_uretim:
        #                     break
        #         if kalip_uretim:
        #             order_plan.append({
        #                 'press_code': pres_kodu,
        #                 'order': siparis.Kimlik,
        #                 'production_date': datetime.datetime.now().date(),
        #                 'Profil': siparis.ProfilNo,
        #                 'uretim_detaylari': kalip_uretim,
        #             })
        #         if kalan_miktar > 0 and planned_kg < gunluk_max_uretim:
        #             order_plan.append({
        #                 'press_code': pres_kodu,
        #                 'order': siparis.Kimlik,
        #                 'production_date': datetime.datetime.now().date(),
        #                 'Profil': siparis.ProfilNo,
        #                 'uretim_detaylari': {'Kalan': kalan_miktar},  # Kalan miktar bir sonraki güne taşınacak
        #             })

        # planlama(pri_query)
        # if planned_kg < gunluk_max_uretim:
        #     planlama(non_pri_query)
        #     print(f"order: {order_plan}")
        if len(priority_list) < 1:
            for li in limit_order:
                order_plan.append(li)

        if planned_kg < 13000:
            remaining_orders = orders.exclude(Kimlik__in=[item['order'] for item in order_plan])
            for order in remaining_orders:
                if planned_kg + order.Kg <= 13000:
                    planned_kg += order.Kg
                    order_plan.append({
                        'press_code': pres_kodu,
                        'production_date': datetime.datetime.now().date(),
                        'order': order.Kimlik,
                        'planned_kg': order.Kg,
                        'fixed_production': False
                    })
                else:
                    remaining_kg = 13000 - planned_kg
                    if remaining_kg > 0:
                        order_plan.append({
                            'press_code': pres_kodu,
                            'production_date': datetime.datetime.now().date(),
                            'order': order.Kimlik,
                            'planned_kg': remaining_kg,
                            'fixed_production': False
                        })
                        planned_kg += remaining_kg
                    break

        return order_plan

    def transform_plan(self, plan):
        siparis = SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')).exclude(SiparisTamam='BLOKE')
        
        for o in plan:
            kimlik = o['order']
            s = siparis.get(Kimlik=kimlik)
            o['KartNo'] = s.KartNo
            o['Firma'] = s.FirmaAdi
            o['Billet'] = s.BilletTuru
            o['Profil'] = s.ProfilNo
            o['Yuzey'] = s.YuzeyOzelligi
            o['Kondusyon'] = s.KondusyonTuru
            o['Gramaj'] = s.Profil_Gramaj
            o['SonTermin'] = s.SonTermin.strftime("%d-%m-%Y")

        return plan

def get_alternative_profiles(profil_no):
    alt_group = KalipMuadil.objects.filter(profiller__contains=[profil_no]).first()
    if alt_group:
        alternative_dies = alt_group.profiller
    else:
        alternative_dies = [profil_no]
    
    return alternative_dies
             
class Press4500View(generic.TemplateView):
    template_name = '4500/pres4500.html'
    
    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs) 
    
def get_ongoing_sepet():
    ongoing_sepet = Sepet.objects.filter(bitis_saati__isnull=True)
    
    if ongoing_sepet:
        return ongoing_sepet.latest('id')
    return None

class Stacker4500View(generic.TemplateView):
    template_name = '4500/stacker4500.html'
    
    def get_context_data(self, **kwargs):
        sepet = get_ongoing_sepet()
        
        context = super().get_context_data(**kwargs)

        if sepet:
            context['ongoing_sepet_id'] = sepet.id
            context['ongoing_sepet_no'] = sepet.sepet_no[1:] if sepet.sepet_no.startswith("S") else sepet.sepet_no
            context['yuklenen_data'] = json.dumps(sepet.yuklenen or [])
        else:
            context['yuklenen_data'] = []
            context['ongoing_sepet_no'] = ''
            context['ongoing_sepet_id'] = ''

        return context
    
    def post(self, request, *args, **kwargs):
        sepet_id = request.POST.get('sepet_id')
        sepet_no = request.POST.get('sepet_no')
        sepet_bitti = request.POST.get('sepet_bitti')

        if sepet_bitti:
            sepet_termik = request.POST.get('sepet_termik')
            sepet = Sepet.objects.get(id=sepet_id)
            meta_data = sepet.meta_data or []
            meta_data.append({'Termik': sepet_termik})
            sepet.meta_data = meta_data
            sepet.bitis_saati = timezone.now()
            sepet.save()
            return JsonResponse({'success': True}, status=200)
        
        if sepet_id and sepet_no: # id varsa sepet no değiştiriliyor
            old_sepet = Sepet.objects.get(id=sepet_id)
            old_sepet.sepet_no = sepet_no
            old_sepet.save()
            return JsonResponse({'sepet_id': sepet_id})
        elif sepet_no: # yoksa yeni sepet yaratılıyor
            new_sepet = Sepet.objects.create(
                sepet_no=sepet_no,
                baslangic_saati=timezone.now(),
                pres_kodu = '4500-1'
            )
            return JsonResponse({'sepet_id': new_sepet.id})
        else:
            return JsonResponse({'error': 'Sepet No is required'}, status=400)

def get_kalip_no_list(request):
    if request.method == 'GET':
        end_time = timezone.now()
        start_time = end_time - datetime.timedelta(hours=48)
        plc_data = EventData.objects.using('dms').filter(start_time__gte=start_time, event_type='Extrusion').values_list('static_data', flat=True)
        # plc_data = PlcData.objects.using('plc4').filter(start__gte=start_time).values_list('singular_params', flat=True)
        profil_listesi = set()
        cleaned_to_original = {} 
        for singular_params in plc_data:
            if not singular_params:
                continue
            die_number = singular_params.get("DieNumber", "")
            if not die_number:
                continue
            cleaned_die_number = re.sub(r"-.*$", "", die_number).replace(" ", "")
            if cleaned_die_number not in profil_listesi:
                alt_group = KalipMuadil.objects.filter(profiller__contains=[cleaned_die_number]).first()
                if alt_group:
                    alternative_dies = set(alt_group.profiller)
                    # alternative_dies.discard(cleaned_die_number)
                    # print(f"second alternative dies: {alternative_dies}")
                    # if alternative_dies:
                    #     cleaned_die_number = next(iter(alternative_dies))
                    # alternative_dies = alt_group.profiller
                    for alternative_die in alternative_dies:
                        if alternative_die not in profil_listesi:
                            cleaned_die_number = alternative_die
                            print(f"cleaned_die_number: {cleaned_die_number}")
                profil_listesi.add(cleaned_die_number)
                # if cleaned_die_number not in cleaned_to_original:
                #     cleaned_to_original[cleaned_die_number] = []
                # cleaned_to_original[cleaned_die_number].append(die_number)
            if cleaned_die_number not in cleaned_to_original:
                cleaned_to_original[cleaned_die_number] = set()  # Use a set to avoid duplicates
            
            # Add the original die_number to the set
            cleaned_to_original[cleaned_die_number].add(die_number)
        siparis_query = SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')).exclude(SiparisTamam='BLOKE')
        siparisler = siparis_query.filter(ProfilNo__in=profil_listesi).values_list('ProfilNo', flat=True ).distinct()
        final_list = [
            original_die for cleaned_die_number, original_dies in cleaned_to_original.items()
            if cleaned_die_number in siparisler
            for original_die in original_dies
        ]
        return JsonResponse(final_list, safe=False)
    return JsonResponse({"error": "Invalid request method"}, status=400)

def get_billet_lot_list(request):
    if request.method == 'GET':
        kalip_no = request.GET.get('kalip_no')
        end_time = timezone.now()
        start_time = end_time - datetime.timedelta(hours=48)
        billet_lot_list = list(EventData.objects.using('dms').filter(start_time__gte=start_time, static_data__contains={'DieNumber':kalip_no}).values_list('static_data__BilletLot', flat=True).distinct())
        # billet_lot_list = list(PlcData.objects.using('plc4').filter(start__gte=start_time, singular_params__contains={'DieNumber':kalip_no}).values_list('singular_params__BilletLot', flat=True).distinct())
        return JsonResponse(billet_lot_list, safe=False)
    return JsonResponse({"error": "Invalid request method"}, status=400)

def get_siparis_no_list(request):
    if request.method == 'GET':
        kalip_no = request.GET.get('kalip_no')
        profil_no = re.sub(r"-.*$", "", kalip_no).replace(" ", "")
        profil_list = set()
        alt_profil_list = KalipMuadil.objects.filter(profiller__contains=[profil_no]).first()
        if alt_profil_list:
            alt_profils = alt_profil_list.profiller
            for alt in alt_profils:
                profil_list.add(alt)
        else:
            profil_list.add(profil_no)
        siparis_list = SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')).exclude(SiparisTamam='BLOKE')
        kart_list = list(siparis_list.filter(ProfilNo__in=profil_list).values_list('KartNo', flat=True ).distinct())
        return JsonResponse(kart_list, safe=False)
    return JsonResponse({"error": "Invalid request method"}, status=400)

def get_siparis_kart_info(request):
    if request.method == "GET":
        kart_no = request.GET.get('kart_no')
    try:
        orders = TestereDepo.objects.using('dies').filter(BulunduguYer='TESTERE', Adet__gte=1, KartAktif=1, Aktif=0, KartNo=kart_no) \
        .values('ProfilNo', 'Kg', 'Adet', 'FirmaAdi', 'Mm', 'Profil_Gramaj', 'YuzeyOzelligi', 'KondusyonTuru', 'BilletTuru').order_by('SonTermin')
        order_data = [
            {
                "ProfilNo": order['ProfilNo'],
                "Kg": order['Kg'],
                "Adet": order['Adet'],
                "FirmaAdi": order['FirmaAdi'],
                "Boy": order['Mm'],
                "KondusyonTuru": order['KondusyonTuru'],
                "BilletTuru": order['BilletTuru'],
                "Profil_Gramaj": order['Profil_Gramaj'],
                "YuzeyOzelligi": order['YuzeyOzelligi'],
            }
            for order in orders
        ]
        return JsonResponse({'success': True, 'orders': order_data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
def update_sepet_yuklenen(request):
    if request.method == "POST":
        sepet_id = request.POST.get('sepet_id')
        kart_no = request.POST.get('kart_no')
        kalip_no = request.POST.get('kalip_no')
        billet_lot = request.POST.get('billet_lot')
        adet = int(request.POST.get('adet'))
        try:
            sepet = Sepet.objects.get(id=sepet_id)
            
            # Yuklenende böyle bir kartno var mı bak varsa adetleri topla
            yuklenen = sepet.yuklenen or []
            found = False
            for item in yuklenen:
                if item['KartNo'] == kart_no and item['KalipNo'] == kalip_no and item['BilletLot'] == billet_lot:
                    # Kart No varsa adetleri topla
                    item['Adet'] = int(item['Adet']) + adet
                    found = True
                    break
            siparis = SiparisList.objects.using('dies').filter(KartNo=kart_no)[0]
            # Kart no yoksa yeni entry
            if not found:
                yuklenen.append({'KartNo': kart_no, 'Adet': adet, 'ProfilNo': siparis.ProfilNo, 'KalipNo':kalip_no, 'BilletLot':billet_lot, 'Boy': siparis.PlanlananMm, 'Yuzey': siparis.YuzeyOzelligi, 'Kondusyon': siparis.KondusyonTuru, 'Atandi': False})

            # Update the yuklenen field
            sepet.yuklenen = yuklenen
            sepet.save()

            # Return the updated yuklenen data as a response
            return JsonResponse({'success': True, 'yuklenen': yuklenen})

        except Sepet.DoesNotExist:
            return JsonResponse({'error': 'Sepet not found'}, status=404)

    return JsonResponse({'error': 'Invalid request method'}, status=400)
        
def delete_sepet_yuklenen(request):
    if request.method == "POST":
        sepet_id = request.POST.get('sepet_id')
        kart_no = request.POST.get('kart_no')
        kalip_no = request.POST.get('kalip_no')
        billet_lot = request.POST.get('billet_lot')
        try:
            sepet = Sepet.objects.get(id=sepet_id)
            yuklenen = sepet.yuklenen or []
            updated_yuklenen = [item for item in yuklenen if item['KartNo'] != kart_no and item['KalipNo']!=kalip_no and item['BilletLot']!=billet_lot]
            
            sepet.yuklenen = updated_yuklenen
            sepet.save()

            return JsonResponse({'success': True})
        except Sepet.DoesNotExist:
            return JsonResponse({'error': 'Sepet not found'}, status=404)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

def get_the_latest_data(queryset, datetime_field='start'):
    # send the queryset parameter ordered by datetime asc
    # bugün hariç son baskı sonundan 24 saat önce olan kayıtları getir
    now = timezone.now()
    today = now.date()
    queryset = queryset.exclude(**{f"{datetime_field}__date": today})
    print(queryset.count())
    latest_entry = queryset.order_by(f"-{datetime_field}").first()
    if not latest_entry:
        return queryset.none()
    print(latest_entry)
    latest_time = getattr(latest_entry, datetime_field)
    # time_24_hours_before = latest_time - timedelta(hours=24) #datetime


def get_profil_nos(pres):
    end_time = timezone.now()
    start_time = end_time - datetime.timedelta(hours=48)
    # get_the_latest_data(EventData.objects.using('dms').values(), 'start_time')

    ext_list = list(EventData.objects.using('dms').filter(machine_name=pres, start_time__gte=start_time, end_time__lte=end_time).values_list("static_data__DieNumber", flat=True).distinct())
    # ext_list = list(PlcData.objects.using('plc4').filter(plc = pres, start__gte = start_time, stop__lte=end_time).values_list("singular_params__DieNumber", flat=True).distinct())
 
    profil_list = list(KalipMs.objects.using('dies').filter(KalipNo__in = ext_list).values_list('ProfilNo', flat=True).distinct())
    siparis_query = SiparisList.objects.using('dies').filter(Q(PresKodu='4500-1') & Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')).exclude(SiparisTamam='BLOKE')
    gonderilecek_profiller = list(siparis_query.filter(ProfilNo__in=profil_list).values_list('ProfilNo', flat=True).distinct())
    fark_listesi = list(set(profil_list) - set(gonderilecek_profiller))
    if fark_listesi:
        for profil in fark_listesi:
            muadiller = KalipMuadil.objects.filter(profiller__contains=[profil]).first()
            if muadiller:
                # Her muadil profilin siparişi olup olmadığını kontrol ediyoruz
                for muadil in muadiller.profiller:
                    siparisler = siparis_query.filter(ProfilNo=muadil)
                    if siparisler.exists():
                        gonderilecek_profiller.append(profil)
                        break
    return gonderilecek_profiller

class Hesaplama4500View(PermissionRequiredMixin, generic.TemplateView):
    template_name = '4500/hesaplama.html'
    permission_required ="ArslanTakipApp.view_4500_uretim"

    def get_context_data(self, **kwargs):
        # Son 48 saatteki profil numaraları
        profil_nos = get_profil_nos('4500')
        
        context = super().get_context_data(**kwargs)
        context['profils'] = profil_nos

        return context
    
def get_ext_info(request): 
    if request.method == "GET":
        profil_no = request.GET.get('profil_no')  # pres kodunu da gönderelim
        end_time = timezone.now()
        start_time = end_time - datetime.timedelta(hours=50)

        try:
            alternative_dies = get_alternative_profiles(profil_no)
            events = EventData.objects.using('dms') \
                .filter(start_time__gte=start_time, end_time__lte=end_time) \
                .order_by('start_time')

            grouped_data = []
            current_group = []
            last_event = None

            for event in events:
                die = event.static_data.get("DieNumber")
                lot = event.static_data.get("BilletLot")
                kart = event.static_data.get("kartNo")

                key = (die, lot, kart)

                if not current_group:
                    current_group.append(event)
                else:
                    last = current_group[-1]
                    last_key = (
                        last.static_data.get("DieNumber"),
                        last.static_data.get("BilletLot"),
                        last.static_data.get("kartNo")
                    )

                    time_gap = (event.start_time - last.end_time).total_seconds() / 60.0  # in minutes

                    if key == last_key and time_gap <= 15:
                        current_group.append(event)
                    else:
                        grouped_data.append(current_group)
                        current_group = [event]

            if current_group:
                grouped_data.append(current_group)

            results = []

            for group in grouped_data:
                die = group[0].static_data.get("DieNumber")
                lot = group[0].static_data.get("BilletLot")
                kart = group[0].static_data.get("kartNo")

                if not die or not any(die.startswith(alt) for alt in alternative_dies):
                    continue

                brüt_imalat = sum(
                    (e.static_data.get("Billet Length Pusher", 0) or 0) * 0.1367 for e in group
                )
                billet_count = len(group)
                imalat_baslangici = min(e.start_time for e in group)
                imalat_sonu = max(e.end_time for e in group)

                if billet_count > 0:
                    average_billet_length = brüt_imalat / (billet_count * 1.367)
                else:
                    average_billet_length = 0

                ortalama_billet_boyu = round(average_billet_length, 2)
                
                results.append({
                    "kalip_no": die,
                    "billet_lot": lot,
                    "kart_no": kart,
                    "brüt_imalat": round(brüt_imalat, 2),
                    "billet_count": billet_count,
                    "imalat_baslangici": imalat_baslangici,
                    "imalat_sonu": imalat_sonu,
                    "imalat_baslangici_2": format_date_time_without_year(imalat_baslangici),
                    "imalat_sonu_2": format_date_time_without_year(imalat_sonu),
                    "ortalama_billet_boyu": ortalama_billet_boyu
                })

            return JsonResponse({'success': True, 'ext_data': results})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
def get_ext_info____old(request): 
    if request.method == "GET":
        profil_no = request.GET.get('profil_no') # pres kodunu da gönderelim
        end_time = timezone.now()
        start_time = end_time - datetime.timedelta(hours=50)

        # group by common DieNumber, BilletLot, and kartNo, but also ensure that the events are sequential.
        try:
            alternative_dies = get_alternative_profiles(profil_no)
            events = EventData.objects.using('dms').filter(start_time__gte=start_time, end_time__lte=end_time).order_by('start_time')
            
            # Step 2: Prepare for grouping
            grouped_data = []
            current_group = [] 
            last_event = None

            for event in events:
                die = event.static_data.get("DieNumber")
                lot = event.static_data.get("BilletLot")
                kart = event.static_data.get("kartNo")

                key = (die, lot, kart)

                if not current_group:
                    current_group.append(event)
                else:
                    last = current_group[-1]
                    last_key = (
                        last.static_data.get("DieNumber"),
                        last.static_data.get("BilletLot"),
                        last.static_data.get("kartNo")
                    )

                    # Check if sequential and same group
                    if key == last_key:
                        current_group.append(event)
                    else:
                        grouped_data.append(current_group)
                        current_group = [event]

            # Append last group
            if current_group:
                grouped_data.append(current_group)

            # Step 3: Calculate aggregates per group
            results = []

            for group in grouped_data:
                die = group[0].static_data.get("DieNumber")
                lot = group[0].static_data.get("BilletLot")
                kart = group[0].static_data.get("kartNo")

                if not die or not any(die.startswith(alt) for alt in alternative_dies):
                    continue

                brüt_imalat = sum(
                    (e.static_data.get("Billet Length Pusher", 0) or 0) * 0.1367 for e in group
                )
                billet_count = len(group)
                imalat_baslangici = min(e.start_time for e in group)
                imalat_sonu = max(e.end_time for e in group)

                if billet_count > 0:  # Prevent division by zero
                    average_billet_length = brüt_imalat / (billet_count * 1.367)
                else:
                    average_billet_length = 0  # Handle the case when billet_count is zero or invalid

                ortalama_billet_boyu = round(average_billet_length, 2)
                
                results.append({
                    "kalip_no": die,
                    "billet_lot": lot,
                    "kart_no": kart,
                    "brüt_imalat": round(brüt_imalat, 2),
                    "billet_count": billet_count,
                    "imalat_baslangici": imalat_baslangici,
                    "imalat_sonu": imalat_sonu,
                    "imalat_baslangici_2": format_date_time_without_year(imalat_baslangici),
                    "imalat_sonu_2": format_date_time_without_year(imalat_sonu),
                    "ortalama_billet_boyu": ortalama_billet_boyu
                })
            return JsonResponse({'success': True, 'ext_data': results})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
def get_ext_info_old(request): 
    # her satır için ortalama billet boyu:
    # brüt / (billet sayısı * 1,367)
    if request.method == "GET":
        profil_no = request.GET.get('profil_no') # pres kodunu da gönderelim
        end_time = timezone.now()
        start_time = end_time - datetime.timedelta(hours=48)
        
        try:
            alternative_dies = get_alternative_profiles(profil_no)

            q = Q()
            for die in alternative_dies:
                q |= Q(static_data__DieNumber__startswith=die)
            queryset = (
                EventData.objects.using('dms').filter(
                    start_time__gte=start_time, end_time__lte=end_time
                )
                .filter(q)
                .annotate(
                    kart_no=Cast(F("static_data__kartNo"), CharField()),
                    kalip_no=F("static_data__DieNumber"),
                    billet_count=Count(F("static_data__DieNumber")),
                    brüt_imalat=ExpressionWrapper(
                        Sum(Cast(F("static_data__Billet Length Pusher"), FloatField())) * 0.1367,
                        output_field=FloatField()
                    ),
                    billet_lot=F("static_data__BilletLot")
                )
                .values(
                    "kart_no",
                    "kalip_no",
                    "billet_lot"
                )
                .annotate(
                    imalat_baslangici=Min("start_time"),
                    imalat_sonu=Max("end_time"),
                    billet_count=F("billet_count"),
                    brüt_imalat=F("brüt_imalat")
                )
                .order_by("imalat_baslangici")
            )
            for e in queryset:
                e['imalat_baslangici_2'] = format_date_time_without_year(e['imalat_baslangici'])
                e['imalat_sonu_2'] = format_date_time_without_year(e['imalat_sonu'])
                if e['billet_count'] > 0:  # Prevent division by zero
                    average_billet_length = e['brüt_imalat'] / (e['billet_count'] * 1.367)
                else:
                    average_billet_length = 0  # Handle the case when billet_count is zero or invalid

                e['ortalama_billet_boyu'] = round(average_billet_length, 2)

            ext_data = list(queryset)
            return JsonResponse({'success': True, 'ext_data': ext_data})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

def get_sepet_info(request):
    if request.method == "GET":
        profil_no = request.GET.get('profil_no') # pres kodunu da gönderelim
        end_time = timezone.now()
        end_48_time = end_time - datetime.timedelta(hours=50)
        
        alternative_dies = get_alternative_profiles(profil_no)
        q = Q()
        w = Q()
        for die in alternative_dies:
            q |= Q(static_data__DieNumber__startswith=die)
            w |= Q(yuklenen__contains=[{'ProfilNo': die, 'Atandi': False}]) 
        
        start = EventData.objects.using('dms').filter(start_time__gte=end_48_time, end_time__lte=end_time).filter(q).values('start_time', 'end_time').order_by('start_time')[0]['start_time']
        # start = PlcData.objects.using('plc4').filter(start__gte=end_48_time, stop__lte=end_time).filter(q).values('start', 'stop').order_by('start')[0]['start']
        sepet = Sepet.objects.filter(baslangic_saati__gte=start).filter(w).values().order_by('baslangic_saati') # profil no ile filtrele
        try:
            sepet_data = []

            for s in sepet:
                for item in s['yuklenen']:
                    if item.get("ProfilNo") in alternative_dies:
                        elem = {
                            "id": s['id'],
                            "SepetNo": s["sepet_no"],
                            "Adet": item["Adet"],
                            "KartNo": item["KartNo"],
                            "Boy": item["Boy"]
                        }
                        if item.get("KalipNo"):
                            elem = {
                                "id": s['id'],
                                "SepetNo": s["sepet_no"],
                                "Adet": item["Adet"],
                                "KartNo": item["KartNo"],
                                "KalipNo": item["KalipNo"],
                                "BilletLot": item["BilletLot"],
                                "Boy": item["Boy"]
                            }
                        sepet_data.append(elem)
            return JsonResponse({'success': True, 'sepet_data': sepet_data})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

def get_kart_info(request):
    if request.method == "GET":
        try:
            profil_no = request.GET.get('profil_no') # pres kodunu da gönderelim
            alternative_dies = get_alternative_profiles(profil_no)

            siparis_query = SiparisList.objects.using('dies').filter(Q(PresKodu='4500-1') & Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')).exclude(SiparisTamam='BLOKE')
            siparisler = siparis_query.filter(ProfilNo__in=alternative_dies).values('Kimlik', 'KartNo', 'Kg', 'Adet', 'PlanlananMm', 'SonTermin', 'FirmaAdi', 'KondusyonTuru', 'YuzeyOzelligi', 'Profil_Gramaj').order_by('SonTermin', '-PlanlananMm')
            # siparisler = SiparisList.objects.using('dies').filter(KartNo__in = ['312578', '312579', '312580', '312581', '312582', '312583', '312584']).values('Kimlik', 'KartNo', 'Kg', 'Adet', 'PlanlananMm', 'SonTermin', 'FirmaAdi', 'KondusyonTuru', 'YuzeyOzelligi', 'Profil_Gramaj').order_by('SonTermin')
            for s in siparisler:
                s["FirmaAdi"] = s['FirmaAdi'].split(' ')[0]
                s['SonTermin'] = format_date(s['SonTermin'])
            list_siparisler = list(siparisler)

            return JsonResponse({'success': True, 'siparis_data': list_siparisler}, safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
def sepete_dagit(request):
    if request.method == 'POST':
        try:
            profil_no = request.POST.get('profil')
            profil_gr = request.POST.get('profil_gr')
            secilen_ext = json.loads(request.POST.get('secilen_ext'))
            secilen_sepet = json.loads(request.POST.get('secilen_sepet'))
            secilen_siparis = json.loads(request.POST.get('secilen_siparis'))
            kart_dagilimi = json.loads(request.POST.get('sonuc_kartlar')) # kartları neyle birlikte kaydetmeliyim
            gelen_sepetler = json.loads(request.POST.get('sonuc_sepetler'))
            sepetler_grouped = {}
            alternative_dies = get_alternative_profiles(profil_no)

            kart_nos = [sepet["KartNo"] for sepet in gelen_sepetler]
            siparis_list = {siparis.KartNo: siparis for siparis in SiparisList.objects.using('dies').filter(KartNo__in=kart_nos)}

            for sepet in gelen_sepetler:
                sepet_id = sepet["id"]
                kart_no = sepet["KartNo"]

                if sepet_id not in sepetler_grouped:
                    sepetler_grouped[sepet_id] = []
                siparis = siparis_list.get(kart_no) # SiparisList.objects.using('dies').filter(KartNo=kart_no)[0]
                if siparis:
                    sepetler_grouped[sepet_id].append({"KartNo": kart_no, "Adet":sepet["Adet"], "Boy": sepet["Boy"], "ProfilNo":profil_no, "Yuzey": siparis.YuzeyOzelligi, 
                                                   "BilletLot": sepet["BilletLot"], "KalipNo":sepet["KalipNo"], "Kondusyon": siparis.KondusyonTuru, "Atandi": True})

            grouped_sepetler = [{"id": sepet_id, "items": items} for sepet_id, items in sepetler_grouped.items()]
            print(grouped_sepetler)
            with transaction.atomic():
                for sepetler in grouped_sepetler:
                    sepet = Sepet.objects.get(id=sepetler['id']) 
                    yuklenen_veri = sepet.yuklenen
                    # ProfilNo ile eşleşen eski verileri sil
                    yuklenen_veri = [item for item in yuklenen_veri if item["ProfilNo"] not in alternative_dies]
                    for item in sepetler['items']:
                        yuklenen_veri.append(item)
                    sepet.yuklenen = yuklenen_veri
                    sepet.save()
                KartDagilim.objects.create(
                    profil_no = profil_no,
                    profil_gr = profil_gr,
                    secilen_ext = secilen_ext,
                    secilen_sepet = secilen_sepet,
                    secilen_siparis = secilen_siparis,
                    dagitilan_kartlar = kart_dagilimi
                )

            return JsonResponse({'success': True}, safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

def get_sepetler(pres):
    # içinde Atandi = False olan sepet listesini getirs
    sepetler = Sepet.objects.filter(yuklenen__contains=[{'Atandi':False}]).order_by('-baslangic_saati').values()

    data = json.dumps(list(sepetler), sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

class Sepetler4500View(generic.TemplateView):
    template_name = '4500/sepetler.html'

def sepet_get_kalip_no_list(request):
    if request.method == 'GET':
        end_time = timezone.now()
        start_time = end_time - datetime.timedelta(hours=48)
        plc_data = EventData.objects.using('dms').filter(start_time__gte=start_time).values_list('static_data', flat=True)
        # plc_data = PlcData.objects.using('plc4').filter(start__gte=start_time).values_list('singular_params', flat=True)
        profil_listesi = set()
        cleaned_to_original = {} 
        for singular_params in plc_data:
            if not singular_params:
                continue
            die_number = singular_params.get("DieNumber", "")
            if not die_number:
                continue
            cleaned_die_number = re.sub(r"-.*$", "", die_number).replace(" ", "")
            if cleaned_die_number not in profil_listesi:
                alt_group = KalipMuadil.objects.filter(profiller__contains=[cleaned_die_number]).first()
                if alt_group:
                    alternative_dies = set(alt_group.profiller)
                    alternative_dies.discard(cleaned_die_number)
                    if alternative_dies:
                        cleaned_die_number = next(iter(alternative_dies))
                profil_listesi.add(cleaned_die_number)
            if cleaned_die_number not in cleaned_to_original:
                cleaned_to_original[cleaned_die_number] = set()
            
            cleaned_to_original[cleaned_die_number].add(die_number)
        siparis_query = SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')).exclude(SiparisTamam='BLOKE')
        siparisler = siparis_query.filter(ProfilNo__in=profil_listesi).values_list('ProfilNo', flat=True ).distinct()
        final_list = [
            original_die for cleaned_die_number, original_dies in cleaned_to_original.items()
            if cleaned_die_number in siparisler
            for original_die in original_dies
        ]
        return JsonResponse(final_list, safe=False)
    return JsonResponse({"error": "Invalid request method"}, status=400)

def sepet_get_billet_lot_list(request):
    if request.method == 'GET':
        kalip_no = request.GET.get('kalip_no')
        end_time = timezone.now()
        start_time = end_time - datetime.timedelta(hours=48)
        billet_lot_list = list(EventData.objects.using('dms').filter(start_time__gte=start_time, static_data__contains={'DieNumber':kalip_no}).values_list('static_data__BilletLot', flat=True).distinct())
        # billet_lot_list = list(PlcData.objects.using('plc4').filter(start__gte=start_time, singular_params__contains={'DieNumber':kalip_no}).values_list('singular_params__BilletLot', flat=True).distinct())
        return JsonResponse(billet_lot_list, safe=False)
    return JsonResponse({"error": "Invalid request method"}, status=400)

def sepet_get_siparis_no_list(request):
    if request.method == 'GET':
        kalip_no = request.GET.get('kalip_no')
        profil_no = re.sub(r"-.*$", "", kalip_no).replace(" ", "")
        profil_list = set()
        alt_profil_list = KalipMuadil.objects.filter(profiller__contains=[profil_no]).first()
        if alt_profil_list:
            alt_profils = alt_profil_list.profiller
            for alt in alt_profils:
                profil_list.add(alt)
        else:
            profil_list.add(profil_no)
        siparis_list = SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')).exclude(SiparisTamam='BLOKE')
        kart_list = list(siparis_list.filter(ProfilNo__in=profil_list).values_list('KartNo', flat=True ).distinct())
        return JsonResponse(kart_list, safe=False)
    return JsonResponse({"error": "Invalid request method"}, status=400)
    
def update_sepet(request):
    if request.method == "POST":
        sepet_id = request.POST.get('sepet_id')
        sepet_no = request.POST.get('sepet_no')
        yuklenen_data = json.loads(request.POST.get('yuklenen'))
        new_data = []
        try:
            sepet = Sepet.objects.get(id=sepet_id)
            sepet.sepet_no = sepet_no
            for y in yuklenen_data: 
                siparis = SiparisList.objects.using('dies').filter(KartNo=y['KartNo'])[0] # kalipno, billetlot ve kart no seçilsin
                row = {"KartNo": y['KartNo'], "Adet": y['Adet'], "KalipNo":y["KalipNo"], "BilletLot": y["BilletLot"], 'ProfilNo': siparis.ProfilNo, 'Boy': siparis.PlanlananMm, 'Yuzey': siparis.YuzeyOzelligi, 'Kondusyon': siparis.KondusyonTuru, 'Atandi': False}
                new_data.append(row)
            
            sepet.yuklenen = new_data
            sepet.save()

            # Return the updated yuklenen data as a response
            return JsonResponse({'success': True})

        except Sepet.DoesNotExist:
            return JsonResponse({'error': 'Sepet not found'}, status=404)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

class saw4500View(generic.TemplateView):
    template_name = '4500/saw.html'

def get_position_data(position):
    query = EventData.objects.using('dms').filter(static_data__position=position, static_data__count__gt = 0).order_by('-id')
    # query = PlcData.objects.using('plc4').filter(position=position, count__gt = 0).order_by('-id') # node redde order by count desc şeklinde
    print(query.values('id', 'count'))
    
    return query

class FinishSaw4500View(generic.TemplateView):
    template_name = '4500/finishsaw.html'

def get_saw_table(request):
    exts = EventData.objects.using('dms').filter(static_data__position="saw table", static_data__count__gt=0).order_by('-id')
    # exts = PlcData.objects.using('plc4').filter(position="saw table", count__gt=0).order_by('-id')
    
    colors = ["#698BAA", "#7DB1CB", "#8DD3DE", "#B1E4F1", "#62A4A0"]
    color_index = 0
    last_sarj_no = ""
    
    data = []
    for ext in exts:
        print(ext)
        if ext.static_data.get('BilletLot') != last_sarj_no:
            color_index = (color_index + 1) % len(colors)
            last_sarj_no = ext.static_data.get('BilletLot')

        data.append({
            "id": ext.id,
            "count": ext.static_data.get('count'),
            "len": float(ext.static_data.get('ProfileLength', 0)),
            "sarj_no": ext.static_data.get('BilletLot', ""),
            "kalip_no": ext.static_data.get('DieNumber', ""),
            "figur": int(ext.static_data.get('figur', 0)),
            "color": colors[color_index]
        })

    return JsonResponse({"data": data})

def get_position_data(position):
    return EventData.objects.using('dms').filter(static_data__position=position, static_data__count__gt=0).order_by('-id')
    # return PlcData.objects.using('plc4').filter(position=position, count__gt=0).order_by('-id')

def get_saw_data(request):
    saw_table = list(get_position_data('saw table').values('id', 'static_data__count', 'static_data'))
    saw_line = list(get_position_data('saw line').values('id', 'static_data__count', 'static_data'))
 
    return JsonResponse({'saw_table': saw_table, 'saw_line': saw_line})

def kesime_al(request):
    if request.method == 'GET':
        try:
            adet = int(request.GET.get('adet'))
            # record_ids = list(PlcData.objects.using('plc4').filter(position='saw table').order_by('id').values_list('id', flat=True)[:adet])            
            # count = PlcData.objects.using('plc4').filter(id__in=record_ids).update(position='saw line')
            unique_counts = list(EventData.objects.using('dms').filter(static_data__position='saw table').order_by('static_data__count').values_list('static_data__count', flat=True).distinct()[:adet])
            for obj in EventData.objects.using('dms').filter(static_data__count__in = unique_counts): #.update(static_data__position='saw line')
                static_data = obj.static_data
                static_data['position'] = 'saw line'

                obj.static_data = static_data
                obj.save()
            # unique_counts = list(PlcData.objects.using('plc4').filter(position='saw table').order_by('count').values_list('count', flat=True).distinct()[:adet])
            # update_position = PlcData.objects.using('plc4').filter(count__in = unique_counts).update(position='saw line')
            
            return JsonResponse({'success': True}, safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
def testere_tezgahi(request):
    if request.method == 'GET':
        try:
            max_count = EventData.objects.using('dms').filter(static_data__position='saw line').latest('id').count
            # max_count = PlcData.objects.using('plc4').filter(position='saw line').latest('id').count  #aggregate(Max('count'))['count__max']s
            data = get_position_data('saw line').filter(static_data__count=max_count).values()
            return JsonResponse(list(data), safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
def testere_siparis_list(request):
    if request.method == 'GET':
        # position saw line olanların profil nolarını al
        try:
            profil_list = list(EventData.objects.using('dms').filter(static_data__position = 'saw line').values_list('static_data__profiles', flat=True).distinct())
            # profil_list = list(PlcData.objects.using('plc4').filter(position = 'saw line').values_list('singular_params__profiles', flat=True).distinct())
            testere = TestereDepo.objects.using('dies').filter(ProfilNo__in = profil_list, PresKodu='4500-1', BulunduguYer='TESTERE', Adet__gte=1) \
            .annotate(Bloke=Case(When(Aktif=0, then=Value('AÇIK')), default=Value('BLOKELİ'), output_field=CharField())) \
            .values('ProfilNo', 'KartNo', 'Mm', 'Adet', 'Kg', 'BilletTuru', 'YuzeyOzelligi', 'PresKodu', 'SonTermin', 'Bloke').order_by('SonTermin', '-Mm')
            # print(f"testere: {testere}")
            return JsonResponse(list(testere), safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})        

def testere_kesim_bitti(request):
    if request.method == 'GET':
        try:
            EventData.objects.using('dms').filter(static_data__position='saw line').update(static_data__position='stacker')
            # PlcData.objects.using('plc4').filter(position='saw line').update(position='stacker')
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class YudaNewView(generic.TemplateView): 
    template_name = 'Yuda/yuda.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if the user is a member of either group, it's to show the yetki field to the user if they are not in the groups
        is_in_group = (
            self.request.user.groups.filter(name="Yurt Disi Satis Bolumu").exists() or
            self.request.user.groups.filter(name="Yurt Ici Satis Bolumu").exists()
        )
        # Add the is_in_group variable to the context
        context['is_in_group'] = is_in_group
        return context

def yuda_get_profil_list(request):
    query = request.GET.get('query', '')  # Get the search term
    profiles = ProfilMs.objects.using('dies').filter(ProfilNo__startswith=query).values('Kimlik', 'ProfilNo')[:200]  # Limit to 200 results for performance
    
    profiles_data = [{'id': profile['ProfilNo'], 'name': profile['ProfilNo']} for profile in profiles]
    
    return JsonResponse({'profiles': profiles_data})

def generate_yuda_no(parent: Yuda = None) -> str:
    now = datetime.datetime.now()
    if parent:
        # Count how many children the parent already has
        child_count = parent.children.count()
        return f"{parent.yuda_no}-{str(child_count + 1).zfill(3)}"
    else:
        # Count today's top-level yudas (without a parent)
        count_today = Yuda.objects.filter(create_time__date=now.date(), parent__isnull=True).count()
        sequential_number = str(count_today + 1).zfill(3)
        return f"{now.year}-{now.strftime('%m%d')}-{sequential_number}"

def extract_from_request_data(request: dict) -> dict:
    """Constructs meta_data and the flags from the request."""
    meta_data = {}
    is_old_profile = False
    has_mekanik = 0
    satis_yetki = ""
    meta_data["OnayDurumu"] = "Kalıphane Onayı Bekleniyor"

    for key, value in request.items():
        if value != "":
            if key == "ProjeTipi" or key == "MevcutProfil":
                meta_data[key] = value
                if value == "Mevcut Profil":
                    is_old_profile = True
            elif key == "TalasliImalat" and value == "Var":
                has_mekanik = 1
            elif key == "BirlikteCalisan":
                meta_data[key] = value.split(',')
            elif key != "parent_id":
                meta_data[key] = value
            elif key == "Yetki":
                satis_yetki = value

    if satis_yetki == "":
        if request.user.groups.filter(name='Yurt Ici Satis Bolumu').exists():
            satis_yetki = 'Yurt Ici Satis Bolumu'
        elif request.user.groups.filter(name='Yurt Disi Satis Bolumu').exists():
            satis_yetki =  'Yurt Disi Satis Bolumu'
    
    if is_old_profile:
        onay_durumu = determine_onay_durumu({'kaliphane': 2, 'mekanik': has_mekanik, 'satis': 1})
        meta_data["OnayDurumu"] = onay_durumu

    return meta_data, is_old_profile, satis_yetki

def get_yuda_group_names(meta_data, satis_yetki):
    """Get the group names to assign permissions based on meta_data."""
    group_names = ['Ust Yonetim Bolumu', 'Planlama Bolumu', 'Kalite Bolumu', 'Kaliphane Bolumu', 'Pres Bolumu', 'Proje Bolumu', satis_yetki]
    group_mapping = {'Paketleme': 'Paketleme Bolumu', 'YuzeyEloksal': 'Eloksal Bolumu', 'YuzeyAhsap': 'Ahsap Kaplama Bolumu', 
                        'YuzeyBoya': 'Boyahane Bolumu', 'TalasliImalat': 'Mekanik Islem Bolumu'}
    yuda_meta_data = {'Paketleme': 'Ozel Paketleme', 'TalasliImalat': 'Var'}

    for field, group in group_mapping.items():
        if field in meta_data:
            if yuda_meta_data[field] == meta_data[field]:
                group_names.append(group)
            elif field not in yuda_meta_data:
                group_names.append(group)
    
    return group_names

def create_yuda_vote_and_comment(yuda):
    """Create a YudaVote and comment."""
    YudaOnay.objects.create(Group=Group.objects.get(name='Kaliphane Bolumu'), Yuda_id=yuda.id, OnayDurumu=True)
    mevcut_profil = yuda.meta_data['MevcutProfil']
    profil = f"'{mevcut_profil}' numaralı mevcut profil"
    if ',' in mevcut_profil:
        mevcut_profil = mevcut_profil.replace(",", "', '")
        profil = f"'{mevcut_profil}' numaralı mevcut profiller"

    Comment.objects.create(
        Kullanici_id=57, FormModel="YudaForm", FormModelId=yuda.id, Tarih=datetime.datetime.now(),
        Aciklama=f"Yeni proje, {profil} için açıldığından, sistem tarafından otomatik olarak Kalıphane onayı verilmiştir."
    )
    
def add_yuda_files(req_files, file_titles, yuda):
    for file, title in zip(req_files, file_titles):
        UploadFile.objects.create(
            File = file,
            FileTitle = title,
            FileSize = file.size,
            FileModel = "YudaForm",
            FileModelId = yuda.id,
            UploadedBy = yuda.created_by,
            Note = "",
        )

def create_yuda_notification(yuda):
    allowed_groups = [group for group, perms in get_groups_with_perms(yuda, attach_perms=True).items() if 'gorme_yuda' in perms]
    for u in User.objects.filter(groups__in=allowed_groups).exclude(id=yuda.created_by__id):
        notification = Notification.objects.create(
            user=u,
            message=f'{yuda.meta_data["MusteriFirmaAdi"][:11]}.. için bir YUDA ekledi.',
            subject=f"Yeni YUDA",
            where_id=yuda.id,
            new_made_by = yuda.created_by,
            col_marked = "#E9ECEF",
        )
        logger.debug(f"YUDA Notification is created. ID: {notification.id}, Time: {notification.timestamp.strftime('%d-%m-%y %H:%M')}")
    
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'notifications_{yuda.created_by__id}',
            {
                'type': 'send_notification',
                'notification': {
                    'id': notification.id,
                    'subject': notification.subject,
                    'made_by': get_user_full_name(notification.new_made_by_id),
                    'message': notification.message,
                    'where_id': notification.where_id,
                    'is_read': notification.is_read,
                    'timestamp': notification.timestamp.strftime('%d-%m-%y %H:%M'),
                    'is_marked': notification.is_marked,
                },
            }
        )
        logger.debug(f"YUDA Notification is sent. ID: {notification.id}, Time: {notification.timestamp.strftime('%d-%m-%y %H:%M')}")

def yuda_create(request):
    if request.method == 'POST':
        for attempt in range(3):
            try:
                with transaction.atomic():
                    yuda = Yuda()
                    yuda.created_by = request.user
                    parent_id = request.POST.get("parent_id")
                    parent = None
                    if parent_id:
                        parent = get_object_or_404(Yuda, id = parent_id)

                    yuda.parent = parent
                    yuda.yuda_no = generate_yuda_no(parent)
                    
                    meta_data, is_old_profile, satis_yetki = extract_from_request_data(request.POST)
                    yuda.meta_data = meta_data
                    yuda.save()

                    assign_perm("gorme_yuda", request.user, yuda) # Assign permission to the current user
                    assign_perm("acan_yuda", request.user, yuda) # Yudayı açan kişiye değiştirme ve görme yetkisi ver

                    if meta_data['MusteriFirmaAdi']!='DENEME':
                        group_names = get_yuda_group_names(meta_data, satis_yetki)
                        groups = [Group.objects.get(name=name) for name in group_names]
                        for group in groups:
                            assign_perm("gorme_yuda", group, yuda)
                    
                    if is_old_profile:
                        create_yuda_vote_and_comment(yuda)

                    file_titles = request.POST.getlist('fileTitles[]')
                    request_files = request.FILES.getlist('files[]')
                    add_yuda_files(request_files, file_titles)

                    if request.user.id != 1:
                        create_yuda_notification(yuda)

                return JsonResponse({'message': 'Kayıt başarılı', 'id': yuda.id})
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Geçersiz JSON formatı', 'status': 'false'}, status=500)
            except IntegrityError:
                time.sleep(0.1)
                continue
            except Exception as e:
                return JsonResponse({'error': str(e), 'status':'false'}, status = 500)

class KaliphaneIsEmriView(generic.TemplateView):
    template_name = 'Kaliphane/is_emri_kg.html'

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     # sayfanın tablerini getirmek için kullanılabilir. 
    #     # context['is_in_group'] = is_in_group
    #     return context

stok_kodu_map = {
    'PORTOL DİŞİ': 'Varyant6',
    'PORTOL KÖPRÜ': 'Varyant7',
    'DESTEK': 'Varyant8',
    '': 'Varyant',
    '': 'Varyant',
    '': 'Varyant',
}
    
def kaliphane_get_tab_info(request):
    if request.method == 'GET':
        # operasyon = request.GET.get('operasyon') # TESTERE ya da ISIL İŞLEM olacak
        # hangi operasyon? 
        # hangi operasyonsa bu operasyonun başlatılmış iş emri var mı ona bak
        # yoksa açık iş emirlerinin bir listesini getir
        # varsa başlatılmış iş emri gösterilsin 
        # isemri durum = 'BASLAMADI' ise İş Emri eklenmiş fakat henüz üretime başlanmamış
        # varyant1=pres, varyant2=figür, varyant3=çap, varyant4=hazne, varyant5=sadecekalıp, varyant6=kapak, 
        # varyant7=köprü, varyant8=destek, varyant9=yanno, varyant10=bolster, varyant11=mührepaketboyu
        # iş emri listesinde gösterilecek olan sütunlar:
        # UrtKimlik, Tree_StokKodu, Varyant9, Çap, StokKodu, StokKoduna bağlı varyant as Kesim Boyu, Kesim Boyu-5 as Gerçek Ölçü
        is_emris = KaliphaneIsEmri.objects.using('kh').filter(Durum='BASLAMADI', OperasyonKodu='TESTERE').values()
        for emir in is_emris:
                emir['KesimBoyu'] = stok_kodu_map(emir['StokKodu'])
                emir['GercekOlcu'] = emir['KesimBoyu'] - 5
