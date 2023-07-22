from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'StokApp'
urlpatterns = [
    path('stockCard/', views.stockCard, name="stockCard"),
]


""" app_name = 'StokApp'
urlpatterns = [
    path('stockCard/', views.StokCardView.as_view()),
] """