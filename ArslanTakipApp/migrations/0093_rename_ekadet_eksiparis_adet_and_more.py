# Generated by Django 4.2.2 on 2024-08-02 15:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ArslanTakipApp', '0092_eksiparis_aktif_eksiparis_presgrubu'),
    ]

    operations = [
        migrations.RenameField(
            model_name='eksiparis',
            old_name='EkAdet',
            new_name='Adet',
        ),
        migrations.RenameField(
            model_name='eksiparis',
            old_name='EkBilletTuru',
            new_name='BilletTuru',
        ),
        migrations.RenameField(
            model_name='eksiparis',
            old_name='EkDurumu',
            new_name='Durumu',
        ),
        migrations.RenameField(
            model_name='eksiparis',
            old_name='EkKalankG',
            new_name='KalankG',
        ),
        migrations.RenameField(
            model_name='eksiparis',
            old_name='EkKg',
            new_name='Kg',
        ),
        migrations.RenameField(
            model_name='eksiparis',
            old_name='EkPresKodu',
            new_name='PresKodu',
        ),
        migrations.RenameField(
            model_name='eksiparis',
            old_name='EkTermin',
            new_name='Termin',
        ),
        migrations.RenameField(
            model_name='eksiparis',
            old_name='EkYuzeyOzelligi',
            new_name='YuzeyOzelligi',
        ),
    ]
