# Generated by Django 4.2.2 on 2023-07-29 09:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ArslanTakipApp', '0008_kalip_paketboyu_kalip_silinmesebebi_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='location',
            options={'permissions': [('dg_view_location', 'OLP can view location'), ('gonder_view_location', 'Gonderme Yetkisi Var')]},
        ),
    ]
