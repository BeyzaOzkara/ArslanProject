# Generated by Django 4.2.2 on 2023-11-02 14:40

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ArslanTakipApp', '0030_yudaonay_yuda'),
    ]

    operations = [
        migrations.AddField(
            model_name='yuda',
            name='yuklenenDosyalar',
            field=models.FileField(blank=True, max_length=250, null=True, upload_to='media/'),
        ),
        migrations.AlterField(
            model_name='yuda',
            name='Bariyerleme',
            field=models.CharField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='yuda',
            name='Folyo',
            field=models.CharField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='yuda',
            name='IstekYapanKisi',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='yuda_istekyapan', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='yuda',
            name='MetreAgirlikTalebi',
            field=models.CharField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='yuda',
            name='OnemliYuzeyler',
            field=models.CharField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='yuda',
            name='OzelPaketleme',
            field=models.CharField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='yuda',
            name='ProjeYoneticisi',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='yuda_projeyoneticisi', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tarih', models.DateTimeField(auto_now=True, null=True)),
                ('aciklama', models.CharField(blank=True, null=True)),
                ('eklenenDosyalar', models.FileField(blank=True, max_length=250, null=True, upload_to='media/')),
                ('form', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='ArslanTakipApp.yuda')),
                ('kullanici', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
