from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField

# Create your models here.
class Location(models.Model):
    locationName = models.CharField(max_length=255, verbose_name="Lokasyon İsmi")
    locationRelationID = models.ForeignKey("self", on_delete=models.CASCADE, blank =True, null=True)
    isPhysical = models.BooleanField(verbose_name="Fiziksel Bir Konum mu?")

    def __str__(self):
        return self.locationName
    
    class Meta:
        permissions = [("dg_view_location", "OLP can view location")]

    
#veritabanı isimlerini ingilizce yap
#blank true eklenecekleri belirle
class Kalip(models.Model):
    KalipNo = models.CharField(null=True)
    ProfilNo = models.CharField(null=True)
    Kimlik = models.IntegerField(null=True)#profilno ile çoğunda aynı
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
    ResimGramaj = models.FloatField(null=True)
    KalipAciklama = models.CharField(null=True)
    SikayetVar = models.IntegerField(null=True)
    KaliteAciklama = models.CharField(null=True)
    AktifPasif = models.CharField(null=True)
    Hatali = models.IntegerField(null=True)
    PresKodu = models.CharField(null=True)
    ResimDizini = models.CharField(null=True)
    PaketBoyu = models.CharField(null=True)
    kalipLocation = models.ForeignKey(Location, on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name="Kalıp"
        verbose_name_plural="Kalıplar"

    def __str__(self):
        return self.KalipNo

class DiesLocation(models.Model):
    kalipNo = models.CharField(primary_key=True, verbose_name="Kalıp Numarası")
    kalipVaris = models.ForeignKey(Location, on_delete=models.CASCADE, null=True)

    class Meta:
        managed = False
        db_table = 'View1_KalipLastLocation'

#bir yerden diğer yere aktarılması, tarih saat, kim
class Hareket(models.Model):
    kalipNo = models.CharField(null=False, verbose_name="Kalıp Numarası")
    kalipKonum = models.ForeignKey(Location, on_delete=models.CASCADE, blank=True, null =True, related_name="kalip_konum", verbose_name="Kalıp Konum")
    kalipVaris = models.ForeignKey(Location, on_delete=models.CASCADE, null =True, related_name="kalip_varis", verbose_name="Kalıp Varış")
    hareketTarihi = models.DateTimeField(auto_now=True, null=True)
    kimTarafindan = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Kim Tarafından")

    class Meta:
        verbose_name="Hareket"
        verbose_name_plural="Hareketler"

#Hareket object ne gözüksün??    
    def __str__(self):
        return str(self.kalipNo)
    
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
    ResimGramaj = models.FloatField(null=True)
    KalipAciklama = models.CharField(null=True)
    SikayetVar = models.IntegerField(null=True)
    KaliteAciklama = models.CharField(null=True)
    AktifPasif = models.CharField(null=True)
    Hatali = models.IntegerField(null=True)
    PresKodu = models.CharField(null=True)
    ResimDizini = models.CharField(null=True)
    PaketBoyu = models.CharField(null=True)
    class Meta:
        managed = False
        db_table = 'View020_KalipListe'