# Generated by Django 4.2.2 on 2025-03-14 15:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ArslanTakipApp', '0121_testeredepo'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(blank=True, null=True)),
                ('machine_name', models.CharField(blank=True, null=True)),
                ('start_time', models.DateTimeField(blank=True, null=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('static_data', models.JSONField(blank=True, null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='unitofmeasure',
            name='conversion_factor',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='unitofmeasure',
            name='type',
            field=models.CharField(blank=True, choices=[('weight', 'Ağırlık'), ('volume', 'Hacim'), ('count', 'Adet'), ('length', 'Uzunluk')], max_length=50, null=True),
        ),
        migrations.CreateModel(
            name='TemporalData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dynamic_data', models.JSONField(blank=True, null=True)),
                ('event_id', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='ArslanTakipApp.eventdata')),
            ],
        ),
    ]
