from django.contrib import admin
from .models import StockItem, Asset, StockTransaction, AssetTransfer

admin.site.register(StockItem)
admin.site.register(Asset)
admin.site.register(StockTransaction)
admin.site.register(AssetTransfer)
