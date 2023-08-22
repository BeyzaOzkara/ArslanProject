import base64, binascii, zlib
import time
import math
from urllib.parse import unquote
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Location, Kalip, Hareket, KalipMs, DiesLocation, PresUretimRaporu, SiparisList
from django.template import loader
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.decorators import login_required, permission_required
from guardian.shortcuts import get_objects_for_user
from django.db.models import Q, Sum, Max, Count, Case, When
from django.db import transaction 
from aes_cipher import *
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# Create your views here.

class IndexView(generic.TemplateView):
    template_name = 'ArslanTakipApp/index.html'

class RegisterView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/register.html"

def compare(s, t):
    return sorted(s) == sorted(t)

def guncelle(i, b, u):
    for j in b:
        print(j[0])
        if i == 'KalipNo':
            k = KalipMs.objects.using('dies').get(KalipNo = j[0])
            print(k.ProfilNo)
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

@login_required #user must be logged in
#@permission_required("ArslanTakipApp.view_location") #izin yoksa login sayfasına yönlendiriyor
def location(request):
    loc = get_objects_for_user(request.user, "ArslanTakipApp.dg_view_location", klass=Location) #Location.objects.all() 
    loc_list = list(loc.values().order_by('id'))
    loc_list_rev = list(reversed(loc_list))
    for item in loc_list_rev:
        for i in loc_list:
            if item['locationRelationID_id'] == i['id']:
                try:
                    i['_children'].append(item)
                except:
                    i['_children'] = [item]
                loc_list.remove(item)

    childData = loc_list
    gonderData = location_list(request.user)

    if request.method == "POST":
        dieList = request.POST.get("dieList")
        dieList = dieList.split(",")
        dieTo = request.POST.get("dieTo")
        lRec = Location.objects.get(id = dieTo)
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
                
    data = json.dumps(childData)
    return render(request, 'ArslanTakipApp/location.html', {'location_json':data, 'gonder_json':gonderData})

def location_list(a):
    gonderLoc = get_objects_for_user(a, "ArslanTakipApp.gonder_view_location", klass=Location)
    gonderLoc_list = list(gonderLoc.values().order_by('id'))
    gonderLoc_list_rev = list(reversed(gonderLoc_list))
    for item in gonderLoc_list_rev:
        for i in gonderLoc_list:
            if item['locationRelationID_id'] == i['id']:
                try:
                    i['_children'].append(item)
                except:
                    i['_children'] = [item]
                gonderLoc_list.remove(item)

    childData = gonderLoc_list
    data = json.dumps(childData)
    return data

def kalip_liste(request):
    #Kalıp Listesi Detaylı
    params = json.loads(unquote(request.GET.get('params')))
    for i in params:
        value = params[i]
        #print("Key and Value pair are ({}) = ({})".format(i, value))
    size = params["size"]
    page = params["page"]
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

    g = list(query.values()[(page-1)*size:page*size])

    for c in g:
        if c['UretimTarihi'] != None:
            c['UretimTarihi'] = c['UretimTarihi'].strftime("%d-%m-%Y")
            c['SonTeniferTarih'] =c['SonTeniferTarih'].strftime("%d-%m-%Y %H:%M:%S")
            c['SonUretimTarih'] =c['SonUretimTarih'].strftime("%d-%m-%Y")
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
    for i in params:
        value = params[i]
        print("Key and Value pair are ({}) = ({})".format(i, value))
    size = params["size"]
    page = params["page"]
    filter_list = params["filter"]
    q = {} 
    kalip_count = 0
    lastData= {'last_page': math.ceil(kalip_count/size), 'data': []}

    if len(filter_list)>0:
        print(filter_list)
        for i in filter_list:
            if i["type"] == "like":
                q[i['field']+"__startswith"] = i['value']
            elif i["type"] == "=":
                q[i['field']] = i['value']
    
        query = PresUretimRaporu.objects.using('dies').all()
        query = query.filter(**q).order_by('-Tarih') 

        g = list(query.values()[(page-1)*size:page*size])
        for c in g:
            if c['Tarih'] != None:
                c['Tarih'] = c['Tarih'].strftime("%d-%m-%Y") + " <BR>└ " + c['BaslamaSaati'].strftime("%H:%M") + " - " + c['BitisSaati'].strftime("%H:%M")
                c['BaslamaSaati'] =c['BaslamaSaati'].strftime("%H:%M")
                c['BitisSaati'] =c['BitisSaati'].strftime("%H:%M")
            #print(c)
        kalip_count = query.count()
        lastData= {'last_page': math.ceil(kalip_count/size), 'data': []}
        lastData['data'] = g

    data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

