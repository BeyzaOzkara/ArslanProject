# Generated by Django 4.2.2 on 2025-03-15 10:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ArslanTakipApp', '0123_rename_event_id_temporaldata_event'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='temporaldata',
            name='event',
        ),
        migrations.RemoveField(
            model_name='unitofmeasure',
            name='base_uom',
        ),
        migrations.DeleteModel(
            name='EventData',
        ),
        migrations.DeleteModel(
            name='TemporalData',
        ),
        migrations.DeleteModel(
            name='UnitOfMeasure',
        ),
    ]
