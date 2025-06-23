import datetime
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db.models import Index, Q
from django.contrib.auth.models import Group

# Create your models here.
class Location(models.Model):
    locationName = models.CharField(max_length=255, verbose_name="Lokasyon İsmi")
    presKodu = models.CharField(max_length=250, null=True, blank=True)
    locationRelationID = models.ForeignKey("self", on_delete=models.CASCADE, blank =True, null=True)
    isPhysical = models.BooleanField(verbose_name="Fiziksel Bir Konum mu?")
    capacity = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return self.locationName
    
    class Meta:
        permissions = [("dg_view_location", "Gorme Yetkisi Var"), 
                       ("gonder_view_location", "Gonderme Yetkisi Var"), 
                       ("meydan_view_location", "Meydan Gorme Yetkisi Var"), 
                       ("goz_view_location", "Goz Gorme Yetkisi Var"),
                        ("kalipEkran_view_location", "Kalip Ekrani Gorme Yetkisi Var")]

#veritabanı isimlerini ingilizce yap
#blank true eklenecekleri belirle
class DiesLocation(models.Model): #Kalıpların son konumları
    kalipNo = models.CharField(primary_key=True, verbose_name="Kalıp Numarası")
    kalipVaris = models.ForeignKey(Location, on_delete=models.CASCADE, null=True)
    hareketTarihi = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        managed = False
        db_table = 'View1_KalipLastLocation'

class LocationDies(models.Model): #konumların içindeki kalıplar
    location_id = models.IntegerField(null=True)
    locationName = models.CharField(null=True)
    kalip_list = models.TextField(null=True)

    class Meta:
        managed=False
        db_table = 'View_DiesInLocations'

#bir yerden diğer yere aktarılması, tarih saat, kim
class Hareket(models.Model):
    kalipNo = models.CharField(null=False, verbose_name="Kalıp Numarası")
    kalipKonum = models.ForeignKey(Location, on_delete=models.CASCADE, blank=True, null =True, related_name="kalip_konum", verbose_name="Kalıp Konum")
    kalipVaris = models.ForeignKey(Location, on_delete=models.CASCADE, null =True, related_name="kalip_varis", verbose_name="Kalıp Varış")
    hareketTarihi = models.DateTimeField(auto_now=True, null=True)
    kimTarafindan = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Kim Tarafından")
    aciklama = models.CharField(null=True, blank=True)

    class Meta:
        verbose_name="Hareket"
        verbose_name_plural="Hareketler"

#Hareket object ne gözüksün??    
    def __str__(self):
        return str(self.kalipNo)

class MusteriFirma(models.Model):
    FirmaKodu = models.CharField(blank=True, primary_key=True)
    FirmaAdi = models.CharField(null=True, blank=True)
    MusteriTemsilcisi = models.CharField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'View009_FirmaListesi'

class KalipMs(models.Model):
    KalipNo = models.CharField(primary_key=True)
    ProfilNo = models.CharField(null=True)
    Kimlik = models.IntegerField(null=True)#profilno ile aynısı
    FirmaKodu = models.CharField(null=True)
    FirmaAdi = models.CharField(null=True)
    Cinsi = models.CharField(null=True)
    Miktar = models.FloatField(null=True)
    Capi = models.FloatField(null=True)
    UretimTarihi = models.DateTimeField(null=True)
    GozAdedi = models.IntegerField(null=True)
    Silindi = models.IntegerField(null=True)
    SilinmeSebebi = models.CharField(null=True)
    Bolster = models.CharField(null=True)
    KalipCevresi = models.FloatField(null=True)
    KaliteOkey = models.IntegerField(null=True)
    UreticiFirma = models.CharField(null=True) 
    TeniferOmruMt = models.FloatField(null=True)
    TeniferOmruKg = models.FloatField(null=True)
    TeniferKalanOmurKg = models.FloatField(null=True)
    TeniferNo = models.IntegerField(null=True)
    SonTeniferTarih = models.DateTimeField(null=True)
    SonTeniferKg = models.FloatField(null=True)
    SonTeniferSebebi = models.CharField(null=True)
    SonUretimTarih = models.DateTimeField(null=True)
    SonUretimGr = models.FloatField(null=True)
    UretimTenSonrasiKg = models.FloatField(null=True)
    UretimToplamKg = models.FloatField(null=True)
    ProfilGramaj = models.FloatField(null=True)
    KalipAciklama = models.CharField(null=True)
    SikayetVar = models.IntegerField(null=True)
    KaliteAciklama = models.CharField(null=True)
    AktifPasif = models.CharField(null=True)
    Hatali = models.IntegerField(null=True)
    PresKodu = models.CharField(null=True)
    ResimDizini = models.CharField(null=True)
    PaketBoyu = models.CharField(null=True)
    BariyerOkey = models.IntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'View020_KalipListe'

