# SDM 0.5.0 — 6. aşama: temizlik ve son uyumluluk

Beşinci aşama `463e5e9bd0bd6984f3005873b443613b711dd215` üzerine kuruludur.
PR hedefi `codex/0.5.0-phase5-odak`. Altı ayrı aşama ve kullanıcı onaylı
GPT-6.1 Sol / high seçimi korunur. Yardımcı hiçbir PR'ı birleştirmedi.

## Son kaynak değişiklikleri

- Orbit/Nova çizim yolları ve eski tablo renderer'ı kaldırıldı. Eski tercih
  anahtarları yalnız göç katmanında korunur; mevcut göç testleri çalışır.
- Tema geçişi geçici pencereleri, HUD'u, inceleme işçilerini ve pencereye ait
  zamanlayıcıları temizler. Ayarlar kendi Kaydet/İptal yaşam döngüsünü korur.
- Kayıp dosya hatası adlandırılmış Listeden kaldır eylemi sunar. Filtre veya
  seçim değişse bile hata kutusunun asıl kaydı hedeflenir. İptal/silme motorunun
  mevcut güvenli bekleme/temizleme yolu kullanılır.
- Küçük hızlarda grafik ölçeği ayırt edilebilir ondalık değerler gösterir ve
  sayı biçimi tercihini kullanır. Ölçülmüş bağlantı sayısı açıkça adlandırılır.
- Thumbnail işçisi Tk nesnesini arka planda tutmaz. Genel ayarlar ikonu gerçek
  vektör geometrisiyle çizilir; fontta olmayan bir sembol kullanılmaz.
- Kurulum sürümü ve dosya adı build.ps1'in app_version.VERSION değerinden
  gelir. Eski 0.4.3 kurulum adı artık yeni paket için kullanılmaz. Mevcut
  yayımlanmış 0.4.3 dosyası veya etiketi değiştirilmedi.
- RELEASE-NOTES-0.5.0.md eklendi. README eski yayımlanmış setup bağlantısını
  korur ve 0.5.0 kaynak dalını henüz yayımlanmış kurulum gibi göstermez.

## Yerel doğrulama ve paket kapısı

Son kaynak için 88 birim testi: motor/güvenlik, gerçek HTTP eksik/yanlış yanıt
reddi, gerçek şema göçü, tercihler, manifest, ekran yakalama ve paket kodu
karşılaştırması. Şablon DB hızlandırması ve migration ayrımı korunur.

Native testler dört tasarım/modu, ortak bileşenleri, Atlas, tüm pencereleri,
Ayarlar, Odak, gerçek aktarımı, 12 iptal/kaldırma çevrimini ve pencere temizliğini
kapsar. 74 PNG (8 bileşen + 10 Atlas + 20 pencere/tarayıcı + 24 Ayarlar + 12
Odak) boyut/palet/içerik ve SHA-256 ile denetlenir. Kaynak masaüstü testi
gerçek sistem tepsisini açar, Çıkış eylemiyle sürecin tamamen bitmesini bekler,
ikinci süreçte yeniden açar ve dört görünümü tekrar dener. FFmpeg bölüm/MP3/
iptal/kaynak koruma ve gerçek PowerShell kapatma yardımcısı ayrıca sınanır.
Projede bağımsız ML özelliği/pipeline'ı bulunmadığından ML testi iddia edilmez.

Gerçek Chromium HTTP/Video/MP3 ve eklenti SHA-256 kontrolleri önceki aşamada
geçti; bu aşamada aynı tarayıcı/köprü kodu değiştirilmedi. Yenileme çağrısının
taklit olduğu sınır korunur; kurulu eklentinin gerçek reload'u iddia edilmez.
Tüm testler geçici sahte profiller ve yapay medya kullanır.

build.ps1, derleme öncesi/sonrası kaynak bütünlüğünü denetler. Ardından
tools/check_package.py zorunludur: frozen Python modüllerinin iç içe kodu
Git blob'larından derlenen kodla karşılaştırılır, UI varlık baytları kaynakla
eşleştirilir, paket kullanıcı verisi/gizli bilgi taramasından geçer. Setup
SHA-256 dosyası üretilip yeniden karşılaştırılır. Gerçek frozen masaüstü/tray
çıkış/yeniden açılışı iki sahte profilde ve PowerShell yardımcısı ayrıca çalışır.
Karşılaştırıcıda değişen iç fonksiyonun reddedilmesi birim testidir. Üretim
paketi test/CI yardımcılarını ve cache klasörlerini tools altına toplamaz.

Yayın workflow'u derlemeden önce tam motor/native/tarayıcı/medya doğrulamasını
çalıştırır; derlenen paket kapısı başarısızsa yayın adımına geçilmez. Kurulu
SDM güncellenmez ve gerçek HKCU eklenti kayıtlarına yazan eski installer testi
çalıştırılmaz. Kurulumu kullanıcı dener.

