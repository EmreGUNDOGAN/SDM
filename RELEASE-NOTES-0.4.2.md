## SDM 0.4.2 — Atlas, Orbit ve Nova

### Altı görünüm
- Atlas: sol gezinme, bilgi kartları, açık/koyu.
- Orbit: üst kategoriler, sağ oturum/kuyruk paneli, açık/koyu.
- Nova: tam genişlik, turuncu vurgu ve alt işlem şeridi, açık/koyu.
- Ayarlarda Atlas / Orbit / Nova — Açık Tema / Koyu Tema adları; tema adları için İngilizce Light / Dark seçimi. Eski light/dark ayarları Atlas’a taşınır.
- Arama açıklaması, temizleme, sonuç sayısı, boş durum, görünür seçim ve hover/basılı/klavye odak durumları. Görsel tasarım panoları esas alınmıştır; gerçek masaüstü yazı/render boyutları ve mevcut sütun tercihleri korunur.

### Diğer geliştirmeler
- Kaldır düğmesinde Listeden kaldır ve Dosyaları da kaldır; dosya silme mevcut onay ve çalışan aktarımı bekleme akışını korur.
- Video/ses için başlamadan zaman aralığı: hızlı kesim veya yeniden kodlayan hassas kesim. Kuyrukta seçim korunur; desteklenmeyen kaynak açıkça reddedilir. Hızlı kesimde anahtar kare kaynaklı saniye sapması olabilir; ağdaki ek parçaların miktarı sunucuya bağlıdır.
- Araçlar sekmelerle düzenlendi; ilgili açıklamalar ve bağlantı kontrolü alanı seçilen araca göre değişir.
- Güncelleme uygulama içinde indirilip doğrulanır, aktarımlar duraklatılır, eski işlem kapanınca görünmeyen kurulum yürütülür ve SDM yeniden açılır. Başarısız kurulum sonucu sonraki açılışta gösterilir.

### Güncelleme
Ayarlar → Güncelleme → Güncellemeleri kontrol et. Token gerekmez. 0.4.1’in eski güncelleyicisi bu geçişte kurulum ilerlemesini gösterebilir; görünmeden kurulum akışı 0.4.2 içindeki sonraki güncellemelerde kullanılır. Bu setup eski sessiz kurulumdan sonra da SDM’yi yeniden açar.

### Doğrulama
51 otomatik test; altı gerçek Tk arayüzü, arama/kategori filtreleri, seçim durumları, iki dilde tema adlarının kaydı; gerçek paralel aktarım, 12 iptal/silme döngüsü; gerçek HTTP + FFmpeg hızlı/hassas bölüm süreleri ve iptal; gerçek PowerShell’de eski işlemi bekleme ve başarı/hata yeniden açılma sırası. Kurulum paketinin gerçek dosya değiştirme adımı Actions üzerinde ayrıca derlenir; PowerShell testinde kurulum/yeniden açma sınırı fixture ile izole edilmiştir.

### Paket
GitHub Actions üretimi setup, eklenti ZIP’i, SHA-256 dosyası ve latest.json. Kaynak deposu özel kalır. Chrome/Opera normal eklenti yenilemesinin uçtan uca doğrulaması ve bütün kaynaklardaki 403 hataları için garanti verilmez.
