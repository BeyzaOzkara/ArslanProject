# Generated by Django 4.2.2 on 2024-04-18 11:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ArslanTakipApp', '0063_notification_is_marked'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='made_by',
            field=models.CharField(blank=True, null=True),
        ),
    ]