#gelen id başka konumların parenti ise altındakileri listele??
def location_hareket(request):
    params = json.loads(unquote(request.GET.get('params')))
    size = params["size"]
    page = params["page"]
    filter_list = params["filter"]

    hareket_count = 0
    lastData= {'last_page': math.ceil(hareket_count/size), 'data': []}

    if len(filter_list)>0:
        print(filter_list)
        hareketK = filter_list[0]['value']
        hareketQuery = Hareket.objects.all()
        location_list = Location.objects.values()
        hareketQuery = list(hareketQuery.values().filter(kalipNo=hareketK))
        kalip_l = list(DiesLocation.objects.filter(kalipNo=hareketK).values())
        users = User.objects.values()
        harAr = []
        print(hareketQuery)
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
            har['kimTarafindan'] = list(users.filter(id=int(h['kimTarafindan_id'])))[0]["first_name"] + " " + list(users.filter(id=int(h['kimTarafindan_id'])))[0]["last_name"] 
            har['hareketTarihi'] = h['hareketTarihi'].strftime("%d-%m-%Y %H:%M:%S")
            harAr.append(har)
            print(h)
            print(har)
        print(harAr)
        hareket_count = len(harAr)

        lastData= {'last_page': math.ceil(hareket_count/size), 'data': []}
        lastData['data'] = list(harAr[(page-1)*size:page*size])
                
    #print(lastData)
    data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
    return HttpResponse(data)

def kalip(request):
    """ with transaction.atomic():
        listFields = {'AktifPasif', 'Silindi',  'Hatali', 'KalipNo', 'SilinmeSebebi', 'TeniferKalanOmurKg', 'KaliteOkey', 'TeniferOmruMt', 'TeniferOmruKg', 'TeniferNo', 'SonTeniferTarih', 
                        'SonTeniferKg', 'SonTeniferSebebi', 'SonUretimTarih', 'SonUretimGr', 'UretimTenSonrasiKg', 'UretimToplamKg', 'KalipAciklama', 'SikayetVar', 'KaliteAciklama', 
                        'PresKodu', 'PaketBoyu'}
        for i in listFields:
            print(i)
            u = {}
            rows1 = list(KalipMs.objects.using('dies').order_by('-KalipNo').values_list('KalipNo', i))
            rows2 = list(Kalip.objects.order_by('-KalipNo').values_list('KalipNo', i))
            a = compare(rows1,rows2)
            if a == False:
                print (a)
                b= set(rows1) - set(rows2)
                #print (b)
                #guncelle(i,b,u)
                for j in b:
                    print(j[0])
                    if i == 'KalipNo':
                        k = KalipMs.objects.using('dies').get(KalipNo = j[0])
                        print(k.ProfilNo)
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
                        Kalip.objects.filter(KalipNo = j[0]).update(**u) """
                        #print("updated")
    return render(request, 'ArslanTakipApp/kalip.html')

class KalipView(generic.TemplateView):
    template_name = 'ArslanTakipApp/kalip.html'

