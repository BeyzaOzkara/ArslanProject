# Generated by Django 4.2.2 on 2024-09-24 15:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ArslanTakipApp', '0095_presuretimtakip'),
    ]

    operations = [
        migrations.AddField(
            model_name='presuretimtakip',
            name='pres_kodu',
            field=models.CharField(blank=True, null=True),
        ),
    ]