class ProfilMs(models.Model):
    Kimlik = models.IntegerField(null=True, blank=True)
    ProfilNo = models.CharField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'View028_ProfilListe'

class Sepet(models.Model):
    sepet_no = models.CharField(null=True, blank=True)
    baslangic_saati = models.DateTimeField(null=True, blank=True)
    bitis_saati = models.DateTimeField(null=True, blank=True)
    pres_kodu = models.CharField(null=True, blank=True)
    yuklenen = models.JSONField(null=True, blank=True)
    meta_data = models.JSONField(null=True, blank=True)

    class Meta:
        permissions = [("view_4500_uretim", "Uretim Gorme Yetkisi Var")]

class KartDagilim(models.Model):
    profil_no = models.CharField(null=True, blank=True)
    profil_gr = models.FloatField(null=True, blank=True)
    secilen_ext = models.JSONField(null=True, blank=True)
    secilen_sepet = models.JSONField(null=True, blank=True)
    secilen_siparis = models.JSONField(null=True, blank=True)
    dagitilan_kartlar = models.JSONField(null=True, blank=True)
    tarih = models.DateTimeField(auto_now=True, blank=True, null=True)

class KalipMuadil(models.Model):
    profiller = ArrayField(models.CharField(max_length=50),  # Each die ID will be a string (e.g., 'A', 'B', 'C')
        size=None, blank=True,
    )

class QRCode(models.Model):
    qr = models.CharField(null=True, blank=True)
    name = models.CharField(null=True, blank=True)
    detail = models.CharField(null=True, blank=True)

class PresUretimRaporu(models.Model):
    KalipNo = models.CharField(primary_key=True)
    KartNo = models.IntegerField(null=True)
    PresTestereNo = models.IntegerField(null=True)
    Tarih = models.DateTimeField(null=True)
    Operator = models.CharField(null=True)
    StokKodu = models.CharField(null=True)
    StokCinsi = models.CharField(null=True)
    PartiNo = models.CharField(null=True)
    PresKodu = models.CharField(null=True)
    PresAdi = models.CharField(null=True)
    Gerceklesen = models.FloatField(null=True)
    BaslamaSaati = models.DateTimeField(null=True)
    BitisSaati = models.DateTimeField(null=True)
    HataKodu = models.IntegerField(null=True, blank=True)
    HataTuru = models.CharField(null=True, blank=True)
    HataAciklama = models.CharField(null=True)
    Durum = models.CharField(null=True)
    IslemGoren_Kg = models.FloatField(null=True)
    ToplamBilletKg = models.FloatField(null=True)
    Sure = models.DecimalField(null=True, max_digits=18, decimal_places=2)
    
    class Meta:
        managed = False
        db_table = 'View062_PresUretimRaporu'

#siparistamam bloke
class SiparisList(models.Model):
    Kimlik = models.IntegerField(primary_key=True)
    KartNo = models.IntegerField(null=True)
    ProfilNo = models.CharField(null=True)
    BulunduguYer = models.CharField(null=True)
    KartAktif = models.IntegerField(null=True)
    SiparisTamam = models.CharField(null=True)
    SiparisDurum = models.CharField(null=True)
    GirenKg = models.FloatField(null=True, verbose_name="Sipariş Kg")
    GirenAdet = models.FloatField(null=True)
    Kg = models.FloatField(null=True, verbose_name="Kalan Kg")
    Adet = models.FloatField(null=True)
    PlanlananMm = models.FloatField(null=True)
    Siparismm = models.FloatField(null=True)
    SonTermin = models.DateTimeField(null=True)
    FirmaAdi = models.CharField(null=True)
    KondusyonTuru = models.CharField(null=True)
    BilletTuru = models.CharField(null=True)
    PresKodu = models.CharField(null=True)
    Profil_Gramaj = models.FloatField(null=True)
    YuzeyOzelligi = models.CharField(null=True)

    class Meta:
        managed = False
        db_table = 'View051_ProsesDepoListesi'

