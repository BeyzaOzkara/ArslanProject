# Generated by Django 4.2.2 on 2025-03-17 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ArslanTakipApp', '0125_delete_kalip'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parameter',
            name='ParentId',
            field=models.ManyToManyField(blank=True, to='ArslanTakipApp.parameter'),
        ),
    ]
