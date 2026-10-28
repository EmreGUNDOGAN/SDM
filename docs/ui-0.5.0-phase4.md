# SDM 0.5.0 — 4. aşama: Ayarlar

Üçüncü aşama `a039ce18906a91b65f8f2c598faad593e2054824` üzerine kuruludur.
PR hedefi `codex/0.5.0-phase3-dialogs`. Üçüncü aşamanın GitHub Verify #7 işi,
hesap ödeme/harcama limiti engeli nedeniyle runner başlamadan durdu. Bu durum
başarılı doğrulama sayılmadı; kullanıcı bilgilendirildi. Yayın yapılmadı.

A08–A13: 200 px bölüm menüsü, altı bölüm, kartlar ve ortak kontroller.
SettingsContent, Odak için de gömülebilir. language anahtarı ve Türkçe/English
sayı biçimi korunur. Alan sınırları satır içinde gösterilir ve Kaydet engellenir.

Kuyruklar derin kopya üzerinde düzenlenir; gerçek queue_rules doğrulayıcısı ve
tarih/saat davranışı korunur. Ad değişikliği kayıt sırasında indirme
veritabanı ve çalışan/zamanlanmış kuyruk adlarına uygulanır. Kaydetmeden
uygulama tercihleri değişmez; geri yükleme de önce forma alınır.

Tarayıcı sürüm/durum bilgisi yalnız kimliği doğrulanmış eklenti isteğindeki
sınırlı tarayıcı adı ve sürümden gelir. Son temas 90 saniyeden eskiyse canlı
bağlantı doğrulanmış gösterilmez. Cookie veya profil okunmaz. Kaspersky
durumu gerçek kurulum dosyası aramasıdır; otomatik virüs taraması değildir.

Yedek içeriği DEFAULT_SETTINGS ile aynıdır; token, bağlantı anahtarı,
veritabanı ve indirilen dosyalar dahil değildir. Ayar içeriğindeki kullanıcı
klasör yolları kullanıcının kendi yedeğinde bulunur; kaynak depoya alınmaz.

Yerel doğrulama: mevcut dört görünüm, Atlas menü/ayar bağlantıları ve eski
pencere regresyonları; yeni 24 gerçek native görsel; sınırlar, kirli alan
sayısı, yedek içeriği, kayıt öncesi geri yükleme, İptal/Geri al, başarısız kayıt
ve gerçek sahte profil kaydı/DB kuyruk adı göçü. Kimliksiz tarayıcı isteğinin
durum değiştirememesi ayrıca sınanır. Gerçek HTTP ve SHA-256 tarayıcı
kontrolleri korunur. Kurulu program veya gerçek kullanıcı profili kullanılmadı.
