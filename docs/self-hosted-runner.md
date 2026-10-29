# SDM Windows Verify runner

Verify, özel SDM deposuna kayıtlı `SDM-Windows` runner'ında çalışır.
Etiketler: `self-hosted`, `Windows`, `X64`, `sdm-ui`. Yayın workflow'u bu
değişiklikle taşınmaz; main'e push ve birleştirme yapılmaz.

Runner, proje checkout'undan ayrı `C:\actions-runner` klasöründedir.
İlk kurulan sürüm 2.338.2; resmi GitHub release varlığının SHA-256 değeri
`a1f17aa987fc8158bc7521d284912267a0d01b7c2c4684b33c86783b5e8221cc`
ile doğrulanmıştır. Kayıt anahtarı kısa süreli API anahtarıyla alınır;
anahtarlar veya yerel runner ayarları kaynak deposuna eklenmez.

Windows servisi ve otomatik başlangıç kurulmaz. Masaüstü/tray testleri için
runner açık kullanıcı oturumunda normal süreç olarak çalışır. Bilgisayar ve
runner çalışırken işler alınır; yeniden açılış sonrasında yerel PowerShell
başlatıcısı çalıştırılmalıdır:

```powershell
& C:\actions-runner\start-sdm-runner.ps1
```

Yerel başlatıcı `SDM_RUNNER_PYTHON` değişkenini mevcut Python 3.12 exe'sine
ayarlar ve PowerShell 7'yi süreç PATH'ine ekler. Kişisel SDK yolları bu
belgede veya workflow'da sabitlenmez. Verify, sürümü denetler ve checkout
içinde ayrı `.venv` oluşturur; bağımlılıkları yalnız bu ortama kurar.
Windows MSI Python kurulumu çalıştırılmaz. Node 22 `setup-node` aracılığıyla
runner'ın ayrı araç önbelleğine hazırlanır; sistemdeki Node değiştirilmez.
Pip/npm önbellekleri de runner klasörü altındadır.

Runner'ın checkout'u `C:\actions-runner\_work` altındadır; kullanıcının
çalışma deposu değildir. Gerçek SDM profili okunmaz/yazılmaz. UI ve tarayıcı
testleri mevcut geçici sahte profil kurallarını korur. Gerçek HTTP, SHA-256,
migration, kaynak manifesti ve gizli bilgi kontrolleri değiştirilmez.

Kurulumda YAML/PowerShell sözdizimi, workflow'daki gerçek sanal ortam hazırlık
adımı ve yeni sanal ortamdan native Tk açılışı sınanmıştır. Bu kontroller tam
Verify başarısı sayılmaz. Tam sonuç, GitHub koşumunun head commit'i ve bütün
adımları üzerinden ayrıca kontrol edilir. Kayıt/credential dosyaları ve
runner günlükleri Git'e veya yayına eklenmez.