class TestereDepo(models.Model):
    KartNo = models.IntegerField(null=True, blank=True)
    ProfilNo = models.CharField(null=True, blank=True)
    BulunduguYer = models.CharField(null=True, blank=True)
    KartAktif = models.IntegerField(null=True)
    Aktif = models.IntegerField(null=True, blank=True)
    Mm = models.FloatField(null=True, blank=True)
    Adet = models.FloatField(null=True, blank=True)
    Kg = models.FloatField(null=True, blank=True)
    FirmaAdi = models.CharField(null=True)
    KondusyonTuru = models.CharField(null=True)
    Profil_Gramaj = models.FloatField(null=True)
    BilletTuru = models.CharField(null=True, blank=True)
    YuzeyOzelligi = models.CharField(null=True, blank=True)
    PresKodu = models.CharField(null=True, blank=True)
    SonTermin = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'View051_TestereDepoListesi'

class PlcData(models.Model):
    plc = models.CharField(blank=True, null=True)
    start = models.DateTimeField(null=True, blank=True)
    stop = models.DateTimeField(null=True, blank=True)
    event = models.CharField(blank=True, null=True)
    singular_params = models.JSONField(null=True, blank=True)
    timed_params = models.JSONField(null=True, blank=True)
    position = models.CharField(null=True, blank=True)
    count = models.BigIntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'plcdata'

class PresUretimTakip(models.Model):
    siparis_kimlik = models.IntegerField(null=True, blank=True)
    kalip_no = models.CharField(null=True, blank=True)
    pres_kodu = models.CharField(null=True, blank=True)
    baslangic_datetime = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "PresUretimTakip"
        verbose_name_plural = "PresUretimTakipler"

