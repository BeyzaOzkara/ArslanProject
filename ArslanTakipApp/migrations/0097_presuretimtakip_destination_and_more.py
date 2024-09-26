# Generated by Django 4.2.2 on 2024-09-26 08:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ArslanTakipApp', '0096_presuretimtakip_pres_kodu'),
    ]

    operations = [
        migrations.AddField(
            model_name='presuretimtakip',
            name='destination',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='ArslanTakipApp.location'),
        ),
        migrations.AddField(
            model_name='presuretimtakip',
            name='finish_reason',
            field=models.CharField(blank=True, null=True),
        ),
    ]
