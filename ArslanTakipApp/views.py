from collections import OrderedDict, defaultdict
import logging
import re
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
from .models import Location, Kalip, Hareket, KalipMs, DiesLocation, PresUretimRaporu, SiparisList, EkSiparis, LivePresFeed, YudaOnay, Parameter, UploadFile, YudaForm, Comment, Notification, EkSiparisKalip
from django.template import loader
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator
from guardian.shortcuts import get_objects_for_user, assign_perm, get_groups_with_perms
from guardian.models import UserObjectPermission, GroupObjectPermission
from django.db.models import Q, Sum, Max, Count, Case, When, ExpressionWrapper, fields, OuterRef, Subquery, FloatField, F, DateTimeField, TimeField, DurationField, IntegerField
from django.db.models.functions import Cast
from django.db import transaction 
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
# from aes_cipher import *
# from Crypto.Cipher import AES
# from Crypto.Util.Padding import pad, unpad
import locale
from .forms import PasswordChangingForm
from .dxfsvg import dxf_file_area_calculation
from django.core.exceptions import PermissionDenied
from django.utils.dateformat import DateFormat
from mailer import send_mail
from django.db.models.functions import ExtractHour, ExtractMinute
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

def format_date_time_s(date):
    return date.strftime("%d-%m-%Y %H:%M:%S")

def format_date_time(date):
    return date.strftime("%d-%m-%Y %H:%M")

def format_date(date):
    return date.strftime("%d-%m-%Y")

def guncelle(i, b, u):
    for j in b:
        if i == 'KalipNo':
            k = KalipMs.objects.using('dies').get(KalipNo = j[0])
            kalip = Kalip()
            kalip.KalipNo = k.KalipNo
            kalip.ProfilNo = k.ProfilNo
            kalip.Kimlik = k.Kimlik
            kalip.FirmaKodu = k.FirmaKodu
            kalip.FirmaAdi = k.FirmaAdi
            kalip.Cinsi = k.Cinsi
            kalip.Miktar = k.Miktar
            kalip.Capi = k.Capi
            kalip.UretimTarihi = k.UretimTarihi
            kalip.GozAdedi = k.GozAdedi
            kalip.Silindi = k.Silindi
            kalip.SilinmeSebebi =k.SilinmeSebebi
            kalip.Bolster = k.Bolster
            kalip.KalipCevresi = k.KalipCevresi
            kalip.KaliteOkey = k.KaliteOkey
            kalip.UreticiFirma = k.UreticiFirma
            kalip.TeniferOmruMt = k.TeniferOmruMt
            kalip.TeniferOmruKg = k.TeniferOmruKg
            kalip.TeniferKalanOmurKg = k.TeniferKalanOmurKg
            kalip.TeniferNo = k.TeniferNo
            kalip.SonTeniferTarih = k.SonTeniferTarih
            kalip.SonTeniferKg = k.SonTeniferKg
            kalip.SonTeniferSebebi = k.SonTeniferSebebi
            kalip.SonUretimTarih = k.SonUretimTarih
            kalip.SonUretimGr = k.SonUretimGr
            kalip.UretimTenSonrasiKg = k.UretimTenSonrasiKg
            kalip.UretimToplamKg = k.UretimToplamKg
            kalip.ResimGramaj = k.ResimGramaj
            kalip.KalipAciklama = k.KalipAciklama
            kalip.SikayetVar = k.SikayetVar
            kalip.KaliteAciklama = k.KaliteAciklama
            kalip.AktifPasif = k.AktifPasif
            kalip.Hatali = k.Hatali
            kalip.PresKodu  = k.PresKodu
            kalip.PaketBoyu = k.PaketBoyu
            kalip.ResimDizini = k.ResimDizini
            kalip.kalipLocation_id = 48
            
            kalip.save()
            print("kalip saved")
        else:
            print(i)
            u[i] = j[1]
            Kalip.objects.filter(KalipNo = j[0]).update(**u)
            print("updated")
    return True