class BilletDepoTransfer(models.Model):
    Create_Time = models.DateTimeField(null=True, blank=True)
    Kimlik = models.IntegerField(null=True, blank=True)
    GirenPartiNo = models.CharField(null=True, blank=True)
    GirenBoy = models.FloatField(null=True, blank=True)
    GirenAdet = models.FloatField(null=True, blank=True)
    GirenKg = models.FloatField(null=True, blank=True)
    GirenDepoKodu = models.CharField(null=True, blank=True)
    StokCinsi = models.CharField(null=True, blank=True)
    Aciklama = models.CharField(null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = 'BilletDepoTransfer'

class HammaddePartiListesi(models.Model):
    Billet = models.CharField(null=True, blank=True)
    DepoKodu = models.CharField(null=True, blank=True)
    StokKodu = models.CharField(null=True, blank=True)
    StokCinsi = models.CharField(null=True, blank=True)
    PartiNo = models.CharField(null=True, blank=True)
    TransferCikanKg = models.FloatField(null=True, blank=True)
    UretimKg = models.FloatField(null=True, blank=True)
    KalanKg = models.FloatField(null=True, blank=True)
    Cap = models.FloatField(null=True, blank=True)
    Aciklama = models.CharField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'View044_HammaddePartiListesi'

class HammaddeBilletStok(models.Model):
    parti_no = models.CharField(null=True, blank=True)
    kayit_tarihi = models.DateTimeField(auto_now=True)
    konum = models.ForeignKey(Location, on_delete=models.DO_NOTHING, null=True)
    boy = models.FloatField(null=True, blank=True)
    adet = models.IntegerField(null=True, blank=True)
    kg = models.FloatField(null=True, blank=True)
    stok_cinsi = models.CharField(null=True, blank=True)
    aciklama = models.CharField(null=True, blank=True)
    gelen_kimlik = models.IntegerField(null=True)

class HammaddeBilletCubuk(models.Model): #fırın için
    billet_no = models.CharField(null=True, blank=True)
    parti_no =models.CharField(null=True, blank=True)
    stok = models.ForeignKey(HammaddeBilletStok, on_delete=models.DO_NOTHING, null=True)
    guncel_boy = models.FloatField(null=True, blank=True)
    sira = models.IntegerField(null=True, blank=True)
    tarih = models.DateTimeField(null=True, blank=True)

class EkSiparis(models.Model):
    EkNo = models.IntegerField(null=True)
    KartNo = models.IntegerField(null=True)
    Kimlik = models.IntegerField(null=True)
    PresKodu = models.CharField(null=True)
    Termin = models.DateTimeField(null=True)
    BilletTuru = models.CharField(null=True, blank=True)
    Kg = models.FloatField(null=True, verbose_name="Ek Kg")
    KalankG = models.FloatField(null=True, verbose_name="Ek Kalan Kg")
    KimTarafindan = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    Silindi = models.BooleanField(null=True)
    MsSilindi = models.BooleanField(null=True)
    Sira = models.IntegerField(null=True)
    Durumu = models.FloatField(null=True)
    Adet = models.IntegerField(null=True)
    YuzeyOzelligi = models.CharField(null=True)
    ProfilNo = models.CharField(null=True, blank=True)
    PresGrubu = models.CharField(null=True, blank=True)
    Aktif = models.BooleanField(null=True, blank=True)
     
    class Meta:
        verbose_name="EkSiparis"
        verbose_name_plural="EkSiparisler"
    
    def production_started(self):
        """
        Check if production has started for this EkSiparis.
        """
        last_eksiparis_kalip = self.eksipariskalip_set.last()  # Get the latest EkSiparisKalip entry
        if last_eksiparis_kalip:
            return last_eksiparis_kalip.Uretim == "Basla"
        return False

class EkSiparisKalip(models.Model):
    EkSiparisBilgi = models.ForeignKey(EkSiparis, on_delete=models.DO_NOTHING, null=True, blank=True)
    KalipNo = models.CharField(null=True, blank=True)
    Durum = models.CharField(null=True, blank=True)
    HataKodu = models.CharField(null=True, blank=True)
    Uretim = models.CharField(null=True, blank=True)
    UretimBitirmeSebebi = models.CharField(null=True, blank=True)
    UretimBitirmeSebebiAciklama = models.CharField(null=True ,blank=True)
    Tarih = models.DateTimeField(auto_now=True, null=True)

class LivePresFeed(models.Model):
    MakineKodu = models.CharField(null=True)
    Start = models.DateTimeField(null=True)
    Stop = models.DateTimeField(null=True)
    Parameters = models.JSONField(null=True) #kalipNo
    Events = models.CharField(null=True) #ya da ForeignKey yap
    #node-red-contrib-postgresql  --> npm install node-red-

class Termik(models.Model):
    OvenName = models.CharField(null=True)
    SampleTime = models.DateTimeField(null=True)
    Bolge1 = models.FloatField(null=True)
    OrtaBolge = models.FloatField(null=True)
    Bolge2 = models.FloatField(null=True)
    Bolge1TB = models.FloatField(null=True)
    Bolge2TB = models.FloatField(null=True)
    ProgramSet = models.CharField(null=True)
    BatchNo = models.CharField(null=True)

class YudaForm(models.Model):
    YudaNo = models.CharField(unique=True ,null=True, blank=True)
    YeniKalipNo = models.CharField(null=True, blank=True)
    OnayDurumu = models.CharField(null=True, blank=True)
    ProjeYoneticisi = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="yuda_projeyoneticisi", blank=True, null =True)
    YudaAcanKisi = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="yuda_acankisi", blank=True, null =True)
    Tarih = models.DateTimeField(null=True, blank=True)
    RevTarih = models.DateTimeField(null=True, blank=True) #düzenleme yapıldığındaki tarih
    GüncelTarih = models.DateTimeField(null=True, blank=True) #her yeni yorumda güncellensin
    MusteriFirmaAdi = models.CharField(null=True, blank=True)
    SonKullaniciFirma = models.CharField(null=True, blank=True)
    KullanımAlani = models.CharField(null=True, blank=True)
    CizimNo = models.CharField(null=True, blank=True)
    ProfilSip = models.CharField(null=True, blank=True) #haftalık mı aylık mı yıllık mı sipariş
    ProfilMiktarBirim = models.CharField(null=True, blank=True)
    YillikProfilSiparisiMiktar = models.CharField(null=True, blank=True)
    MusteriOdemeVadesi = models.CharField(null=True, blank=True)
    AlasimKondusyon = models.JSONField(null=True, blank=True)
    DinTolerans = models.CharField(null=True, blank=True)
    BirlikteCalisan = ArrayField(models.CharField(max_length=200), blank=True, size=3, default=list)
    MetreAgirlikTalebi = models.CharField(null=True, blank=True)
    MATmin = models.CharField(null=True, blank=True)
    MATmax = models.CharField(null=True, blank=True)
    OnemliOlculer = models.CharField(null=True, blank=True)
    YuzeyPres = models.JSONField(null=True, blank=True)
    YuzeyEloksal = models.JSONField(null=True, blank=True)
    YuzeyBoya = models.JSONField(null=True, blank=True)
    YuzeyAhsap = models.JSONField(null=True, blank=True)
    TalasliImalat = models.CharField(null=True, blank=True)
    TalasliImalatAciklama = models.CharField(null=True, blank=True)
    Paketleme = models.CharField(null=True, blank=True)
    PaketlemeAciklama = models.CharField(null=True, blank=True)
    Silindi = models.BooleanField(null=True)
    Silindi_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, blank=True, null =True)
    meta_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.YudaNo

    class Meta:
        verbose_name="YudaForm"
        verbose_name_plural="YudaForms"
        permissions = [("gorme_yuda", "Yuda Gorme Yetkisi Var"), ("yonetici_yuda", "Yuda Proje Yoneticisi"), ("acan_yuda", "Yuda Acan Kisi")]

