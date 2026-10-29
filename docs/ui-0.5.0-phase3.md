# SDM 0.5.0 — 3. aşama: indirme ve yardımcı pencereler

İkinci aşamanın Verify başarılı `215fc5d310eb1f672082e58a74af06021fd08faa`
commit'i üzerine kurulur. PR hedefi `codex/0.5.0-phase2-atlas-main`.
Kullanıcı kalan aşamaları ve Verify sonuçlarının otomatik takibini onayladı.
Ara PR yayın adayı değildir; main'e push veya birleştirme yapılmadı.

- A03: otomatik, üç işçili bağlantı inceleme; dosya/video kartları, kalite,
  MP3, kuyruk/klasör, gerçek süreyle bölüm seçimi ve güvenli kapanış.
- A04/A07: yakalama karar penceresi ve eklenti Video/MP3 seçimi; gönderilen
  kalite korunur, yeni video seçiminde 1080p önerilir. İptal kararı bir kez gider.
- A05: gerçek görev/parça/hız geçmişinden ortak TransferContent; bilinmeyen
  boyut ve gözlenmemiş bağlantılar açıkça belirtilir. Odak çekmecesinde kullanılabilir.
- A06: tamamlanma, dosya/klasör eylemleri ve kullanıcı başlatmalı virüs taraması.
- A14: beş araç, korunmuş iptal edilebilir işçiler, gerçek medya süresiyle
  zaman çizelgesi, kaynak dosyayı koruma ve aynı pencerede altyazı seçimi.
- A15/A16: taşınabilir HUD, kaydedilen konum, ölçülmüş grafik ve zamanlayıcı temizliği.
- A17/A19: sürüm bilgisi ve gerçek yayın notları; adlandırılmış kararlar,
  hata çözme eylemleri, teknik ayrıntı ve bildirim tonları.

Yerel doğrulama: 84 birim testi; native bileşenler, ana pencere, canlı aktarım,
12 iptal/kaldırma çevrimi; gerçek FFmpeg kesim/MP3/iptal/kaynak koruma;
gerçek Chromium ve yerel HTTP yakalama; eklenti gerçek dosya SHA-256 eşleşmesi
ve bozuk kopyayı reddetme. Yenileme testinde runtime.reload çağrısı taklittir:
Chrome komut satırı/CDP eklentisini gerçek reload sonrasında devre dışı bırakır.
Bu, gerçek kurulu eklentinin yeniden açıldığı iddiası değildir.

18 native pencere ve 2 tarayıcı görseli: palet, içerik, boyut ve PNG SHA-256
doğrulanır. Araçlar görselinde sol yan panel ve sağ gövde ayrı palet rolleriyle
kontrol edilir. Native Windows çerçevesi ve kaydırma çubukları korunur.
Tüm profiller ve medya yapay/geçicidir; kurulu SDM ve kullanıcı profili kullanılmadı.

Verify bu PR'ın son commit'i için ayrıca kontrol edilir. Paketleme/kurulum/yayın
bu ara aşamada yapılmadı. Kalan kapsam: Ayarlar, Odak ve son uyumluluk denetimi.
