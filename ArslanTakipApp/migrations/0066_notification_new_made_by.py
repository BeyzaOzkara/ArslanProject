# Generated by Django 4.2.2 on 2024-04-20 10:09

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ArslanTakipApp', '0065_alter_comment_silindi_alter_notification_is_marked_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='new_made_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='created_notifications', to=settings.AUTH_USER_MODEL),
        ),
    ]
