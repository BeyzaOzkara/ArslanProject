from django.db import models

# Create your models here.

class Store(models.Model):
    StoreName = models.CharField(max_length=255, verbose_name="Depo İsmi")

class Group(models.Model):
    GroupName = models.CharField(max_length=255, verbose_name="Grup İsmi")

class Unit(models.Model):
    UnitName = models.CharField(max_length=255, verbose_name="Birim")

class Type(models.Model):
    TypeName =models.CharField(max_length=255, verbose_name="Stok Türü")

class StockCard(models.Model):
    StockStore = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, verbose_name="Depo")
    StockGroup = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
    StockType = models.ForeignKey(Type, on_delete=models.SET_NULL, null=True, verbose_name="Stok Türü")
    StockNo = models.CharField(max_length=255, verbose_name="Stok Kodu", unique=True) #?? sonradan düzenlenemez gruba göre otomatik oluşsun 
    StockName = models.CharField(max_length=255, verbose_name="Stok İsmi")
    StockDetail = models.CharField(max_length=255, verbose_name="Stok Detayı") #Ölçüler
    StockUnit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, related_name="stok_unit", verbose_name="Kullanılan Ölçü Birimi")
    PackageUnit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, related_name="package_uit", verbose_name="Ambalaj Birimi")
    PackageAmount = models.DecimalField(max_digits=255, decimal_places=3, null=True, verbose_name="Paket İçi Miktar")
    Equivalent = models.CharField(max_length=255, verbose_name="Muadil Stok") #liste
    Brand = models.CharField(max_length=255, verbose_name="Marka")
    ProductName = models.CharField(max_length=255, verbose_name="Ürün İsmi")
    CriticStock = models.DecimalField(max_digits=255, decimal_places=3, null=True, verbose_name="Kritik Stok Miktarı")
    MinOrderAmount = models.DecimalField(max_digits=255, decimal_places=3, null=True, verbose_name="Minimum Sipariş Miktarı")
    #birden fazla yüklenecek fotoğraflar vs için bi şeyler ayarla


