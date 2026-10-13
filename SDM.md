# SDM

Windows için kişisel indirme yöneticisi.

Uygulama başlığı ve sistem tepsisi adı SDM olarak düzenlenmiştir.
Ayarlar ve geçmiş `~/.sdm/`, günlükler `~/.sdm/sdm.log` altında tutulur.
Eski uygulamanın ayarları otomatik taşınmaz.

## Çalıştırma

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Windows setup (0.4.0)

Setup'a FFmpeg, ffprobe ve YouTube çözümlemesi için Deno dahildir.
Python veya FFmpeg'i ayrıca kurmanız gerekmez.

Setup sırasında Opera ve/veya Chrome eklentisini seçin. Dosyalar ve uygulama
bağlantısı hazırlanır. Tarayıcıda geliştirici modunu açıp `extension`
klasörünü bir kez **Paketlenmemiş yükle** ile seçin. Tarayıcı onayı olmadan
mağaza dışı eklentiler sessizce kalıcı kurulamaz.

Video oynarken sağ üstte **SDM ile indir** düğmesi görünür. Tıklayınca
videoda bulunan çözünürlükler ve varsa MP3 seçeneği listelenir. Ayrı ses
ve görüntü MKV olarak birleştirilir; MP3 seçilirse yalnızca ses dönüştürülür.
Altyazılar varsayılan olarak indirilmez; altyazı sunucusundaki hatalar
video indirmesini engellemez.

Desteklenen sayfalar: YouTube, Vimeo, Dailymotion, TikTok, Instagram,
X/Twitter, Facebook, Twitch ve SoundCloud. Her sitenin erişim kuralları,
DRM, oturum gereksinimleri ve bölge kısıtları indirmeyi engelleyebilir.
Eklenti tarayıcı çerezlerini ve şifrelerini okumaz.

## Entegre edilen özellikler

- Beyaz arayüz ve siyah metin; ana tabloda indirilen ve kalan boyut.
- Sütunlar menüsüyle görünür alan seçimi; seçimler yeniden açılışta korunur.
- Yeni indirmede otomatik açılan detay penceresi, duraklat/devam/iptal,
  bağlantı ilerleme çubuğu, detayları gizle ve tamamlanınca kapat.
- Hız tek ölçüm noktasından zaman ağırlıklı ortalamayla hesaplanır; süre
  ilk saniyelerde hesaplanıyor olarak, sonra yaklaşık değer olarak gösterilir.
- Normal HTTP/HTTPS dosya indirmeleri eklenti tarafından duraklatılır.
  SDM bağlantıyı doğrulayıp kabul ederse aktarılır; kabul etmezse tarayıcı
  devam eder. Blob bağlantıları ve tarayıcı oturumu isteyen dosyalar
  doğrudan aktarılmaz. Yerel ağ adresleri otomatik yakalamadan dışlanır.
- Video kalite menüsü dışına tıklamak veya Esc tuşu menüyü kapatır.
- SDM logosu pencere, sistem tepsisi, görev çubuğu ve setup'ta kullanılır.

Yerel köprü yalnızca `127.0.0.1:49282` üzerinde çalışır; eklenti kimliği
ve kurulum başına oluşturulan gizli bağlantı anahtarı doğrulanır.

Kaynak ve lisans bildirimleri için UPSTREAM-NOTICES.md dosyasına bakın.
