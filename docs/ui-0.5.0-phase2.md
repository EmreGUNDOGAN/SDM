# SDM 0.5.0 — 2. aşama: Atlas ana pencere

Kullanıcı 2. aşamayı GPT-6.1 Sol / high ile onayladı. Kapsam A01, A02,
sağ ayrıntı paneli, araç/durum çubukları, A18 menüleri ve uygulama içi
köşe bildirimleridir. Sürüm 0.5.0 olarak kalır.

## Dal ve bağımlılık

Bu dal, Verify #5'te başarılı olan 1. aşama commit'i
`711faf72997ff028dfe1886c532bc8c252934d90` üzerine kuruludur.
İlk PR birleştirilmediğinden 2. aşama PR'ı
`codex/0.5.0-phase1-foundations` dalını hedefler. PR yalnız bu aşamanın
farklarını gösterir. Yardımcı hiçbir PR'ı birleştirmez; main'e push yapmaz.
Bu ara PR yayın adayı değildir.

## Uygulama

- `layout_atlas.py`: 232 px kenar menü, durum/kategori/kuyruk sayıları ve
  zamanlama saati; altta Araçlar → Masaüstü HUD → Ayarlar. Başlık, öğe sayısı,
  Ctrl+F araması ve yakalama durumu. Araç çubuğu mevcut eylemleri çağırır.
- `atlas_table.py`: native Treeview hücre sınırlarından çizilen aynı hizada
  başlık/satırlar; 54 px satır, uzantı karosu, kategori/alan adı alt satırı,
  durum rengi ve ince ilerleme. Uzun metinler üç noktayla kısalır. Sayı biçimi
  `language` ayarından gelir; başlık ve dosya adı verileri değiştirilmez.
- `atlas_details.py`: tekli/çoklu seçim paneli. Gerçek görev/parça ölçümleri,
  bilinmeyen boyut/bağlantı ayrımı ve mevcut eylemler. Yapılandırılan bağlantı
  üst sınırı, gözlenmiş bağlantı sayısı gibi gösterilmez. Seçim yoksa panel
  gizlenir ve liste genişler; çoklu seçimde özet ve toplu eylemler görünür.
- `atlas_view.py`: sunum amaçlı filtre/eylem/uzantı/alan adı yardımcıları.
  Adresteki kimlik bilgileri ve sorgu dizisi alt satıra yazılmaz.
- İndirme satırları kimliklerini korur; değişmeyen satırlar silinip yeniden
  eklenmez. Değişmeyen tablo görüntüsü yeniden yaratılmaz. Yenilemede seçim,
  native odak, yatay ve dikey kaydırma konumları sınanır.
- A18 sağ tık/Kaldır/Sütunlar/Kuyruk menüleri ortak PIL yüzeyini kullanır.
  Duruma göre geçersiz eylemler devre dışıdır. Sağ tık çoklu seçimi korur.
  Sütunlar'da dosya adı kilitlidir ve Varsayılana dön bulunur; ayar saklanır.
  Eski ID sütunu da isteğe bağlı olarak erişilebilir kalır.
- Ok tuşlarıyla menüde gezinilir; sağ/sol ile alt menüye girilip çıkılır.
  Checkbox ve radyo seçimi, kısayol, açıklama ve tehlikeli eylem görünümü ayrıdır.
  Tarayıcı kurulumu ve kuyruk ayarları uygun mevcut ayar sekmesini açar.
- SHA eşleşmesi, güncel sürüm bilgisi ve geçersiz bırakma bilgisi Atlas'ta köşe
  bildirimi olur. SHA uyuşmazlığı hata kutusudur. Windows bildirim tercihi
  yalnız pencere dışı bildirimi etkiler; uygulama içi bildirimleri kapatmaz.
  Tema değişimi/kapanışta bildirimler, bağlam menüsü ve bağlamalar temizlenir.
- Durum çubuğunda gerçek aktif sayı, hız sparkline'ı, oturum miktarı ve gerçek
  boş disk alanı bulunur. Disk sorgusu UI thread'ini bekletmez.
- Arama veya başka metin alanında Delete kullanmak seçili indirmeyi silmez.
  Boş alandaki bağlantı/dosya bırakma mevcut `on_drop` akışına bağlıdır.

## Taslağa göre kabul

Kaynak: kullanıcının tasarım paketindeki A01/A02/A18 PNG ve HTML'leri.
Örnek dosya adları, bağlantılar ve kullanıcı yolları koda kopyalanmadı.

