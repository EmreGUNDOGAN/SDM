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

### Verify sonrası küçük pencere düzeltmesi

İlk Verify koşumunda kaynak kontrolleri ve 64 birim testi geçti; bileşen galerisinin
zaman çizelgesi klavye testi başarısız oldu. Aynı hata 1080×640 yerel pencerede
yeniden üretildi: 814 piksel yüksekliğindeki test içeriğinin en alt bileşeni
pencereye sığmadığından Tk tarafından görünür hale getirilmiyordu.

Galeri iki yönde kaydırılabilir hale getirildi. Klavye denemesi öncesinde hedef
görünür alana getirilir; görünürlük ve gerçek odak sahipliği ayrıca doğrulanır.
Tk'nin eşzamansız eşleme/odak işlemleri en çok iki saniye beklenir; hedef test
penceresi klavye olayından önce etkinleştirilir. Süre sonunda beklenen durum
oluşmamışsa test hata verir. Satır içi hata etiketinin görünürlüğü de aynı biçimde
beklenir ve denetlenir.
Sol ok tuşundan sonra bitişin 88 saniye olması ve değişiklik bildirimi denetlenmeye
devam eder. Kontrol atlanmadı veya gevşetilmedi. Her palet için üst alan ve zaman
çizelgesi olmak üzere iki ayrı HWND görüntüsü üretilir. Verify adımı 640 piksel
yüksekliği açıkça seçerek bu koşulu sürekli sınar.

Uygulama kodu değişmedi. Değişen bileşen testi küçük ve normal pencere boylarında
yerelde doğrulandı; başarılı ve değişmeyen motor/birim testleri tekrarlanmadı.
Test ve CI değiştiği için yeni commit için Verify yeniden gereklidir.

### Verify sonrası yerel pencere yakalaması ve kota düzeltmesi

İkinci Verify koşumunda kaynak kontrolleri ve 64 birim testi yeniden geçti.
Zaman çizelgesi kontrolü de geçti; sonraki koyu tema görüntüsünde beklenen zemin
rengi bulunmadı. Önizleme yüklemesi ayrıca GitHub artifact depolama kotası dolu
olduğu için başarısız oldu. Bunlar iki ayrı hatadır.

Pillow'un HWND yakalaması [kaynak kodunda](https://github.com/python-pillow/Pillow/blob/main/src/display.c)
pencere DC'sinden `BitBlt` ile kopyalama yapar. Yerelde bekleyen tema boyaması
koşulu yeniden üretildi: beyazdan koyuya ayarlanan pencere için bu kopya beyaz
piksel döndürürken, pencerenin kendisine güncel çizimi yaptırmak koyu piksel verdi.

`tools/window_capture.py`, yalnız test sürecine ait Tk üst penceresini kabul eder.
Tk'nin iç HWND'si yerine `wm frame` ile bulunan yerel üst pencere kullanılır;
istemci alanı, [RedrawWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-redrawwindow)
ve [PrintWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-printwindow)
ile senkron çizdirilir. Beklenen palet yakalama yardımcısına verilmez; çıktı
bitmapine beklenen renkler sonradan boyanmaz. GDI nesneleri işlem sonunda bırakılır.

Önizlemeler, test penceresinin üstü tamamen başka bir sahte pencereyle örtülüyken
alınır. Önceki zemin kontrolü korunur; ayrıca çizilmiş vurgu rengi işareti aranır.
Bekleyen tema boyaması için ayrı bir yerel yakalama kontrolü de vardır.
640 ve 840 piksel yükseklikte dört palet ve iki kaydırma konumu yerelde geçti.

`tools/report_component_previews.py`, sekiz PNG'nin varlığını, okunabilirliğini,
zemin/işaret renklerini ve gerçek dosya SHA-256 değerlerini zorunlu olarak denetler.
Eksik, bozuk, eski paletli veya boş görüntüler üç yeni regresyon testiyle reddedilir.
Sonuçlar artifact yüklemesi yerine GitHub iş özetine yazılır; mevcut kullanıcının
artifact dosyaları silinmez. Başarısız kontrolleri yok sayan bir seçenek eklenmedi.

Uygulama kodu yine değişmedi. Değişen yakalama/bileşen/rapor kontrolleri yerelde
çalıştırıldı; başarılı ve değişmeyen motor/birim/UI scriptleri tekrarlanmadı.
Test/CI farkı ve yeni yardımcılar manifestte yer alır; yeni commit Verify gerektirir.

### DIB belleğini okumadan önce çizim tamamlanması

Üçüncü Verify'da 67 birim testi ve kaynak kontrolleri geçti. Yerel UI adımı,
beyazdan koyuya geçişin ilk piksel kontrolünde durdu. Önceki yakalama değişikliği
bu CI hatasını gidermemiştir; yerel başarı CI başarısı olarak kabul edilmez.

Yakalama yardımcısında `CreateDIBSection` ile alınan bellek, GDI çizimi
tamamlanmadan CPU tarafından okunuyordu. [Microsoft'un sözleşmesi](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-createdibsection),
bu erişimden önce çizimin `GdiFlush` ile tamamlanmasını açıkça ister.
Okuma artık bu çağrıdan sonra yapılır; tamamlanma hatası yakalama hatasıdır.
Piksel beklentileri ve örtülü pencere kontrolleri aynen korunur.

Üç yeni regresyon testi, gecikmiş çizimi ancak flush sırasında belleğe aktaran
sahte Windows arka ucunu kullanır. Eski kodda güncel piksel ve hata aktarımı
testleri başarısız oldu; düzeltmeden sonra üçü de geçti. Kaynakların hata halinde
bırakılması ve başka sürece ait pencerenin reddi de denetlenir.
Önizleme raporunun üç regresyon testi de yeniden geçti. CI komutuna yeni test
modülü eklendi. Başarısız piksel kontrolü artık gerçek/beklenen rengi, Tk sürümünü
ve ekran derinliğini de bildirir.

640 piksel yükseklikte dört palet, sekiz gerçek pencere görüntüsü ve zorunlu
önizleme raporu geçici sahte profilde yerelde geçti. Değişmeyen motor testleri
ve diğer UI scriptleri yeniden çalıştırılmadı. Bu düzeltmenin CI üzerindeki etkisi
yeni Verify ile doğrulanacaktır; önceki başarılı adımlar yeni commit için
tamamlanmış doğrulama sayılmaz. Uygulama kodu değişmedi; test/CI değişiklikleri
ve regresyon dosyası manifest kapsamındadır.

## Sonraki aşamalar

2. Atlas ana pencere, tablo/panel, araç/durum çubuğu, menüler, bildirim bağlantıları.
3. Atlas indirme pencereleri, araçlar, HUD, grafik ve güncelleme iletileri.
4. Ayarların altı bölümü ve tüm Kaydet/İptal davranışı.
5. Odak ikon şeridi/kartları, ayrıntı çekmecesi ve ayarlar sayfası.
6. Eski yerleşimlerin temizliği, son görsel/işlevsel kabul ve yayın hazırlığı.

Araç çubuğu, ana menü ve diyalogların mevcut çağrılarını ortak bileşenlere taşıma
işi ilgili ekran aşamalarında yapılır. Otomatik inceleme, yeni ileti davranışları
ve eklenti görünümü de bu ilk altyapı PR'ında tamamlandı sayılmaz.