class YudaOnay(models.Model):
    Yuda = models.ForeignKey(YudaForm, on_delete=models.DO_NOTHING, null=True, blank=True, related_name='yudaonay')
    Group = models.ForeignKey(Group, on_delete=models.DO_NOTHING, null=True, blank=True)
    Tarih = models.DateField(auto_now=True, null=True, blank=True)
    OnayDurumu = models.BooleanField(null=True, blank=True)

class YudaOnayDurum(models.Model):
    yuda_id = models.IntegerField(null=True, blank=True)
    yuda_tarih = models.DateTimeField(null=True, blank=True)
    firma_adi = models.CharField(null=True, blank=True)
    kaliphane_onay_durumu = models.IntegerField(null=True, blank=True)
    satis_onay_durumu = models.IntegerField(null=True, blank=True)
    mekanik_islem_onay_durumu = models.IntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'view1_yudadurum4'

class Yuda(models.Model):
    yuda_no = models.CharField(unique=True, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, blank=True, null=True, related_name="yuda_creater")
    deleted = models.BooleanField(default=False, blank=True, null=False)
    deleted_by = models.ForeignKey(User, on_delete=models.PROTECT, blank=True, null=True, related_name="yuda_deleter")
    create_time = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    edit_time = models.DateTimeField(auto_now=True, blank=True, null=True)
    meta_data = models.JSONField(null=True, blank=True) # last_comment_time burada mı olmalı yoksa dışarıda mı olmalı
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='children', blank=True, null=True) # child yudaları getir-> parent_instance.children.all() 
    #  

    #YuklenenDosyalar = models.FileField(max_length=250, upload_to='media/', blank=True, null=True)

class Parameter(models.Model):
    ParentId = models.ManyToManyField("self", symmetrical=False, blank=True)
    Isim = models.CharField(null=True, blank=True)
    Tag = models.CharField(null=True, blank=True) #appname-yuda gibi

    def __str__(self):
        return self.Isim

class MyFile(models.Model):
    """ my_yuda = models.ForeignKey(YudaForm, related_name="files", on_delete=models.DO_NOTHING, null=True, blank=True)
    file_type = models.CharField(null=True, blank=True)
    file = models.FileField(upload_to='media/') """
    
class UploadFile(models.Model):
    File = models.FileField(upload_to='media/')
    FileTitle = models.CharField(null=True, blank=True)
    FileSize = models.IntegerField(null=True, blank=True)
    FileModel = models.CharField(null=True, blank=True)
    FileModelId = models.CharField(null=True, blank=True)
    UploadDate = models.DateField(auto_now=True, null=True, blank=True)
    UploadedBy = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="file_uploaded_by", blank=True, null =True)
    OriginFile = models.ForeignKey("self", on_delete=models.DO_NOTHING, blank =True, null=True)
    Note = models.CharField(null=True, blank=True)

    def __str__(self):
        return self.File

class Comment(models.Model):
    Kullanici = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    FormModel = models.CharField(null=True, blank=True)
    FormModelId = models.CharField(null=True, blank=True)
    Kategori = models.CharField(null=True, blank=True)
    Tarih = models.DateTimeField(null=True, blank=True)
    EditTarih = models.DateTimeField(null=True, blank=True)
    Aciklama = models.CharField(null=True, blank=True)
    ReplyTo = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    Silindi = models.BooleanField(default=False ,null=True, blank=True)
    ViewedUsers = models.ManyToManyField(User, related_name='viewed_comments', blank=True)  # Field to track viewed users

    def mark_viewed(self, user):
        """
        Mark a comment as viewed by a user.
        """
        self.ViewedUsers.add(user)

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    new_made_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_notifications', null=True)
    message = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, null=True)
    where_id = models.IntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False, null=True, blank=True)
    is_marked = models.BooleanField(default=False, null=True, blank=True)
    col_marked = models.CharField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

class UretimBasilanBillet(models.Model):
    Siralama = models.IntegerField(null=True, blank=True)
    KalipNo = models.CharField(max_length=250, null=True, blank=True)
    PresKodu = models.CharField(max_length=20, null=True, blank=True)
    Sure = models.IntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'UretimBasilanBillet'

