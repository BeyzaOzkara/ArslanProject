# Generated by Django 4.2.2 on 2025-03-20 14:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DMS', '0002_realtimedata'),
    ]

    operations = [
        migrations.AddField(
            model_name='realtimedata',
            name='event_type',
            field=models.CharField(blank=True, null=True),
        ),
    ]