def location_kalip(request):
    #kalıp arşivi sayfasındaki kalıplar
    if request.method == "GET":
        path = request.get_full_path()
        print(path)
        params = json.loads(unquote(request.GET.get('params')))
        for i in params:
            value = params[i]
            print("Key and Value pair are ({}) = ({})".format(i, value))
        size = params["size"]
        page = params["page"]
        filter_list = params["filter"]
        q = {}

        loc = get_objects_for_user(request.user, "ArslanTakipApp.dg_view_location", klass=Location) #Location.objects.all() 
        loc_list = list(loc.values())
        locs = [l['id'] for l in loc_list]
        query = DiesLocation.objects.filter(kalipVaris_id__in = locs).order_by('kalipNo')
        lfil =[]
        if request.user.is_superuser:
            query = DiesLocation.objects.all().order_by('kalipNo')
        
        if len(filter_list)>0:
            for i in filter_list:
                if i["type"] == "like":
                    q[i['field']+"__startswith"] = i['value']
                elif i["type"] == "=":
                    #q[i['field']] = i['value']
                    loca = loc.values().get(id = i['value'])
                    if loca['isPhysical']: 
                        q[i['field']] = i['value']
                    else :
                        lo = loc.values().filter(locationRelationID_id = i['value'])
                        for j in list(lo):
                            if j['isPhysical']:
                                lfil.append(j['id'])
                            else:
                                filo = loc.values().filter(locationRelationID_id = j['id'])
                                for f in list(filo):
                                    if f['isPhysical']:
                                        lfil.append(f['id'])
                                    else :
                                        filo2 = loc.values().filter(locationRelationID_id = f['id'])
                                        #print(filo2)
                                        for b in list(filo2):
                                            if b['isPhysical']:
                                                lfil.append(b['id'])
                        #print(lfil)
                        query = DiesLocation.objects.filter(kalipVaris_id__in=lfil)

        query = query.filter(**q) 
        kal = KalipMs.objects.using('dies').all()
        a = list(query.values()[(page-1)*size:page*size])
        for b in a:
            s = kal.get(KalipNo=b['kalipNo'])
            if s.Silindi == 1 or s.AktifPasif == 'Pasif':
                #print(b)
                a.remove(b)
                #print("silindi")
            c = kal.get(KalipNo=b['kalipNo']).Hatali
            if c==1:
                b['Hatali'] = 1
        #print(a)
        kalip_count = query.count()
        lastData= {'last_page': math.ceil(kalip_count/size), 'data': []}
        lastData['data'] = a #list(query.values()[(page-1)*size:page*size])
        data = json.dumps(lastData, sort_keys=True, indent=1, cls=DjangoJSONEncoder)
        return HttpResponse(data)


key = b'arslandenemebyz1'

def encrypt_aes_ecb(key, plaintext):
    cipher = AES.new(key, AES.MODE_ECB)
    padded_plaintext = pad(plaintext.encode('utf8'), AES.block_size)
    ciphertext = cipher.encrypt(padded_plaintext)
    return ciphertext

def decrypt_aes_ecb(key, ciphertext):
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted_data = cipher.decrypt(ciphertext)
    unpadded_data = unpad(decrypted_data, AES.block_size)
    return unpadded_data.decode('utf-8')

