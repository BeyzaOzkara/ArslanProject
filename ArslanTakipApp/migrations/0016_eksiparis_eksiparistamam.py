# Generated by Django 4.2.2 on 2023-08-30 16:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ArslanTakipApp', '0015_eksiparis_ekdurumu'),
    ]

    operations = [
        migrations.AddField(
            model_name='eksiparis',
            name='EkSiparisTamam',
            field=models.CharField(null=True),
        ),
    ]