def hareketSave(dieList, lRec, dieTo, request):
    for i in dieList:
        k = DiesLocation.objects.get(kalipNo = i)
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

@permission_required("ArslanTakipApp.view_location") #izin yoksa login sayfasına yönlendiriyor
@login_required #user must be logged in
def location(request):
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
                dieTo = Location.objects.get(locationRelationID = dieTo, locationName__contains = "ONAY").id
                
            if gozCapacity == None:
                hareketSave(dieList, lRec, dieTo, request)
            else:
                firinKalipSayisi = DiesLocation.objects.filter(kalipVaris_id = lRec.id).count()
                if firinKalipSayisi < gozCapacity:
                    if not (firinKalipSayisi + len(dieList)) > gozCapacity:
                        hareketSave(dieList, lRec, dieTo, request)
            response = JsonResponse({'message': "Kalıplar Başarıyla Gönderildi."})
        except Exception as e:
            response = JsonResponse({'error':  'İşlem gerçekleştirilemedi. ' + str(e)})
        
        return response
    return render(request, 'ArslanTakipApp/location.html', {'location_json':data, 'gonder_json':gonderData})

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
                if i["type"] == "like":
                    q[i['field']+"__startswith"] = i['value']
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
            s = kal.get(KalipNo=b['kalipNo'])
            if s.Silindi == 1 or s.AktifPasif == 'Pasif':
                a.remove(b)
            c = kal.get(KalipNo=b['kalipNo']).Hatali
            if c==1:
                b['Hatali'] = 1
        #print(a)
        kalip_count = query.count()
        lastData= {'last_page': math.ceil(kalip_count/size), 'data': [], 'sayi': sayi}
        lastData['data'] = a #list(query.values()[(page-1)*size:page*size])
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
            hareket = Hareket()
            hareket.kalipVaris_id = 48
            hareket.kalipNo = c['KalipNo']
            hareket.kimTarafindan_id = 1
            hareket.save()
            print("Hareket saved")
        #print(b)
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
def location_hareket(request):
    params = json.loads(unquote(request.GET.get('params')))
    size = params["size"]
    page = params["page"]
    filter_list = params["filter"]

    hareket_count = 0
    lastData= {'last_page': math.ceil(hareket_count/size), 'data': []}

    if len(filter_list)>0:
        hareketK = filter_list[0]['value']
        hareketQuery = Hareket.objects.all()
        location_list = Location.objects.values()
        hareketQuery = list(hareketQuery.values().filter(kalipNo=hareketK).order_by("-hareketTarihi"))
        kalip_l = list(DiesLocation.objects.filter(kalipNo=hareketK).values())
        users = User.objects.values()
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

        lastData= {'last_page': math.ceil(hareket_count/size), 'data': []}
        lastData['data'] = list(harAr[(page-1)*size:page*size])
                
    #print(lastData)
    data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

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
            response = JsonResponse({'message': 'Kayıt başarılı'})
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

def qrKalite(request):
    if request.method == "GET":
        """ path = request.get_full_path()
        print(path)
        print(path.rsplit('/', 1)[-1]) """
        """ sepetArray = []
        # Şifre oluşturma
        for i in range(100,251): #250 if i<10: 
            sepet = "S" + str(i)
            encSepet = encrypt_aes_ecb(key, sepet)
            hexSepet = binascii.hexlify(encSepet)
            print(hexSepet)
            #encode mu kullanmıştım??
            decodedString = hexSepet.decode('utf-8') #??sanırım buydu
            print(decodedString)
            s = sepet + ", " + str(decodedString)
            sepetArray.append(s)
        print(sepetArray)
        f = open("QRsepet2.csv", "a")
        for j in sepetArray:
            f.write(j+"\n")
        f.close() """
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
        context = {
            "type" : "deneme",
            "no": "denemee"
        }

    # location = Location.objects.all()
    # group = Group.objects.get(name="KalipTamYetki")
    # for l in location:
    #     assign_perm("dg_view_location", group, l)
    
    return render(request, 'ArslanTakipApp/qrKalite.html', context)