def qrKalite(request):
    if request.method == "GET":
        print("qr sayfası")
        """ path = request.get_full_path()
        print(path)
        print(path.rsplit('/', 1)[-1]) """

        # Şifre çözme
        unhexli = binascii.unhexlify('b23d7cad6447841b177fe5610114b374')
        print(unhexli)
        decrypted_text = decrypt_aes_ecb(key, unhexli)
        print("Çözülmüş Veri:", decrypted_text)        

        ty = request.GET.get('type', '')
        no = request.GET.get('no', '')
        print(ty + " " + no)
        
        context = {
            "type" : unhexli,
            "no" : decrypted_text,
        }

        """ olmayan = []
        notsaved = []
        query = KalipMs.objects.using('dies').all() #['SIRA 5','11497'], ['SIRA 6','402-3'], ['SIRA 8','12773-3'],['SIRA 9','4405-31'],['SIRA 9','4471-33'],
        sira1 = [
                 ]
        for i in sira1:
            try:
                print(i[1])
                a = list(KalipMs.objects.using('dies').filter(KalipNo__startswith = i[1]).values())
                if not a:
                    olmayan.append(i)
                for j in a:
                    kno = j['KalipNo']
                    if kno.strip()==i[1]:
                        if DiesLocation.objects.get(kalipNo = kno).kalipVaris_id != Location.objects.get(locationName = i[0]).id:
                            hareket = Hareket()
                            print(kno+'if ici')
                            hareket.kalipKonum_id = DiesLocation.objects.get(kalipNo = kno).kalipVaris_id
                            #print(DiesLocation.objects.get(kalipNo = kno).kalipVaris_id)
                            hareket.kalipVaris_id = Location.objects.get(locationName = i[0]).id
                            #print(hareket.kalipVaris_id)
                            hareket.kalipNo = query.get(KalipNo = kno).KalipNo
                            hareket.kimTarafindan_id = request.user.id
                            hareket.save()
                            print("Hareket saved")
                            print()
            except:
                print(KalipMs.objects.using('dies').get(KalipNo = i[1]).KalipNo)
                notsaved.append(i)
                print("Hareket not saved")
    
    print(olmayan)
    print(notsaved) """
    return render(request, 'ArslanTakipApp/qrKalite.html', context)

class qrKaliteView(generic.TemplateView):
    template_name = 'ArslanTakipApp/qrKalite.html'


class HareketView(generic.TemplateView):
    template_name = 'ArslanTakipApp/hareket.html'

def qrDeneme(request):
    return

class SiparisView(generic.TemplateView):
    template_name = 'ArslanTakipApp/siparisList.html'


def siparis_list(request):
    s = SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE'))
    k = KalipMs.objects.using('dies').all()

    params = json.loads(unquote(request.GET.get('params')))
    for i in params:
        value = params[i]
        print("Key and Value pair are ({}) = ({})".format(i, value))
    size = params["size"]
    page = params["page"]
    filter_list = params["filter"]
    sorter_List = params["sorterList"]
    q={}
    
    if len(filter_list)>0:
        for i in filter_list:
            if i['field'] == 'TopTenKg':
                q["ProfilNo"+"__in"] = siparis_TopTenFiltre(i)
            elif i["type"] == "like":
                if i['field'] != 'FirmaAdi':
                    q[i['field']+"__startswith"] = i['value']
                else: q[i['field']+"__contains"] = i['value']
            elif i["type"] == "=":
                if i['field'] == 'SiparisTamam':
                    if i['value'] == 'BLOKE':
                        q[i['field']] = i['value']
                    elif i['value'] == 'degil':
                        s = s.exclude(SiparisTamam ='BLOKE')
                    else: s =s
                else: q[i['field']] = i['value']
            elif i['type'] != i['value']:
                q[i['field'] +"__gte"] = i['type']
                q[i['field'] +"__lt"] = i['value']
            else:q[i['field']] = i['value']

            if i['field'] != 'SiparisTamam':
                s = s.exclude(SiparisTamam = 'BLOKE').filter(**q).order_by('-SonTermin')
            else: s = s.filter(**q).order_by('-SonTermin')
    else:
        s = s.exclude(SiparisTamam = 'BLOKE')
    sor =[]
    if len(sorter_List)>0:
        for j in sorter_List:
            if j['field'] != 'TopTenKg':
                if j['type'] == 'azalan':
                    sor.append( "-"+j['field'])
                else: sor.append(j['field'])
            else: 
                s = s.extra(
                    select={
                        "kg_sum": "(SELECT SUM(TeniferKalanOmurKg) FROM View020_KalipListe WHERE (View020_KalipListe.ProfilNo = View051_ProsesDepoListesi.ProfilNo AND View020_KalipListe.AktifPasif='Aktif' AND View020_KalipListe.Hatali=0 AND View020_KalipListe.TeniferKalanOmurKg>= 0))"
                    },
                )
                if j['type'] == 'azalan':
                    sor.append( "-kg_sum")
                else: sor.append("kg_sum")
        s = s.order_by(*sor)

    else: s= s.order_by('-SonTermin')

    sip = list(s.values('KartNo','ProfilNo','FirmaAdi', 'GirenKg','Kg', 'KondusyonTuru', 'PresKodu','SiparisTamam','SonTermin','BilletTuru')[(page-1)*size:page*size])
    for a in sip:
        kal = k.filter(ProfilNo=a['ProfilNo'], AktifPasif="Aktif", Hatali=0).values('ProfilNo', 'TeniferKalanOmurKg')
        tkal =0
        skal =0
        ttk =0
        if kal.filter(TeniferKalanOmurKg__gte = 0):
            tkal = len(kal.filter(TeniferKalanOmurKg__gte = 0))
            skal = len(kal)
            ttk = math.ceil(kal.filter(TeniferKalanOmurKg__gte = 0).aggregate(Sum('TeniferKalanOmurKg'))['TeniferKalanOmurKg__sum'])
        a['kalipSayisi'] = str(tkal) + " / " + str(skal)
        a['SonTermin'] =a['SonTermin'].strftime("%d-%m-%Y")
        a['GirenKg'] = f'{math.ceil(a["GirenKg"]):,}'
        a['Kg'] = f'{math.ceil(a["Kg"]):,}'
        a['TopTenKg'] = f'{ttk:,}'

    sip_count = s.count()
    lastData= {'last_page': math.ceil(sip_count/size), 'data': []}
    lastData['data'] = sip
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
        print(diff)
        print(profilList)
    
    return profilList

