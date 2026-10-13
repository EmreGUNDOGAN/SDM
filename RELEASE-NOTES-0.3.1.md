# SDM 0.3.1

## Arayüz ve indirme akışı

- Onaylanan modern düzen: açık/koyu/sistem teması, tek tip çizgili ikonlar, SDM pencere simgesi ve kompakt HUD.
- Tarayıcı indirmesinde önce **Şimdi indir / Kuyruğa ekle / İptal et** seçimi; uygun dosyalarda **Tarayıcıda indir** seçeneği.
- Şimdi indir seçilince ilerleme penceresi otomatik açılır. İptal et indirmeyi durdurur ve pencereyi kapatır. Pencerenin X düğmesi yalnızca pencereyi kapatır.
- Tamamlanınca Aç / Klasörü göster penceresi; ayarlardan kapatılabilir.

## Motor ve düzenleme

- Yeni indirmeler eski geçici parçaları kullanmaz. Dosyayla birlikte sil, yazıcı durduktan sonra ilgili parçaları da temizler.
- Uygun doğrudan video/ses HTTP akışları SDM'nin paralel Range motorunu kullanır. HLS/DASH parçaları eşzamanlı indirilebilir; desteklenmeyen akışlar normal video motoruna döner.
- Hız ve süre zaman ağırlıklı ortalamayla hesaplanır; toplam hız limiti normal dosya ve video aktarımları arasında paylaşılır.
- Kuyruk, uygulama açıkken zamanlı başlatma, kuyruk tamamlanınca 60 saniyelik iptal süresiyle bilgisayarı kapatma.
- Çoklu bağlantı yapıştırma, sürükle-bırak, oynatma listesinden seçim (ilk 100 öğe), tahmini video boyutları ve SHA-256 karşılaştırması.

## Tarayıcı ve ayarlar

- Sağ tıkta SDM ile indir ve bu sitede yakalamayı kapat.
- Canva varsayılan istisna; diğer siteler ve yakalanacak dosya uzantıları ayarlanabilir.
- Eklentiden 15 dakika, 1 saat veya tekrar açılana kadar yakalamayı durdurma.
- Anlaşılır hata açıklamaları ve çözüm düğmeleri.
- Ayar yedekleme/geri yükleme; erişim bilgileri yedeğe alınmaz.
- GitHub kararlı sürüm kontrolü, SHA-256 ile doğrulanan setup ve kullanıcı onayıyla güncelleme. Özel depo için yalnızca SDM deposunda Contents: Read yetkili token gerekir; Windows DPAPI ile şifrelenir.

## Kurulum

Açık SDM'yi sistem tepsisinden kapatıp **SDM-Setup-0.3.1.exe** dosyasını çalıştır. Güncellemeden sonra tarayıcı eklentisini yeniden yükle ve açık video sayfasını yenile.

Her sunucuda hız artışı garanti edilmez. DRM/oturum isteyen kaynaklar ve blob bağlantıları desteklenmeyebilir. Kuyruk zamanlaması SDM kapalıyken çalışmaz. Opera'nın ayrı uygulaması ayrıca test edilmemiştir; Chromium ortak eklenti akışı test edilmiştir.