def qrKalite_deneme(request):
    user = request.user
    message = "Yuda Kaydet"
    y = YudaForm.objects.get(id=107)

    allowed_groups = [group for group, perms in get_groups_with_perms(y, attach_perms=True).items() if 'gorme_yuda' in perms]

    try: 
        # for u in allowed_users:
        for u in User.objects.filter(groups__in=allowed_groups).exclude(id=request.user.id):
            print(u)
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
    pKodu = eksiparis.EkPresKodu
    presId = presler[pKodu]
    firinId = firinlar[pKodu]
    try:
        pres = Location.objects.get(id=presId)
        location = DiesLocation.objects.filter(kalipVaris=pres).first()
        if location: # preste kalıp var mı
            die = KalipMs.objects.using('dies').filter(KalipNo=location.kalipNo).first()
            if die and die.ProfilNo == pNo: # siparişin kalıbı mı
                return 1 # üretimi bitir
            else:
                gozler = Location.objects.filter(locationRelationID=firinId)
                kalipList = DiesLocation.objects.filter(kalipVaris__in=gozler).values_list('kalipNo', flat=True)
                kaliplar = KalipMs.objects.using('dies').filter(KalipNo__in= list(kalipList), ProfilNo=pNo).values_list('KalipNo', flat=True)
                if len(kaliplar) >= 1:
                    return 4
                return 2 # boş
        else: # fırında uyumlu kalıp var mı
            gozler = Location.objects.filter(locationRelationID=firinId)
            kalipList = DiesLocation.objects.filter(kalipVaris__in=gozler).values_list('kalipNo', flat=True)
            kaliplar = KalipMs.objects.using('dies').filter(KalipNo__in= list(kalipList), ProfilNo=pNo).values_list('KalipNo', flat=True)
            if len(kaliplar) >= 1:
                return 3 # üretime başla
            else: return 2 #boş
    except Location.DoesNotExist:
        return None
    
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

def checkKalip(id):
    ek_siparis_instance = EkSiparis.objects.get(id=id)
    return ek_siparis_instance.production_started()

def eksiparis_list(request):
    params = json.loads(unquote(request.GET.get('params')))
    size = params["size"]
    page = params["page"]
    filter_list = params["filter"]
    offset, limit = calculate_pagination(page, size)
    # presKodu bazlı getirilecek pres operatörlerine sadece o pres için olan siparişleri görme yetkisi verilecek.
    
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
    ek_siparis_list = list(ekSiparis.filter(SipKimlik__in=sip_filter)[offset:limit].values())

    for e in ek_siparis_list:
        siparis1 = siparis.get(Kimlik=e['SipKimlik'])
        e['EkTermin'] = format_date(e['EkTermin'])
        e['SipKartNo'] = f"{e['SipKartNo']}-{e['EkNo']}"
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
        if siparis.filter(Kimlik = e['SipKimlik']).exists() == False :
            a = ekSiparis.get(SipKimlik = e['SipKimlik'], EkNo = e['EkNo'])
            if a.MsSilindi != True:
                a.MsSilindi = True
                a.save()
            ekSiparisList.remove(e)
        else:
            siparis1 = siparis.get(Kimlik = e['SipKimlik'])
            e['EkTermin'] = format_date(e['EkTermin'])
            e['SipKartNo'] = str(e['SipKartNo']) + "-" +str(e['EkNo'])
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

class YudaView(generic.TemplateView):
    template_name = 'ArslanTakipApp/yuda2.html'

#for getting the select options 
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