def siparis_max(request):
    s = SiparisList.objects.using('dies').filter(Q(Adet__gt=0) & ((Q(KartAktif=1) | Q(BulunduguYer='DEPO')) & Q(Adet__gte=1)) & Q(BulunduguYer='TESTERE'))
    k= KalipMs.objects.using('dies').filter(TeniferKalanOmurKg__gte = 0, AktifPasif="Aktif", Hatali=0)
    e ={}
    e['GirenMax'] =math.ceil(s.aggregate(Max('GirenKg'))['GirenKg__max'])
    e['KgMax'] = math.ceil(s.aggregate(Max('Kg'))['Kg__max'])

    e['GirenSum'] = math.ceil(s.aggregate(Sum('GirenKg'))['GirenKg__sum'])
    e['KgSum'] = math.ceil(s.aggregate(Sum('Kg'))['Kg__sum'])

    sProfil = list(s.values_list('ProfilNo', flat=True).distinct())
    proTop = k.filter(ProfilNo__in = sProfil).values('ProfilNo').annotate(psum = Sum('TeniferKalanOmurKg'))
    sonuc = proTop.aggregate(Max('psum'))['psum__max']
    e['TopTenMax']  = math.ceil(sonuc)
    
    return JsonResponse(e)

def siparis_child(request, pNo):
    #Kalıp Listesi Detaylı
    kalip = KalipMs.objects.using('dies').values('KalipNo','UreticiFirma', 'TeniferKalanOmurKg', 'UretimToplamKg', 'PresKodu', 'Capi')
    child = kalip.filter(ProfilNo=pNo, AktifPasif="Aktif", Hatali=0)
    location_list = Location.objects.values()
    #print()
    gonder = list(child)
    for c in gonder:
        pkodu = PresUretimRaporu.objects.using('dies').filter(KalipNo=c["KalipNo"]).order_by("-Tarih", "-BitisSaati").values("PresKodu","Tarih", "BitisSaati")
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
