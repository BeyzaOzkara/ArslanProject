import math
from urllib.parse import unquote
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Location, Kalip, Hareket, KalipMs, DiesLocation
from django.template import loader
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.decorators import login_required, permission_required
from guardian.shortcuts import get_objects_for_user
from django.db.models import Q
from django.db import transaction 

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
@permission_required("ArslanTakipApp.view_location") #izin yoksa login sayfasına yönlendiriyor
def location(request):
    loc = get_objects_for_user(request.user, "ArslanTakipApp.dg_view_location", klass=Location) #Location.objects.all() 
    loc_list = list(loc.values())
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

    if request.method == "POST":
        dieList = request.POST.get("dieList")
        print("diesList: "+ dieList)
        dieList = dieList.split(",")
        dieTo = request.POST.get("dieTo")
        lRec = Location.objects.get(id = dieTo)
        print("lRec: ")
        print(lRec.id)
        for i in dieList:
            k = DiesLocation.objects.get(kalipNo = i)
            print(k.kalipVaris.id)
            if k.kalipVaris != lRec.id:
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
    return render(request, 'ArslanTakipApp/location.html', {'location_json':data})

def location_list(request):
    loc_list = list(request.values())
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
    data = json.dumps(childData)
    return loc_list

def kalip_liste(request):
    #Kalıp Listesi Detaylı
    #Tıklayınca Kalıp Teknik resimleri göster Popup?
    params = json.loads(unquote(request.GET.get('params')))
    size = params["size"]
    page = params["page"]
    filter_list = params["filter"]
    query = KalipMs.objects.using('dies').all()
    #query = Kalip.objects.all()
    location_list = Location.objects.values()
    q = {} 
    
    if len(filter_list)>0:
        for i in filter_list:
            if i['type'] != 'kalipLocation':
                if i["type"] == "like":
                    q[i['field']+"__contains"] = i['value']
                elif i["type"] == "=":
                    q[i['field']] = i['value']

    query = query.filter(**q).order_by('-UretimTarihi') 

    g = list(query.values()[(page-1)*size:page*size])

    for c in g:
        if c['UretimTarihi'] != None:
            c['UretimTarihi'] = c['UretimTarihi'].strftime("%d-%m-%Y")
            c['SonTeniferTarih'] =c['SonTeniferTarih'].strftime("%d-%m-%Y %H:%M:%S")
            c['SonUretimTarih'] =c['SonUretimTarih'].strftime("%d-%m-%Y")
        try: 
            b = DiesLocation.objects.get(kalipNo = c['KalipNo']).kalipVaris_id
        except:
            b = 48
            hareket = Hareket()
            hareket.kalipVaris_id = 48
            hareket.kalipNo = c['KalipNo']
            hareket.kimTarafindan_id = request.user.id
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
        #query = Kalip.objects.filter(kalipLocation_id__in=locs).order_by('KalipNo')
        lfil =[]
        if request.user.is_superuser:
            query = DiesLocation.objects.all().order_by('kalipNo')
        
        if len(filter_list)>0:
            for i in filter_list:
                if i["type"] == "like":
                    q[i['field']+"__contains"] = i['value']
                elif i["type"] == "=":
                    #q[i['field']] = i['value']
                    loca = loc.values().get(id = i['value'])
                    if loca['isPhysical']: 
                        q[i['field']] = i['value']
                        #print("1.if")
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

def qrKalite(request):
    if request.method == "GET":
        ty = request.GET.get('type')
        no = request.GET.get('no')
        if ty==None and no==None:
            print("sepet yok")
            ty = ""
            no = ""
        print(ty + " " + no)
        
        context = {
            "type" : ty,
            "no" : no,
        }
    return render(request, 'ArslanTakipApp/qrKalite.html', context)

class qrKaliteView(generic.TemplateView):
    template_name = 'ArslanTakipApp/qrKalite.html'


class HareketView(generic.TemplateView):
    template_name = 'ArslanTakipApp/hareket.html'


