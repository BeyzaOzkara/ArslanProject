# Mail raporu ayarları

Raporların adresleri Django admin panelindeki **Mail raporu ayarları** bölümündeki
ilgili rapor kaydından yönetilir. Kaydettikten sonra servis yeniden
başlatılmaz; sonraki mail kontrolü ve gönderim güncel ayarları okur.

## İlk kurulum

İlk kurulumda `0144_mailreportsettings` tabloyu ve sevkiyat ayarını oluşturur.
`0146_scheduled_mail_report_settings` saatli iki raporun mevcut listelerini ekler.
`0147_event_mail_report_settings` hareket sonrası iki raporu ve pres dağıtımlarını ekler.
Migration dosyaları hazırlanmıştır;
geliştirme sırasında gerçek veritabanına uygulanmamıştır.

1. Celery worker ve Beat'i durdurun; güncel kodu sunucuya aktarın.
2. Projenin Python ortamında çalıştırın:

   ```bash
   python manage.py migrate ArslanTakipApp 0147 --database=default
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

Ana sayfa mail göndermez.

## Saatli raporlar

| Admin kaydı | Mevcut çalışma saati | Başlangıç TO / CC |
| --- | --- | --- |
| Güncel Test Raporu | Her gün 07:00 | 16 / 6 |
| Profil Sipariş Takip Raporu | Her gün 07:00 | 1 / 2 |

Saatli raporlarda admin'den TO, CC ve gönderim aktifliği yönetilir; gönderici ve
deneme göndericisi alanları gösterilmez. Çalışma saatleri mevcut Celery Beat
ayarlarından gelir ve bu değişiklikte değiştirilmemiştir. Pasif bir raporu tekrar
açmak geçmişte kaçırılan çalışmaları tekrar göndermez; sonraki planlı saatte çalışır.

Güncel Test Raporu boş dökümde de gönderilir. Profil Sipariş Takip Raporu yalnızca
uygun kayıt varsa gönderilir. Önceki rapor içerikleri ve bu davranışlar korunmuştur.

YUDA ve şifre sıfırlama mailleri bu kayıtlara bağlı değildir.

## Hareket sonrası mailler

**Kalıp Transferi** ve **Test Alınması Gereken Kalıp** kayıtlarında:

- Üstteki TO/CC alanları bütün presler için **ortak** listeyi oluşturur; boş olabilir.
- Alt bölümdeki **Mail raporu pres dağıtımları** satırlarında hedefe özel TO/CC
  düzenlenir. Gönderimde ortak liste ve ilgili pres satırı birleştirilir.
- Pres/hedef kodu, lokasyondaki `presKodu` değeriyle aynı olmalıdır; örneğin
  `1100-1` veya `Yeni 1100`. Admin'den yeni satır eklenebilir.
- Transfer için mevcut 12 hedef, test maili için mevcut 8 pres dağıtımı başlangıç
  verisine aktarılır. Sonraki admin değişiklikleri üzerine yazılmaz.
- Transfer mailindeki **İşlemi yapan kullanıcıya da gönder** seçeneği başlangıçta
  açıktır. Test mailindeki **İlgili müşteri temsilcisine de gönder** de açıktır.
  Otomatik eklenen bu alıcılar istenirse bu seçeneklerle kapatılabilir.
- Rapor pasife alınırsa bütün presler için; tek bir pres satırı pasife alınırsa
  yalnızca o hedef için bütün gönderim durur. Kalıp hareketinin kaydı devam eder.
- Transfer hedefinin ayrı satırı yoksa önceki davranış korunur: ortak liste ve
  etkinse işlemi yapan kullanıcı kullanılır. Test mailinde pres satırı zorunludur;
  eksikse eski sabit bir liste kullanılmaz, hata kaydedilir.
- Transfer satırını **silmek**, sadece hedefe özel adresleri kaldırır. Ortak
  listeye de mail gitmesini durdurmak için satırı silmek yerine pasife alın.
- Ortak, pres bazlı ve dinamik bütün listeler boş kalırsa gönderim yapılmaz;
  yapılandırma hatası oluşur.

Yetki devrinde personel kullanıcısına, ana ayarı görüntüleme/değiştirme izinlerinin
yanı sıra **Mail raporu pres dağıtımı** görüntüleme/ekleme/değiştirme (gerekiyorsa
silme) izinleri de verilmelidir. Değişiklikler ana raporun admin geçmişinde görünür.

Bu iki kayıt için gönderici/test göndericisi alanları kullanılmaz. Önceden tanımlı
pres bazlı toplu test raporu fonksiyonu da aynı **Test Alınması Gereken Kalıp**
dağıtımını kullanır; bu fonksiyon için yeni bir zamanlama eklenmemiştir.
