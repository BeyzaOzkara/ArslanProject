from django.urls import path
from . import views

app_name = 'DMS'

urlpatterns = [
    path('event_data/', views.event_data_view, name='event_data'),
    path('api/get_event_data/', views.api_get_event_data, name='api_get_event_data'),
    path('api/update_event_data/', views.api_update_event_data, name='api_update_event_data'),
    path('api/get_kalip_nos/', views.api_get_kalip_nos, name='api_get_kalip_nos'),
]
