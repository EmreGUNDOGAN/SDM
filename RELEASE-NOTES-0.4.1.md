## SDM 0.4.1 — Daha net aktarım takibi

Bu sürüm, indirme yöntemini görünür kılar ve küçük pencerelerde menü erişimini düzeltir.

### Yenilikler ve düzeltmeler
- Sol menü fare tekerleği ve görünür kaydırma çubuğuyla kaydırılır; Ayarlar erişilebilir kalır.
- Detay penceresinde HTTP Range, tek HTTP bağlantısı veya HLS/DASH yöntemi ve gözlenen aktif aktarım sayısı gösterilir. Yapılandırılmış bağlantı limiti gerçek bağlantı sayısı olarak gösterilmez.
- HTTP parçalarının byte ilerlemesi ve HLS/DASH parçalarının gözlenen ilerlemesi listelenir; uzun videolarda son 80 parça korunur.
- Tek bağlantıya dönüşün nedeni detaylarda gösterilir.
- Tek bağlantı eklerken başlatmadan önce dosya boyutu incelenir; video kalite seçiminde bulunan boyut veya açıkça işaretlenmiş tahmin gösterilir. Sunucu boyut vermiyorsa bilinmiyor olarak kalır.
- YouTube HTTP akışlarının istek parçası boyutu dikkate alınır. 403 durumunda kaynak sayfa yalnızca bir kez yeniden çözümlenir; devam eden erişim hatası doğru açıklamayla gösterilir.
- Tahmini video boyutu artık kesin disk alanı gereksinimi gibi değerlendirilmez.

### Güncelleme
SDM’de **Ayarlar → Güncelleme → Güncellemeleri kontrol et** yolunu kullanın. Token gerekmez. Eklenti kurulum klasöründen yüklenmişse uygulama güncellendikten sonra eklenti menüsünden **Eklentiyi yenile** seçilebilir; açık video sayfasını yenileyin.

### Bilinen sınırlar
- Sunucu izinleri ve YouTube erişim sınırlamaları nedeniyle her 403 hatasının giderilmesi garanti değildir.
- Gözlenen aktarım sayısı uygulamanın izlediği HTTP/parça işçilerini ifade eder; işletim sistemi soket sayacı değildir.
- Eklentinin normal Chrome/Opera yüklemesinde yenileme akışının uçtan uca doğrulaması henüz tamamlanmamıştır. Gerekirse tarayıcıdaki SDM kartından Yeniden yükle kullanın.

### Paket doğrulama
Setup GitHub Actions üzerinde üretilir. SHA-256 doğrulama dosyası ve güncelleme bilgileri release varlıklarında bulunur. Kaynak kod deposu özeldir.
