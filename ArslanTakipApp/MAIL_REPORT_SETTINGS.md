# Sevkiyat raporu mail ayarları

Sevkiyat raporunun adresleri Django admin panelindeki **Mail raporu ayarları →
Sevkiyat Raporu** kaydından yönetilir. Kaydettikten sonra servis yeniden
başlatılmaz; sonraki mail kontrolü ve gönderim güncel ayarları okur.

## İlk kurulum

Bu sürüm ilk kez yüklenirken yeni tablo ve mevcut adreslerin başlangıç kaydı için
`0144_mailreportsettings` migrationı gerekir. Migration dosyası hazırlanmıştır;
geliştirme sırasında gerçek veritabanına uygulanmamıştır.

1. Celery worker ve Beat'i durdurun; güncel kodu sunucuya aktarın.
2. Projenin Python ortamında çalıştırın:

   ```bash
   python manage.py migrate ArslanTakipApp 0144 --database=default
   ```

3. Web uygulamasını, Celery worker ve Beat'i yeniden başlatın.
4. Admin panelinde başlangıç listesini kontrol edin. Mevcut 29 TO adresi (Kevser
   Molla dahil), 7 CC adresi, Serkan/Furkan/yazılım göndericileri ve yazılım deneme
   yönlendirmesi başlangıç verisine dahildir.
5. Gerekirse mail göndermeyen teşhis komutunu çalıştırın:

   ```bash
   python manage.py diagnose_sevkiyat --query --limit 5
   ```

Bu başlangıç verisi sonraki admin değişikliklerini üzerine yazmaz. Kayıt veya
tablo eksikse sistem eski sabit adreslere geri dönmez; hata kaydeder.

## Kullanım ve yetki

- TO, CC, izin verilen göndericiler ve deneme göndericileri ayrı alanlardır.
  Her satıra bir adres yazılabilir; virgül ve noktalı virgül de kabul edilir.
  Adresler küçük harfe çevrilir, aynı alandaki tekrarlar kaldırılır.
- Geçersiz adresler kaydedilemez. Gönderim aktifken TO ve izin verilen gönderici
  listeleri boş bırakılamaz. CC boş olabilir.
- Deneme göndericisi, izin verilen göndericiler listesinde de bulunmalıdır.
  Bu adresten gelen uygun bildirimde TO ve CC yalnızca o adres olur.
- Konu `sevkiyat`, içerik `sevkiyat tamam` koşulları geçerlidir. Harf boyutu ve
  fazla boşluklar tolere edilir. Raporda mailin gönderildiği gün esas alınır.
- **Gönderim aktif** kapatılırsa yeni bildirimler rapor üretmeden işlenir. Tekrar
  açmak, pasif dönemdeki bildirimleri otomatik olarak tekrar göndermez.
- Kaydı silmek ve desteklenmeyen rapor eklemek admin'den kapalıdır.
- Yönetimi devredeceğiniz kullanıcıya `staff` (personel durumu) ile
  `ArslanTakipApp | Mail raporu ayarı | Can view/change Mail raporu ayarı`
  izinlerini verin. Başka modellerin düzenleme yetkisini vermek gerekmez.
  Değişikliği yapan kullanıcı ve değişen alanlar admin'in **Geçmiş** bölümünde görünür.

Ana sayfa mail göndermez. Diğer raporlar henüz bu ayar kaydına bağlı değildir.
