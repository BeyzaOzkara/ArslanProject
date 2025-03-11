# Generated by Django 4.2.2 on 2025-03-10 16:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ArslanTakipApp', '0120_comment_kategori_alter_yudaonaydurum_table'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestereDepo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('KartNo', models.IntegerField(blank=True, null=True)),
                ('ProfilNo', models.CharField(blank=True, null=True)),
                ('BulunduguYer', models.CharField(blank=True, null=True)),
                ('Mm', models.FloatField(blank=True, null=True)),
                ('Adet', models.FloatField(blank=True, null=True)),
                ('Kg', models.FloatField(blank=True, null=True)),
                ('BilletTuru', models.CharField(blank=True, null=True)),
                ('YuzeyOzelligi', models.CharField(blank=True, null=True)),
                ('PresKodu', models.CharField(blank=True, null=True)),
                ('SonTermin', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'View051_TestereDepoListesi',
                'managed': False,
            },
        ),
    ]
