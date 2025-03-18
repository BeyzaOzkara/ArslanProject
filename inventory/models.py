from django.db import models
from django.contrib.auth.models import User

# Create your models here.

     
class UnitOfMeasure(models.Model):
    TYPE_CHOICES = [
        ('weight', 'Ağırlık'),
        ('volume', 'Hacim'),
        ('count', 'Adet'),
        ('length', 'Uzunluk'),
    ]
    name = models.CharField(max_length=250, null=True, blank=True)
    abbreviation = models.CharField(max_length=250, null=True, blank=True)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, null=True, blank=True)
    conversion_factor = models.FloatField(null=True, blank=True)
    base_uom = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    precision = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name="Birim"
        verbose_name_plural="Birimler"
   

class Category(models.Model):
    name = models.CharField(unique=True, blank=True)
    parent = models.ForeignKey("self", on_delete=models.DO_NOTHING, blank =True, null=True, related_name='subcategories')

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name or "Unnamed Category"
    

class Asset(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('maintenance', 'Under Maintenance'),
        ('decommissioned', 'Decommissioned'),
        ('deleted', 'Deleted'),
    ]
    name = models.CharField(unique=True, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.DO_NOTHING, null=True)
    parent = models.ForeignKey("self", on_delete=models.DO_NOTHING, blank=True, null=True, related_name='sub_assets')  
    location = models.ForeignKey("self", on_delete=models.DO_NOTHING, blank=True, null=True, related_name='located_assets')  
    detail = models.CharField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='active', blank=True)
    metadata = models.JSONField(default=dict, blank=True, null=True)


    class Meta:
        verbose_name = "Asset"
        verbose_name_plural = "Assets"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.name or "Unnamed Asset"
    
class AssetTransfer(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)  # Hangi varlık?
    from_location = models.ForeignKey(Asset, related_name="from_location", on_delete=models.SET_NULL, null=True)  
    to_location = models.ForeignKey(Asset, related_name="to_location", on_delete=models.SET_NULL, null=True)  
    date = models.DateTimeField(auto_now_add=True)  # Transfer tarihi
    responsible_person = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=True)

    class Meta:
        verbose_name = 'AssetTransfer'
        verbose_name_plural = 'AssetTransfers'

class StockItem(models.Model):
    code = models.CharField(unique=True)  # Benzersiz stok kodu uuid kodu kullanılabilir
    name = models.CharField()  # Malzeme adı
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)  
    quantity = models.FloatField(default=0)  # Mevcut stok miktarı
    unit = models.ForeignKey(UnitOfMeasure, on_delete=models.SET_NULL, null=True)  # Ölçü birimi (kg, litre, adet vs.)
    reorder_level = models.FloatField(default=10)  # Yeniden sipariş seviyesi
    safety_stock_level = models.FloatField(default=5)
    last_updated = models.DateTimeField(auto_now=True)  # Güncellenme zamanı
    metadata = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        verbose_name = 'StokItem'
        verbose_name_plural = 'StokItems'

    def __str__(self):
        return self.name or 'Unnamed StokItem'

class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ("IN", "Giriş"),
        ("OUT", "Çıkış"),
        ("RETURN", "İade"),
        ("SCRAP", "Hurda"),
    ]
    stock_item = models.ForeignKey(StockItem, on_delete=models.PROTECT)  # Hangi malzeme?
    transaction_type = models.CharField(choices=TRANSACTION_TYPES, max_length=50)   # Stok eklendi mi, tüketildi mi?
    quantity = models.FloatField()  # Miktar
    unit = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, null=True)  # Ölçü birimi
    date = models.DateTimeField(auto_now_add=True)  # İşlem tarihi
    responsible = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)  # Kim tarafından kullanıldı
    location = models.ForeignKey(Asset, on_delete=models.PROTECT, null=True, blank=True)  # Hangi depo/üretim hattı
    metadata = models.JSONField(default=dict, blank=True, null=True)

class StockTransfer(models.Model):
    STATUS_CHOICES = [
        ("pending", "Beklemede"),
        ("completed", "Tamamlandı"),
        ("canceled", "İptal Edildi"),
    ]
    stock_item = models.ForeignKey(StockItem, on_delete=models.PROTECT)  # Hangi malzeme?
    from_location = models.ForeignKey(Asset, related_name="stock_from", on_delete=models.PROTECT, null=True)  
    to_location = models.ForeignKey(Asset, related_name="stock_to", on_delete=models.PROTECT, null=True)  
    quantity = models.FloatField()  # Taşınan miktar
    transfer_date = models.DateTimeField(auto_now_add=True)  # Transfer tarihi
    responsible_person = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)   # Kim taşıdı?
    transfer_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')  