class LastProcessEmail(models.Model):
    email_id = models.CharField(max_length=255, null=True)

    def __str__(self):
        return self.email_id
    
class LastCheckedUretimRaporu(models.Model):
    Siralama = models.IntegerField(null=True)
    TarihSaat = models.DateTimeField(auto_now_add=True, null=True, blank=True)

class IO_List(models.Model):
    line = models.CharField(max_length=250, null=True, blank=True)
    unit = models.CharField(max_length=250, null=True, blank=True)
    ip = models.CharField(max_length=250, null=True, blank=True)
    label = models.CharField(max_length=250, null=True, blank=True)
    address = models.CharField(max_length=250, null=True, blank=True)
    protocol = models.CharField(max_length=250, null=True, blank=True)
    writable = models.BooleanField(null=True, blank=True)
    frequency = models.IntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'IO_List'

class Recipe(models.Model):
    datetime = models.DateTimeField(auto_now=True)
    profile_number = models.CharField(max_length=250, null=True, blank=True)
    parameters = models.JSONField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'Recipe'

# class WorkCenter(models.Model):
#     name = models.CharField(max_length=250, null=True, blank=True)
#     capacity = models.FloatField(null=True, blank=True)
#     personel_count = models.IntegerField(null=True, blank=True)
#     setup_time = models.FloatField(null=True, blank=True)
#     cleanup_time = models.FloatField(null=True, blank=True)

#     def __str__(self):
#         return self.name
    
# class Operation(models.Model):
#     operation_name = models.CharField(max_length=250, null=True, blank=True)
#     work_center = models.ForeignKey(WorkCenter, on_delete=models.CASCADE, null=True, blank=True)
#     operation_time = models.FloatField(null=True, blank=True)

#     def __str__(self):
#         return self.operation_name
    
# class Product(models.Model):
#     product_name = models.CharField(max_length=250, null=True, blank=True)
#     product_type = models.CharField(null=True, blank=True)
#     unit_of_measure = models.ForeignKey(UnitOfMeasure, on_delete=models.CASCADE, null=True, blank=True)

class Personel(models.Model): # bölümü eklemeli miyim
    first_name = models.CharField(max_length=250, null=True, blank=True)
    last_name = models.CharField(max_length=250, null=True, blank=True)
    email = models.CharField(max_length=250, null=True, blank=True)
    department = models.CharField(max_length=250, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    date_joined = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name='Personel'
        verbose_name_plural='Personeller'


class KaliphaneIsEmri(models.Model):
    KartNo = models.CharField(primary_key=True, blank=True)
    Kimlik = models.IntegerField(null=True, blank=True) #UrtKimlik aynı olanların kimlikleri, unique değil
    UrtKimlik = models.IntegerField(null=True, blank=True)
    Tree_StokKodu = models.CharField(null=True, blank=True) # ProfilNo
    StokKodu = models.CharField(null=True, blank=True)
    OperasyonGrupKodu = models.CharField(null=True, blank=True)
    OperasyonKodu = models.CharField(null=True, blank=True)
    OperasyonAdi = models.CharField(null=True, blank=True)
    Durum = models.CharField(null=True, blank=True)
    Bolum = models.CharField(null=True, blank=True)
    UrtSiparisNo = models.CharField(null=True, blank=True)
    Operasyon = models.CharField(null=True, blank=True)
    SiparisNo = models.CharField(null=True, blank=True)
    Aciklama = models.CharField(null=True, blank=True)
    Varyant1 = models.CharField(null=True, blank=True) # pres
    Varyant2 = models.CharField(null=True, blank=True) # figür
    Varyant3 = models.CharField(null=True, blank=True) # çap
    Varyant4 = models.CharField(null=True, blank=True) # hazne
    Varyant5 = models.CharField(null=True, blank=True) # sadece kalıp
    Varyant6 = models.CharField(null=True, blank=True) # kapak
    Varyant7 = models.CharField(null=True, blank=True) # köprü
    Varyant8 = models.CharField(null=True, blank=True) # destek
    Varyant9 = models.CharField(null=True, blank=True) # yan no
    Varyant10 = models.CharField(null=True, blank=True) # bolster
    Varyant11 = models.CharField(null=True, blank=True) # mühre paket boy

    class Meta:
        managed = False
        db_table = 'View_URT_IsEmri'  # KALIPHANE 'kh' db

