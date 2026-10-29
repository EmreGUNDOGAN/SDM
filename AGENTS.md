# SDM Çalışma Kuralları (Kural Kitabı)

Bu dosya SDM deposundaki bütün çalışmalar için geçerli kural kitabıdır.

## Başlamadan önce
- Kodlamadan önce model ve iş ağırlığı seçilir. Öneri kullanıcıya bildirilir; kullanıcı seçip onaylamadan başlanmaz. Ağırlığı artırmak gerekirse yeniden seçim beklenir.
- Kapsam ve sürüm numarası kullanıcı tarafından onaylanır. Yayımlanmış eski sürüm değiştirilmez; değişiklikler yeni sürümde çıkarılır.

## Profil ve kurulum güvenliği
- Gerçek kullanıcı profiline dokunulmaz. Testler ayrı, geçici ve sahte profillerde çalışır.
- Kurulu program güncellenmez; kurulumu kullanıcı dener.

## Yerel doğrulama
- Gönderim öncesinde yerel doğrulama yapılır: değişikliğe uygun testler, kaynak bütünlüğü, sözdizimi ve gizli bilgi taraması.
- Çözülen bir sorun veya yeni değişiklik yoksa aynı tam testler gereksiz yere tekrarlanmaz.
- Testler geçsin diye kontroller gevşetilmez. Hata araştırılıp düzeltilir.
- Şablon veritabanıyla test hızlandırması korunur; migration testleri gerçek şema hazırlığını kullanır.
- Tarayıcı testlerindeki gerçek HTTP yanıtı ve SHA-256 kontrolleri kaldırılmaz.

## Kaynak bütünlüğü manifesti
- Manifest güncellenir. Yeni/değişen dosyalar manifestte bulunur.
- Gönderilecek Git dosyalarının gerçek baytları manifestle karşılaştırılır.
- İlgisiz kullanıcı dosyaları gönderime eklenmez.

## Gönderim (dal + PR)
- Değişiklikler bir dal ve PR üzerinden gönderilir. Aynı işin mevcut PR'ı varsa uygun olduğunda o kullanılır.
- PR başlığı ve açıklaması son kapsamı ve sürümü anlatır.

## GitHub Verify
- Kullanıcının son talimatıyla kalan 0.5.0 aşamalarında Verify başlayınca bağlantı verilir ve sonuç yardımcı tarafından takip edilir; bu noktada kullanıcıdan "bitti/devam" beklenmez. Başarısız koşumlar araştırılıp düzeltilir ve yeniden doğrulanır.
- Her Verify sonucu ve doğruladığı commit kontrol edilir. Başarılı olmayan kaynak yayımlanmaz. Setup, doğrulanmış uygulama kodundan üretilir. Birleştirme ve yayın hakkındaki ayrı kurallar korunur.
- Verify sonrasında uygulama/test/CI kodu değişirse önceki başarı yeterli sayılmaz. Yalnız son doğrulama belgeleri ve manifest değişmişse bu fark açıkça kaydedilir; aynı uygulama için tam test gereksiz yere yeniden başlatılmaz.

## Windows paketi doğrulaması
- Derlenen paket ayrıca doğrulanır: uygulamanın açılışı, masaüstü/ML kontrolleri, tray'den tam çıkış, yeniden açılış ve güncelleyicinin kapatma yardımcısı geçici profillerde sınanır.
- Paket içindeki uygulama ve arayüz dosyaları kaynakla karşılaştırılır; gizli bilgi taraması ve setup SHA-256 kontrolü yapılır.

## Yayın
- Yayın ayrımı korunur. Kaynak kod ve portable arşiv yalnız özel depoda tutulur. Herkese açık sürüm deposuna yalnız setup, SHA dosyası ve sürüm açıklaması konur. Token, kullanıcı veritabanı ve gizli bağlantı dosyaları yayımlanmaz.
- Birleştirilen kaynak ile paketlenen kaynak eşleşmelidir.
- Mevcut yayımlanmış etiketler ve dosyalar değiştirilmez. Yeni sürüm kendi etiketiyle yayımlanır.

## Yayın sonrası
- İndirme ve güncelleme doğrulanır. Herkese açık setup ve SHA dosyaları GitHub hesabı olmadan indirilip karşılaştırılır. Önceki sürümden yeni sürüme güncelleme seçimi kontrol edilir.

## Teslim ve raporlama
- Son teslim kullanıcıya yapılır. Setup ve sürüm sayfası bağlantıları gönderilir. "Kuruldu" denmez; kullanıcı kurup deneyince sonucunu bildirir.
- Uzun işlerde yaklaşık her %10 ilerlemede kısa bilgi verilir. Her bildirimde yaklaşık toplam ilerleme, biten iş, kalan iş ve varsa engel belirtilir; ölçülmeyen ilerleme kesin yüzde gibi sunulmaz.
- Ölçülmemiş hız kazancı veya denenmemiş davranış başarılıymış gibi sunulmaz.

---

## Bu depoya özgü işletim notları

Aşağıdakiler kuralların bu depoda nasıl uygulanacağını açıklar; kuralların yerine geçmez.