@transaction.atomic
def yuda_kaydet(request):
    if request.method == "POST":
        try:
            today = datetime.datetime.now().strftime('%j')
            year = datetime.datetime.now().strftime('%y')
            lastOfDay = YudaForm.objects.filter(YudaNo__startswith=year + '-' + today).order_by('-YudaNo').first()
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

            for key, value in request.POST.items(): 
                if hasattr(y, key):
                    if key == "BirlikteCalisan":
                        value_list = value.split(',')
                        setattr(y, key, value_list)
                    else:
                        setattr(y, key, value)
            y.save()

            group_names = [
                'Ust Yonetim Bolumu',
                'Planlama Bolumu',
                'Kalite Bolumu',
                'Kaliphane Bolumu',
                'Pres Bolumu',
                'Paketleme Bolumu',
                'Yurt Disi Satis Bolumu',
                'Yurt Ici Satis Bolumu',
                'Proje Bolumu',
            ]

            group_mapping = {
                'YuzeyEloksal': 'Eloksal Bolumu',
                'YuzeyAhsap': 'Ahsap Kaplama Bolumu',
                'YuzeyBoya': 'Boyahane Bolumu',
                'TalasliImalat': 'Mekanik Islem Bolumu',
            }

            groups = [Group.objects.get(name=name) for name in group_names]

            assign_perm("gorme_yuda", request.user, y) # Assign permission to the current user
            assign_perm("acan_yuda", request.user, y) # Yudayı açan kişiye değiştirme ve görme yetkisi ver
            assign_perm("gorme_yuda", y.ProjeYoneticisi, y) # Assign permission to the current user
            assign_perm("acan_yuda", y.ProjeYoneticisi, y) # Assign permission to the current user
            for group in groups: #groups içinde olanların hepsinin bütün projeleri görme yetkisi var
                if group.name == "Yurt Ici Satis Bolumu" or group.name == "Yurt Disi Satis Bolumu":
                    if group in request.user.groups.all():
                        assign_perm("gorme_yuda", group, y)
                else:
                    assign_perm("gorme_yuda", group, y)


            # Check field values and assign permissions based on conditions
            for field in y._meta.fields:
                fname = field.name
                fvalue = getattr(y, fname)
                if fname in group_mapping and fvalue is not None and fvalue != "" and fname != "TalasliImalat":
                    group = Group.objects.get(name=group_mapping[fname])
                    assign_perm("gorme_yuda", group, y)
                if fname == "TalasliImalat" and fvalue == "Var":
                    group = Group.objects.get(name=group_mapping[fname])
                    assign_perm("gorme_yuda", group, y)

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
                

            response = JsonResponse({'message': 'Kayıt başarılı', 'id': y.id})
        except json.JSONDecodeError:
            response = JsonResponse({'error': 'Geçersiz JSON formatı'})
            response.status_code = 500 #server error
        except Exception as e:
            response = JsonResponse({'error': str(e)})
            response.status_code = 500 #server error

    return response
        
class YudasView(generic.TemplateView):
    template_name = 'ArslanTakipApp/yudaList.html'

def yuda_filter(i):
    q = {}
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

    user_group = request.user.groups.filter(name__endswith=" Bolumu").first()
    if len(filter_list) > 0:
        for i in filter_list:
            if i['field'] == "bolumOnay":
                if i['value'] == "None":
                    y = y.exclude(yudaonay__Group=user_group)
                else:
                    q = bolumOnayFilter(q, i['value'], user_group)
            else:
                q = yuda_filter(i)

    y = y.filter(Silindi__isnull = True).filter(**q).order_by('-Tarih', '-YudaNo')
    
    filtered_yudas = y.values()
    yudaList = list(filtered_yudas[offset:limit])

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

