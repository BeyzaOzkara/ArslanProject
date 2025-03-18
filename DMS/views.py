from django.shortcuts import render
from .models import EventData, TemporalData


def event_deneme(request):
    EventData.objects.using('dms').create(
        event_type = 'deneme'
    )
    print("deneme")