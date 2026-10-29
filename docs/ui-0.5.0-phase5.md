# SDM 0.5.0 — 5. aşama: Odak Akışı

Dördüncü aşama `37acb502921f05dc98173421d5c924589e452be8` üzerine kuruludur.
PR hedefi `codex/0.5.0-phase4-settings`. Verify #7 ve #8 runner'ları GitHub
hesap ödeme/harcama limiti engeliyle başlamadı. Yerel başarı CI başarısı
olarak sunulmadı; kurulu SDM, main veya yayın değiştirilmedi.

B01/B02: 68 px ikon şeridi, üç özet kartı, 120 örnekli hız geçmişi,
durum sayıları, kategori filtreleri, sıralama ve kart listesi. Native Treeview
veri/seçim/odak/kaydırma API'si korunur. Kart görüntüsü gerçek satır sınırlarından
çizilir. Yenilemede kimlikler, seçim, kaydırma ve değişmeyen görüntü korunur.
Kart eylemi gerçek görev durumuna göre çağrılır; işleme aşamasında yeniden
başlatma yapılmaz. Ctrl/Shift çoklu seçim ve A18 menüsü korunur.

B03: 460 px çekmece listeyi daraltır. Ayrı Toplevel açılmaz; Atlas ile aynı
TransferContent kullanılır. Tek tık, çift tık/Enter ve otomatik ayrıntı
çağrısı çekmeceye yönlenir. Esc/× kapatır; periyodik yenileme geri açmaz.

B06: ortak SettingsContent ana alana gömülür. Kaydedilmemiş değişiklik sayısı,
Geri al/Kaydet ve şerit geçişinde gerçek Kaydet/Kaydetme/Vazgeç kararı vardır.
Kaydet görünümü yeniden kursa bile hedef gezinme devam eder. Kuyruklar menüsü
şeridin hemen sağında açılır. HUD girişi açma/kapatma eylemidir.

Yerel doğrulama: iki modda 12 gerçek native görünüm; sabit satırlar/odak/
kaydırma/görüntü, sıralama, tekli/çoklu seçim, çekmece boyutu, menü konumu,
üç karar düğmesinin gerçek tıklanması ve HUD aç/kapat. Görsel incelemenin
yakaladığı kart yüksekliği değişken gölgelemesi düzeltildi; üretilen resmin
Canvas boyutuyla eşleşmesi ayrıca kontrol edilir. Dört görünüm, Ayarlar ve
eski pencere regresyonları da sahte profillerde sınanır.

Önceki tema testi Odak'ın onaylı davranışına uyarlandı: tek seçimde çekmece
eylemleri, çoklu seçimde toplu çubuk sınanır. Görünürlük kontrolleri kaldırılmadı.
Eski Orbit/Nova çizim yolları son temizlik aşamasında kaldırılacak.
