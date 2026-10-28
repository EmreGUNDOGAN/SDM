# SDM 0.5.0 — 1. aşama: temel altyapı

Bu aşama, onaylı Atlas Pro ve Odak Akışı ekranlarının ortak altyapısını hazırlar.
Tam ekran yenilemesi altı aşamalı çalışmanın devamında yapılır. Bu PR tek başına
yayın adayı değildir. Hiçbir yardımcı PR birleştirmez veya main'e push yapmaz.

## Onaylanan kararlar

- Hedef sürüm 0.5.0; yayın başlığı `SDM $env:SDM_VERSION — Atlas Pro ve Odak Akışı`.
- Yeni kurulum `design=atlas`, `color_mode=light`. İki tasarımda renk modu bağımsızdır.
- `system`, Windows uygulama modunu açılışta çözer; tercih ayarda `system` kalır.
- Eski Atlas/Orbit/Nova açık ve koyu ayarları Atlas'ın aynı renk moduna taşınır.
  Aynı göç eski yedekler geri yüklenirken de uygulanır. Yeni anahtarlar önceliklidir.
- `language`, sayı biçimi davranışıyla korunur. Genel etiketi:
  “Sayı biçimi · Türkçe (1,5) / English (1.5)”. Tasarım adları değişmez.
- Atlas HUD girişi alt menüde Araçlar ile Ayarlar arasındadır.
- Odak kuyruk ikonu şeridin sağında menü açar; ayrı sayfa yapılmaz.

## Bu PR'ın kapsamı

- `ui_tokens.py`: açık/koyu semantik paletler, Inter tipografi, ölçüler, boşluklar,
  köşeler, dosya türleri ve durum renkleri.
- `theme_catalog.py`: yeni ayar modeli, eski ayar göçü ve sistem paleti çözümü.
- `theme_widgets.py`, `ui_controls.py`: PIL düğmeler, anahtar/onay kutusu, segment,
  seçim kartı/seçici, giriş alanı, satır kartı, çip girişi ve sahipli değişken izleri.
- `ui_indicators.py`: durum/dosya karoları, çubuk, halka/dönen gösterge, hız grafiği,
  küçük grafik, parça haritası, özet ve klavye/sürükleme destekli zaman çizelgesi.
- `ui_overlays.py`: özel menü/alt menü, modal ileti kabuğu, katlanabilir teknik
  ayrıntı, listeyi daraltan çekmece, köşe bildirimleri ve araç ipuçları.
- `ui_surface.py`: yeni ikonlar, önbellekli yüzeyler, kopya güvenliği ve 3× yazı.
- Mevcut ayarlar penceresi yeni tasarım/renk anahtarlarını kullanır. Tam A08–A13
  yerleşimi 4. aşamaya aittir. Sayı biçimi tercihi tasarım adlarını etkilemez.

**Geçici yerleşim sınırı:** Atlas'ın mevcut kabuğu korunur. Odak seçimi, 5. aşama
tamamlanana kadar mevcut Orbit yerleşim kabuğunu yeni paletle kullanır. Bu ekran
B01/B06 tamamlandı diye sunulmaz. Eski yerleşim dalları 6. aşamada temizlenecektir.
Motor, veritabanı şeması, köprü, video işleme ve güncelleyici mantığı değiştirilmez.
Tarayıcı testlerindeki HTTP yanıtı ve SHA-256 kontrolleri korunur.

## Kaynak manifesti

`SOURCE-MANIFEST.sha256`, Git index'indeki her dosyanın SHA-256 özetini
`<sha256>  <dosya yolu>` biçiminde, yola göre sıralı içerir; kendisini içermez.
Betik dosyaların checkout kopyasını değil, gönderilecek Git blob baytlarını okur.
Bu fark Windows CRLF dönüşümü sırasında da doğru kaynak bütünlüğü sağlar.

1. Yalnız bu işin dosyalarını açık yollarla `git add` ile hazırla.
2. `python tools/source_manifest.py write` çalıştır.
3. `git add SOURCE-MANIFEST.sha256` çalıştır.
4. `python tools/check_source.py` çalıştır. Bu ayrıca `source_manifest.py check`
   uygular; manifest/Git farkı veya hazırlanmamış izlenen değişiklik varsa başarısız olur.
