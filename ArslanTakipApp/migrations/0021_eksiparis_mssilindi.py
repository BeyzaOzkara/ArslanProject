# Generated by Django 4.2.2 on 2023-09-01 15:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ArslanTakipApp', '0020_rename_ekleyen_eksiparis_kimtarafindan'),
    ]

    operations = [
        migrations.AddField(
            model_name='eksiparis',
            name='MsSilindi',
            field=models.BooleanField(null=True),
        ),
    ]
