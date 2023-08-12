from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'StokApp'
urlpatterns = [
    path('stockCard/', views.stockCard, name="stockCard"),
    path('stockCard/deneme', views.stockCard_deneme, name="deneme"),
]


""" app_name = 'StokApp'
urlpatterns = [
    path('stockCard/', views.StokCardView.as_view()),
] """