5. Kontrol sonucunu PR açıklamasına kaydet.

İzlenmeyen kullanıcı dosyaları manifest/gönderim kapsamına otomatik eklenmez.
Kod değişince betik yeniden üretilir; kontroller test geçsin diye gevşetilmez.

## Doğrulama

- `python -m unittest test_advanced_features test_responsiveness test_features
  test_download_safety test_progress_meter test_browser_files test_browser_bridge
  test_transfer_details test_video_access test_theme_section test_ui_foundations
  test_source_manifest` — gerçek şema/motor yollarını koruyan regresyonlar.
- `python tools/run_ui_checks.py` — her script için ayrı, otomatik temizlenen
  sahte SDM profili: bileşenler, mevcut UI, dört birleşim, gerçek yerel HTTP aktarımı,
  iptal/kaldırma tepkiselliği. Pano izleme ve masaüstü bildirimi kapalıdır.
- Test pencerelerinin kendi HWND'sinden dört bileşen önizlemesi üretilir;
  masaüstü veya kullanıcının diğer pencereleri görüntüye alınmaz.
- `tools/check_source.py`: Git'e hazırlanmış Python/JS sözdizimi, bilinen gizli
  bilgi imzaları, yasak veri dosyaları ve kaynak manifesti. İmza taraması her tür
  gizli bilgiyi bulduğunu iddia etmez; gönderilecek fark ayrıca gözden geçirilir.

Verify iş akışı PR'ın **head commit** kaynağını doğrular; paket üretmez, kurmaz,
birleştirmez veya yayımlamaz. Başladığında bağlantı kullanıcıya verilip durulur.

### Yerel sonuçlar — 28 Ekim 2026

- Motor/güvenlik/temel regresyon koşumu: 63 test başarılı. Son göç-kayıt hatası
  düzeltmesinden sonra ilgili 8 göç/token testi ayrıca başarılı; değişmeyen tam
  takım yeniden çalıştırılmadı. Toplam 64 farklı birim testi kapsandı.
- Son kaynak üzerinde beş yerel UI scripti başarılı: ortak bileşenler, mevcut
  arayüz, dört tasarım/renk birleşimi, gerçek yerel HTTP aktarımı ve 12 iptal/kaldırma
  döngüsü. Her script ayrı, otomatik temizlenen sahte profilde çalıştı.
- Dört bileşen önizlemesi kendi test HWND'sinden alındı ve incelendi. Bunlar
  son A/B ekranlarının kabul görüntüleri değildir.
- Python/JavaScript sözdizimi, bilinen gizli bilgi imzaları, yasak veri dosyaları,
  Git farkının boşluk kontrolü ve gerçek Git blob manifesti yerelde doğrulandı.
- Kilitli bağımlılıklar proje içindeki Python 3.12 sanal ortamında kuruldu;
  `pip check` başarılı. Gerçek kullanıcı profili veya kurulu SDM değiştirilmedi.
- Setup/portable üretilmedi, kurulum denenmedi ve yayın yapılmadı.

## Sonraki aşamalar

2. Atlas ana pencere, tablo/panel, araç/durum çubuğu, menüler, bildirim bağlantıları.
3. Atlas indirme pencereleri, araçlar, HUD, grafik ve güncelleme iletileri.
4. Ayarların altı bölümü ve tüm Kaydet/İptal davranışı.
5. Odak ikon şeridi/kartları, ayrıntı çekmecesi ve ayarlar sayfası.
6. Eski yerleşimlerin temizliği, son görsel/işlevsel kabul ve yayın hazırlığı.

Araç çubuğu, ana menü ve diyalogların mevcut çağrılarını ortak bileşenlere taşıma
işi ilgili ekran aşamalarında yapılır. Otomatik inceleme, yeni ileti davranışları
ve eklenti görünümü de bu ilk altyapı PR'ında tamamlandı sayılmaz.