## Açık dış engel — başarı olarak sunulmaz

GitHub Verify #7/#8 ve Odak koşumu hesap ödeme/harcama limiti nedeniyle runner
başlamadan durdu. GitHub mesajı: “recent account payments have failed or your
spending limit needs to be increased”. Kullanıcı bilgilendirildi; hesapta
ödeme/limit değişikliği yardımcı tarafından yapılmadı.

Bu nedenle son GitHub Verify başarısı **henüz yoktur**. Windows setup/portable
derlemesi, frozen paket kapısının gerçek paket üzerinde çalıştırılması,
birleştirme ve yayın **yapılmadı**. Hazırlanmış paket kontrolü çalışmış gibi
sunulmaz. Engel giderildiğinde son commit Verify sonucu kontrol edilir;
uygulama/test/CI kodu değişirse yeniden doğrulama gerekir. Yalnız belge/manifest
farkı varsa açıkça kaydedilir. Yeni sürüm ancak kendi etiketiyle çıkar.

Yayın sonrası hesabı olmayan indirme/SHA karşılaştırması, önceki sürümden
güncelleme seçimi ve kullanıcıya setup/sürüm sayfası teslimi henüz uygulanamaz;
ortada yeni yayımlanmış setup yoktur. Kaynak/portable özel depoda kalır;
herkese açık sürüm deposuna yalnız setup, SHA ve sürüm notu konur.

## Deneme geri bildirimi: canlı görünüm önizlemesi

Atlas/Odak ile Açık/Koyu/Sistem seçimi artık Kaydet beklemeden ana pencere ve
ayar yüzeyinde önizlenir. Kaydet kalıcılaştırır; İptal/Escape/pencereyi kapatma,
Geri al ve Odak'ta kaydetmeden ayrılma önceki görünümü geri getirir. Yeniden
kurulan ayarlar, geçersiz sayılar/tarihler dahil ham alanları, kuyruk taslak ve
yeniden adlandırmalarını, bölümü ve kaydırma konumunu korur. Önizleme dosyaya
yazmaz, motor hızını veya pano ayarlarını uygulamaz. Başarılı Kaydet görünür
bildirim verir; kayıt istisnaları uygulama günlüğüne de yazılır.

test_ui_theme_preview.py gerçek Tk düğme olaylarıyla iki başlangıç yerleşimini,
taslak korumayı, iptal yollarını, başarısız/başarılı kaydı, DB kuyruk adını,
motor/pano yalıtımını, bekleyen önizlemeden önce Kaydet'i ve Sistem tercihini
sınar. Varsayılan native UI koşumuna eklendi. Bütün profiller yapay/geçicidir;
kullanıcının açık deneme uygulaması veya kurulu program değiştirilmez.

Kullanıcının önceki Kaydet sonrası değişmeme bildirimi yerelde yeniden
üretilemedi; bunu çözüldü saymak yerine canlı önizleme ve kayıt geri bildirimi
eklendi. Uygulama/test kodu değiştiği için önceki Verify sonuçları bu yeni
commit'in başarısı değildir; güncel commit yeniden Verify gerektirir.

## Odak başlık hizalaması ve daralan odak yüzeyi

Kullanıcının işaretlediği Odak başlığında arama kutusu 40 px iken düğmeler
38 px idi. Bu üç kontrol artık 40 px yüksekliğinde, aynı üst/alt kenarda ve
10 px aralıklarla durur. Odak arama yazısı düğmelerle aynı 13 px ölçüdedir;
placeholder tam görünür. Atlas'ın varsayılan arama yazısı değiştirilmez.
1080/1440 px ve açık/koyu görünümde native ekran görüntüleri ile sınanır.

Self-hosted Verify #13 ayrıca tema önizlemesinde bir çizim ValueError'ı
yakaladı. Odaklı düğmenin 1–2 px'e daraltılması aynı Pillow koordinat hatasını
yeniden üretir. Odak çerçevesi sığamayacağı kadar küçük yüzeyde çizilmez;
odak durumu korunur ve normal boyuttaki çizimde çerçeve yeniden görünür.
Regresyon gerçek Pillow çizimini sınar; Tk hata kontrolü kaldırılmaz.
Tema önizleme testi artık callback hatalarının tam çağrı izini raporlar.

Hizalama değişikliği Verify #13 çalışırken yalnız kullanıcının çalışma
checkout'unda hazırlandı; ayrı runner checkout'u ve çalışan koşum iptal
edilmedi/değiştirilmedi. Güncel uygulama/test kodu için yeni tam Verify
gerekir; önceki koşumlar yeni kodun başarısı sayılmaz.
