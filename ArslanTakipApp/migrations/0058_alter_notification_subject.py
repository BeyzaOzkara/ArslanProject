# Generated by Django 4.2.2 on 2024-04-15 13:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ArslanTakipApp', '0057_notification_subject'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='subject',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
