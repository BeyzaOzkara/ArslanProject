# Generated by Django 4.2.2 on 2023-12-20 10:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ArslanTakipApp', '0043_alter_yudaform_revtarih_alter_yudaform_tarih'),
    ]

    operations = [
        migrations.RenameField(
            model_name='yudaonay',
            old_name='Onay',
            new_name='OnayDurumu',
        ),
        migrations.RemoveField(
            model_name='yudaonay',
            name='Aciklama',
        ),
        migrations.AddField(
            model_name='yudaonay',
            name='Kullanici',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='yudaonay',
            name='Yuda',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='ArslanTakipApp.yudaform'),
        ),
        migrations.AlterField(
            model_name='yudaonay',
            name='Tarih',
            field=models.DateField(auto_now=True, null=True),
        ),
    ]