- **`main`'e push = yayın.** `.github/workflows/release.yml`, `main` dalına her push'ta testleri çalıştırır, setup derler ve `app_version.py`'deki sürümle GitHub yayını oluşturur. Bu yüzden `main`'e doğrudan push yapılmaz ve hiçbir PR yardımcı tarafından birleştirilmez. Birleştirme kullanıcının kararıdır.
- **Geçici profil.** Uygulama ve testler `SDM_DATA_DIR` ortam değişkeniyle ayrı bir veri klasörüne yönlendirilir (CI'daki gibi: `build/ui-data`, `build/theme-ui-data` …). Gerçek `~/.sdm/` klasörüne asla yazılmaz, okunmaz, silinmez. Tarayıcı testleri için de ayrı, geçici bir tarayıcı profili kullanılır.
- **Yerel Verify runner.** Kullanıcı SDM deposuna Windows self-hosted runner kurulmasını onayladı. `SDM-Windows`, `sdm-ui` etiketiyle ayrı runner checkout'unda, açık Windows oturumunda ve servis olmadan çalışır. Verify, mevcut Python 3.12'den ayrı `.venv` üretir; kişisel SDK yolları/token/runner credential dosyaları depoya yazılmaz. Ayrıntılar: docs/self-hosted-runner.md. Yayın workflow'unun taşındığı veya paket/yayının tamamlandığı varsayılmaz.
- **Testler.** Motor ve güvenlik: `python -m unittest test_advanced_features test_responsiveness test_features test_download_safety test_progress_meter test_browser_files test_browser_bridge test_transfer_details test_video_access test_theme_section`. Arayüz: `test_ui_031.py`, `test_ui_themes.py`, `test_gui_transfer.py`, `test_cancel_remove_ui.py`, `test_section_live.py`, `test_update_handoff_live.py` (her biri kendi `SDM_DATA_DIR` klasörüyle). Eklenti: `test_*.cjs`.
- **Manifest.** Kullanıcının onayladığı SOURCE-MANIFEST.sha256 ve tools/source_manifest.py biçimi uygulanır; ayrıntılar aşağıdadır.
- **Gizli bilgi taraması.** Gönderilecek farkta token, parola, eklenti bağlantı anahtarı, kullanıcı veritabanı (`*.db`), `~/.sdm` içeriği veya kişisel yol bulunmadığı kontrol edilir.
- **İlerleme.** Uzun işlerde yaklaşık her %10'da kullanıcıya kısa durum bildirilir; GitHub Verify bağlantısı ve sonucu paylaşılır, kalan 0.5.0 aşamalarında onay beklemek için durulmaz.


## Onaylanan 0.5.0 arayüz yenilemesi

- Kullanıcı 0.5.0 hedefini ve altı aşamanın tamamlanmasını onayladı. Son talimat: kalan 3–6. aşamalar bitirilir ve Verify sonuçları yardımcı tarafından takip edilir. Model/çaba seçimi GPT-6.1 Sol / high olarak sürer; çaba artışı yeniden onay gerektirir.
- Altı aşama: (1) temel/token/bileşen/göç/manifest, (2) Atlas ana pencere, (3) Atlas pencereleri, (4) ayarlar, (5) Odak Akışı, (6) temizlik ve son uyumluluk kontrolleri. Her aşama ayrı dal ve PR. Kullanıcı kalan aşamaların tümünü ayrıca onayladığından aşama geçişlerinde yeniden onay beklenmez.
- Varsayılan yeni kurulum: design=atlas, color_mode=light. Tasarım ve renk modu bağımsızdır; system tercihi saklanır, başlangıçta Windows uygulama paleti okunur.
- Kullanıcının son isteği: Atlas/Odak ve Açık/Koyu/Sistem seçimi Kaydet beklemeden canlı önizlenir. Kaydet kalıcılaştırır; İptal, Escape, pencereyi kapatma, Geri al veya kaydetmeden ayrılma önceki görünümü geri getirir. Önizleme motor/pano ayarlarını uygulamaz, dosyaya yazmaz; diğer geçersiz veya kaydedilmemiş alanları korur.
- Eski atlas/orbit/nova açık ve koyu tema anahtarları Atlas'ın aynı renk moduna göç eder. Eski yedekler de aynı dönüşümü kullanır.
- Atlas'ta Masaüstü HUD, alt menüde Araçlar ile Ayarlar arasında bulunur.
- Odak'ta Kuyruklar ikonu şeridin hemen sağında kuyruk menüsünü açar; ayrı sayfa yapılmaz.
- language anahtarı ve sayı biçimi davranışı korunur. Genel bölümü etiketi: “Sayı biçimi · Türkçe (1,5) / English (1.5)”.
- Yayın başlığı release.yml içinde “SDM $env:SDM_VERSION — Atlas Pro ve Odak Akışı” olarak üretilir; başlığa sabit sürüm yazılmaz.
- Kaynak manifesti kökte SOURCE-MANIFEST.sha256 dosyasıdır. Git index'indeki her dosya için “<sha256>  <dosya yolu>” satırı bulunur, yola göre sıralanır; manifest kendisini içermez.
- Sıra: yalnız ilgili dosyaları git add ile hazırla; python tools/source_manifest.py write; manifesti git add ile hazırla; python tools/source_manifest.py check. Hashler Git'in gönderilecek blob baytlarından hesaplanır (CRLF checkout kopyasından değil). Check ayrıca hazırlanmamış izlenen değişiklikleri reddeder. Sonucu PR açıklamasına yaz.
- İlk aşama son taslak ekranların tamamlandığı anlamına gelmez. Ara PR'lar yayın adayı değildir. main'e birleştirme ve yayın yalnız kullanıcının kararıdır.