def yudaDetail(request, yId):
    yudaFiles = getFiles("YudaForm", yId)
    files = json.dumps(list(yudaFiles), sort_keys=True, indent=1, cls=DjangoJSONEncoder)
        
    yudaComments = getParentComments("YudaForm", yId).order_by("Tarih")
    yudaCList = [process_comment(request.user, comment) for comment in yudaComments]
    comments = json.dumps(yudaCList, sort_keys=True, indent=1, cls=DjangoJSONEncoder)

    yudaDetails = YudaForm.objects.filter(id = yId).values()
    
    yList = list(yudaDetails)
    formatted_yuda_details = format_yuda_details(yList)
    data = json.dumps(formatted_yuda_details, sort_keys=True, indent=1, cls=DjangoJSONEncoder)

    onayCount = YudaOnay.objects.filter(Yuda_id=yId, OnayDurumu=True).count()
    retCount = YudaOnay.objects.filter(Yuda_id=yId, OnayDurumu=False).count()
    if not YudaOnay.objects.filter(Yuda_id = yId, Group = request.user.groups.first()).first():
        secim =""
    else:
        secim = YudaOnay.objects.get(Yuda_id = yId, Group = request.user.groups.first()).OnayDurumu
    
    # return render(request, 'ArslanTakipApp/yudaDetail.html', {'yuda_json':data, 'data2':formatted_data2, 'files_json':files, 'comment_json':comments, 'onay':onayCount, 'ret': retCount, 'Selected':secim})
    return render(request, 'ArslanTakipApp/yudaDetail.html', {'yuda_json':data, 'files_json':files, 'comment_json':comments, 'onay':onayCount, 'ret': retCount, 'Selected':secim})

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
            )

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
        pres_kodu = '1600-2'
        sip = SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')).exclude(SiparisTamam='BLOKE')
        sip = sip.filter(PresKodu=pres_kodu)
        distinct_values = {
            'siparisler': sip.values_list('KartNo', flat=True).distinct(),
            'profiller': sip.values_list('ProfilNo', flat=True).distinct(),
            'firmalar': sip.values_list('FirmaAdi', flat=True).distinct(),
            'billetler': sip.values_list('BilletTuru', flat=True).distinct(),
            'kondusyonlar': sip.values_list('KondusyonTuru', flat=True).distinct(),
            'yuzeyler': sip.values_list('YuzeyOzelligi', flat=True).distinct(),
            'gramajlar': sip.values_list('Profil_Gramaj', flat=True).distinct(),
        }

        context_data = {field: json.dumps(list(values)) for field, values in distinct_values.items()}
        context.update(context_data)
        return context
    
    def post(self, request, *args, **kwargs):
        data = request.POST
        pres_kodu = '1600-2' # kullanıcıdan alınacak
        kriterData = json.loads(data['kriterData'])
        if not kriterData:
            return JsonResponse({"error": "Missing data."}, status=400)
        
        order_plan = self.production_plan(pres_kodu, kriterData)
        order_plan = self.transform_plan(order_plan)
        print(order_plan)
        return JsonResponse({'order_plan': order_plan})

    def production_plan(self, pres_kodu, kriterler):
        sip = SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE')).exclude(SiparisTamam='BLOKE')
        orders = sip.filter(PresKodu=pres_kodu, Kg__gt=0).order_by("SonTermin")

        exclude_list = [item['kriter'] for item in kriterler if item['type'] == 'Hariç Tut']
        priority_list = [item['kriter'] for item in kriterler if item['type'] == 'Öncelik']
        limit_list = [item for item in kriterler if item['type'] == 'Limit']

        transformations = {
            'Sipariş': 'KartNo',
            'Billet': 'BilletTuru',
            'Firma': 'FirmaAdi',
            'Kondüsyon': 'KondusyonTuru',
            'Profil': 'ProfilNo',
            'Gramaj': 'Profil_Gramajı',
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
            
            for i in limit_order:
                order_plan.append(i)

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
            o['Profil'] = s.ProfilNo
            o['Billet'] = s.BilletTuru
            o['Yuzey'] = s.YuzeyOzelligi
            o['Kondusyon'] = s.KondusyonTuru
            o['Gramaj'] = s.Profil_Gramaj

        return plan
            
            
