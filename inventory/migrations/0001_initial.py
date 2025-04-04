# Generated by Django 4.2.2 on 2025-03-15 10:17

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, null=True, unique=True)),
                ('detail', models.CharField(blank=True, null=True)),
                ('status', models.CharField(blank=True, choices=[('active', 'Active'), ('maintenance', 'Under Maintenance'), ('decommissioned', 'Decommissioned'), ('deleted', 'Deleted')], default='active', max_length=50)),
                ('metadata', models.JSONField(blank=True, default=dict, null=True)),
            ],
            options={
                'verbose_name': 'Asset',
                'verbose_name_plural': 'Assets',
            },
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, unique=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='subcategories', to='inventory.category')),
            ],
            options={
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
            },
        ),
        migrations.CreateModel(
            name='StockItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(unique=True)),
                ('name', models.CharField()),
                ('quantity', models.FloatField(default=0)),
                ('reorder_level', models.FloatField(default=10)),
                ('safety_stock_level', models.FloatField(default=5)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('metadata', models.JSONField(blank=True, default=dict, null=True)),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='inventory.category')),
            ],
            options={
                'verbose_name': 'StokItem',
                'verbose_name_plural': 'StokItems',
            },
        ),
        migrations.CreateModel(
            name='UnitOfMeasure',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=250, null=True)),
                ('abbreviation', models.CharField(blank=True, max_length=250, null=True)),
                ('type', models.CharField(blank=True, choices=[('weight', 'Ağırlık'), ('volume', 'Hacim'), ('count', 'Adet'), ('length', 'Uzunluk')], max_length=50, null=True)),
                ('conversion_factor', models.FloatField(blank=True, null=True)),
                ('precision', models.IntegerField(blank=True, null=True)),
                ('base_uom', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='inventory.unitofmeasure')),
            ],
            options={
                'verbose_name': 'Birim',
                'verbose_name_plural': 'Birimler',
            },
        ),
        migrations.CreateModel(
            name='StockTransfer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.FloatField()),
                ('transfer_date', models.DateTimeField(auto_now_add=True)),
                ('transfer_status', models.CharField(choices=[('pending', 'Beklemede'), ('completed', 'Tamamlandı'), ('canceled', 'İptal Edildi')], default='pending', max_length=50)),
                ('from_location', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='stock_from', to='inventory.asset')),
                ('responsible_person', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('stock_item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.stockitem')),
                ('to_location', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='stock_to', to='inventory.asset')),
            ],
        ),
        migrations.CreateModel(
            name='StockTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_type', models.CharField(choices=[('IN', 'Giriş'), ('OUT', 'Çıkış'), ('RETURN', 'İade'), ('SCRAP', 'Hurda')], max_length=50)),
                ('quantity', models.FloatField()),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('metadata', models.JSONField(blank=True, default=dict, null=True)),
                ('location', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='inventory.asset')),
                ('responsible', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('stock_item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.stockitem')),
                ('unit', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='inventory.unitofmeasure')),
            ],
        ),
        migrations.AddField(
            model_name='stockitem',
            name='unit',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='inventory.unitofmeasure'),
        ),
        migrations.CreateModel(
            name='AssetTransfer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='inventory.asset')),
                ('from_location', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='from_location', to='inventory.asset')),
                ('responsible_person', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
                ('to_location', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='to_location', to='inventory.asset')),
            ],
            options={
                'verbose_name': 'AssetTransfer',
                'verbose_name_plural': 'AssetTransfers',
            },
        ),
        migrations.AddField(
            model_name='asset',
            name='category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='inventory.category'),
        ),
        migrations.AddField(
            model_name='asset',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='located_assets', to='inventory.asset'),
        ),
        migrations.AddField(
            model_name='asset',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='sub_assets', to='inventory.asset'),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['status'], name='inventory_a_status_69dd7e_idx'),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['category'], name='inventory_a_categor_4ca7a3_idx'),
        ),
    ]
