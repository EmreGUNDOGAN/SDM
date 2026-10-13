# SDM 0.4.0

Windows için modern indirme yöneticisi. Bu sürüm, indirmelerinizi planlamak, takip etmek ve tamamlanan dosyalarla çalışmak için yeni kontroller getirir.

## İndirme kontrolü

- **Ayrı kuyruklar ve öncelik:** Adlandırılmış kuyruklar, kuyruk başına eşzamanlılık ve yüksek/normal/düşük dosya önceliği.
- **Kolay zamanlama:** Takvim ve saat/dakika seçicileri, Bugün/Yarın kısayolları; haftanın günlerine göre tekrarlama, başlangıç ve durma saati. Gece yarısını geçen aralıklar desteklenir.
- **İnterneti rahatlat:** Tek düğmeyle toplam hızı azaltın; kapattığınızda önceki hız sınırı geri gelir.
- **Daha güvenli başlangıç:** Aynı bağlantı için uyarı, disk alanı kontrolü ve yetersiz alanda klasör seçimi.
- **Donma düzeltmesi:** İptal etme ve kaldırma işlemlerinde işçi görevleri arayüz kuyruğuna aktarılır; motor kilidi ile arayüz arasındaki bekleme giderildi.

## Canlı görünüm ve dosya araçları

- Küçük, taşınabilir masaüstü HUD’u; gerçek ölçümlerden hız grafiği ve aktif aktarım ortalaması.
- İsteğe bağlı otomatik ZIP/RAR çıkarma; arşivde dışarı çıkan yollar ve bağlantılar reddedilir.
- Mevcut altyazılarda dil ve SRT/VTT seçimi; otomatik altyazılar ayrıca belirtilir.
- Yerel video/ses kesme ve MP4/MKV/MP3/M4A/WAV dönüştürme. Kaynak dosya korunur; medya yeniden kodlanır.
- Önizlemeyle indirme klasörü düzenleme ve çoklu bağlantı erişim kontrolü.
- Tamamlandı penceresinde **Virüs tarat**: kurulu Kaspersky ile kullanıcı isteği üzerine tarama ve doğrulanmış rapor sonucu. Otomatik tarama yapılmaz.

## Güncelleme ve tarayıcı

- Güncellemeler public **SDM-Updates** deposundan alınır; GitHub tokenı gerekmez. Kurulumdan önce setup boyutu ve SHA-256 doğrulanır.
- Eklentide **Eklentiyi yenile**: kurulum klasöründeki dosyalar doğrulanır ve eklenti yeniden yüklenir; klasör açtırılmaz. Tarayıcı açılışında farklı sürüm algılanırsa aynı doğrulama uygulanır.
- Canva istisnası, tarayıcıdan indirme öncesi seçim ve mevcut açık/koyu tema korunur.

## Kurulum

1. SDM’yi sistem tepsisinden kapatın ve **SDM-Setup-0.4.0.exe** dosyasını çalıştırın.
2. Chrome/Opera için ilk kurulumda geliştirici modunda SDM kurulumunun **extension** klasörünü bir kez yükleyin.
3. 0.3.1 eklentisinden geçerken tarayıcıdaki **Yeniden yükle** düğmesini bir defa kullanın. Sonraki sürümlerde SDM’nin **Eklentiyi yenile** düğmesi kullanılabilir. Açık video sayfasını yenileyin.

## Bilinmesi gerekenler

- Zamanlama SDM açıkken çalışır. Tarayıcı eklentisi mağazadan dağıtılmamaktadır; başka klasörden yüklenen kopyalar kendiliğinden güncellenemez.
- Kaspersky bilgisayarda kurulu olmalıdır. Arşiv içeriğinin taranması Kaspersky ayarlarına bağlıdır; “tehdit bulunmadı” kesin güvenlik garantisi değildir.
- Parolalı veya bağlantı içeren arşivler otomatik çıkarılmaz. Medya araçları DRM kaldırmaz; oturum gerektiren kaynaklar desteklenmeyebilir.
- Hız sunucuya, bağlantıya ve diske bağlıdır; paralel indirme her kaynakta daha hızlı olmayı garanti etmez.
- Setup dijital olarak imzalanmamıştır. Kaynak kodlar ayrı özel depoda tutulur; bu public depo kurulum dosyaları ve sürüm bilgilerini sunar.

Kurulum dosyası **GitHub Actions Windows runner** üzerinde üretilir. Dosya bütünlüğü için aynı sürümün `.sha256` dosyasını kullanın.