- [x] A01: başlık/hücre hizası, canlı arama, bileşik durum/kategori/kuyruk
  filtreleri ve gerçek sayılar; seçim paneli açılır/kapanır.
- [x] A01: native satır kimliği/odak/seçim ve iki eksende kaydırma korunur;
  değişmeyen tablo aynı görüntüyü kullanır. Çoklu seçim özeti ve toplu eylemler.
- [x] A02: gerçek boş liste, boş filtre ve boş arama farklı metinlerdir.
  Aramayı temizle, yeni indirme, panodan yapıştır ve eklenti bağlantısı çalışır.
- [x] A18: 13 satır eylemi, duruma göre devre dışı öğeler, korunan çoklu seçim,
  adlandırılmış kuyruk alt menüleri, kalıcı sütun seçimi ve varsayılana dönüş.
- [x] Açık/koyu palet; 1440×900 ve 1080×640 yerleşimi incelendi. Dar ana alanda
  eylemler araç ipuçlu ikonlara döner, tablo yatay kayar; öğeler üst üste binmez.
- [x] CI'nın 1024 px masaüstü için ek olarak 924×640 gerçek Tk istemcisi sınandı.
  Yalnız test süreci minimum genişliği düşürür; ürünün 1080×640 minimumu değişmez.

Taslağa göre açık farklar: HUD girişi kullanıcı onayıyla alt gruba eklendi.
Gerekli olduğunda native kaydırma çubukları görünür. Panel, onaylı 300–340 px
aralığındaki ortak 320 px tokenını kullanır. Native Windows pencere çerçevesi
ve kesikli bırakma alanı Tk tarafından çizilir. Bilinmeyen ölçümler örnek
veriyle doldurulmaz. A19 karar/hata kutularının, diğer indirme pencerelerinin
ve ayar gövdesinin yeniden çizimi 3–4. aşamalardadır; mevcut işlevler erişilebilir.
Odak bu aşamada mevcut geçici yerleşim kabuğunu kullanmaya devam eder.

## Yerel doğrulama

- 82 birim testi başarılı: mevcut motor/güvenlik/tarayıcı/tema/göç/manifest
  testleri ve yeni Atlas sunum/önizleme regresyonları. Gerçek HTTP yanıtı ve
  SHA-256 doğrulamaları korunur. Göç testleri gerçek şema hazırlığını kullanır.
- Altı UI scripti ayrı geçici sahte profillerde doğrulandı:
  `test_ui_components.py`, `test_ui_031.py`, `test_ui_themes.py`,
  `test_ui_atlas.py`, `test_gui_transfer.py`, `test_cancel_remove_ui.py`.
  Sonraki küçük düzeltmeler için yalnız etkilenen scriptler yeniden çalıştırıldı.
- İptal fixture'ındaki hızlı yerel aktarım, UI ilk kez iptal etmeye çalışmadan
  tamamlanabiliyordu. Yanıt artık gerçek veri gönderdikten sonra iptal anına
  kadar açık tutulur. Test ancak gerçek veri gönderildiğinde iptal eder.
  12 canlı iptal/kaldırma, 25 sn son tarih, >50 heartbeat ve <1.5 sn gecikme
  koşulları korunur. Düzeltilmiş koşumun en kötü heartbeat aralığı 0.313 sn idi;
  bu ölçüm hız kazancı iddiası değildir.
- 8 ortak bileşen önizlemesi ve 10 Atlas önizlemesi zorunlu doğrulanır.
  PNG/palet/boyut/boş görüntü kontrolleri ve gerçek dosya SHA-256 değerleri
  raporlanır. Menüde düz zemin örneklenir; yumuşatılmış yuvarlak kenar
  pikselinin düz zeminle aynı olması beklenmez. Eksik/bozuk/yanlış paletli
  veya boş görüntü hata verir. Artifact kotası kullanılmaz.
- Manifest gönderilecek Git blob baytlarından yeniden üretilip kontrol edilir.
  Sözdizimi, gizli bilgi/yasak veri taraması ve staged whitespace kontrolü
  gönderim öncesinde tamamlanır; kesin sonuçlar PR açıklamasına kaydedilir.

Yerel doğrulama CI başarısı sayılmaz. Yeni PR'ın Verify bağlantısı alınınca
çalışma durdurulur. Gerçek kullanıcı profili ve kurulu program değiştirilmedi;
setup/portable, kurulum ve yayın yapılmadı. Kullanıcının izlenmeyen CLAUDE.md
dosyası gönderime eklenmez.
