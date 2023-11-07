from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import RegisterView

app_name = 'ArslanTakipApp'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('login/', auth_views.LoginView.as_view()),
    path('logout/', auth_views.LogoutView.as_view()),
    path('register/', RegisterView.as_view(), name= "register"),
    path('location/', views.location, name="location"),
    path('location/list/', views.location_list),
    path('location/kalip', views.location_kalip),
    path('location/hareket', views.location_hareket),
    # path('location/update', views.location_update),
    path('hareket', views.HareketView.as_view()),
    path('kalip/', views.KalipView.as_view()),
    path('kalip/liste', views.kalip_liste),
    path('kalip/rapor', views.kalip_rapor),
    path('qr/', views.qrKalite, name='qr'),
    path('siparis/', views.SiparisView.as_view()),
    path('siparis/list', views.siparis_list),
    path('siparis/max', views.siparis_max),
    path('siparis/child/<str:pNo>', views.siparis_child),
    path('siparis/ekle', views.siparis_ekle),
    path('eksiparis/', views.EkSiparisView.as_view()),
    path('siparis/presKodu/<str:pNo>', views.siparis_presKodu),
    path('eksiparis/list', views.eksiparis_list),
    path('eksiparis/acil', views.eksiparis_acil),
    path('kalipfirini/', views.KalipFirinView.as_view()),
    path('kalipfirini/meydan', views.kalipfirini_meydan),
    path('kalipfirini/goz', views.kalipfirini_goz),
    path('baskigecmisi/', views.BaskiGecmisiView.as_view()),
    path('baskigecmisi/list', views.baskigecmisi_list),
    path('yuda', views.YudaView.as_view()),
    path('yuda/<str:objId>', views.yuda),
    path('yuda/ekle', views.yuda_ekle),
    path('yudaDetail', views.YudaDetailView.as_view()),
]