# SDM 0.3.2 — Silme sırasında donma düzeltmesi

0.3.1'de indirme iptal edilip kaldırılırken motor kilidi ile arayüz bildirimleri
birbirini bekleyebiliyordu. Silme, duraklatma, başlatma ve kapanma bildirimleri
artık motor kilidi tutulurken çağrılmıyor.

- Arka plan iş parçacıkları Tk arayüzünü çağırmak yerine güvenli bir olay kuyruğuna veri bırakıyor.
- İlerleme bildirimleri birleştiriliyor; tekrar eden video durum bildirimleri azaltılıyor.
- Silinen kayıtların geç gelen bildirimleri yok sayılıyor; video görevleri yalnızca arayüz iş parçacığında listeden kaldırılıyor.
- Başlatılırken iptal edilen indirme yeniden başlatılmıyor. İptal sonrasında yeni parça indirmeleri açılmıyor.
- Liste güncellemesi her satır için ayrı veritabanı bağlantısı açmak yerine tek sorgu kullanıyor.

Eski motorun karşılıklı beklemesi izole bir örnekte yeniden üretildi. 31 regresyon
testi, 12 gerçek iptal/kaldır döngüsü boyunca arayüz yanıtı, tema/popup/kuyruk ve
gerçek aktarım/tamamlanma kontrolleri geçti.

Yanıt vermeyen eski SDM'yi Görev Yöneticisi'nden kapatıp **SDM-Setup-0.3.2.exe**
ile güncelleyin. Bu sürümde eklenti değişmedi; mevcut 0.3.1 eklentisi kullanılabilir.
Klasör açtırmadan eklenti güncellemesi ayrı bir sonraki geliştirmedir.
