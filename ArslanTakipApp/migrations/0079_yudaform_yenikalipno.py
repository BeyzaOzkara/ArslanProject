# Generated by Django 4.2.2 on 2024-06-08 11:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ArslanTakipApp', '0078_eksipariskalip_tarih_eksipariskalip_uretim'),
    ]

    operations = [
        migrations.AddField(
            model_name='yudaform',
            name='YeniKalipNo',
            field=models.CharField(blank=True, null=True),
        ),
    ]
