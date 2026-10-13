## SDM 0.4.3 — Daha okunaklı, daha tutarlı arayüz

### Arayüz yenilikleri
- Atlas, Orbit ve Nova’nın açık/koyu görünümlerinde uygulamayla birlikte gelen Inter yazı ailesi kullanılır.
- Yazı boyutları ve ağırlıkları, ikon çizgileri, düğmeler, arama alanı ve bilgi kartları tutarlı hale getirildi.
- Nova artık sol kategori menüsü ve turuncu vurgu ile çalışır.
- Atlas tablosunda hücre çizgileri; daha belirgin ilerleme çubukları ve noktalı durum rozetleri eklendi.
- Dar pencerelerde bilgi kartlarının taşması ve sayısal sütunlarda birimlerin kesilmesi azaltıldı.
- Kategori seçimi, arama sonucu sayısı, boş liste açıklaması ve aramayı temizleme kontrolü belirginleştirildi.
- Fare ve klavye odağı ayrıldı; düğmelerde kesik odak çerçevesi kaldırıldı.

### Güncelleme
Ayarlar → Güncelleme → Güncellemeleri kontrol et. Public SDM-Updates deposu üzerinden token gerekmeden indirilir ve SHA-256 doğrulanır. 0.4.2’den güncellerken uygulama güncellemeyi indirir, kurulum için kapanır ve yeniden açılır.

### Doğrulama ve kapsam
Altı gerçek tema görünümü, kategori ve arama davranışı yerel Windows penceresinde kontrol edildi. Otomatik UI, aktarım ve iptal/silme regresyonları GitHub Actions üzerinde çalıştırılır; kurulum paketi yalnızca Actions üzerinde üretilir.

Bu sürüm arayüz düzeltmelerini içerir. Onaylanan tasarım görselleriyle piksel düzeyinde eşleşme iddiası yoktur; açılır menüler, kaydırma çubukları ve Orbit medya küçük resimleri için düzenlemeler devam edecektir. Tarayıcı eklentisinin yakalama davranışı bu sürümde değiştirilmedi.

### Paketler
- SDM-Setup-0.4.3.exe: Windows kurulum paketi
- SDM-Extension-0.4.3.zip: tarayıcı entegrasyonu
- SHA-256 ve latest.json: paket bütünlüğü ve uygulama içi güncelleme bilgileri
