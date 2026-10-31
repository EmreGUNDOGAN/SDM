# SDM 1.0.1 — Şarkı/albüm seçimi, albümün tek indirme olması ve sayfa taramasında video

- YouTube Music: SDM düğmesinde "Bu şarkı" ve "Albümün tamamı" (karışık listede "Listenin tamamı") ayrı seçenekler olarak gösterilir. Albüm sayfasında tek şarkı için önce şarkıyı çalmak gerekir.
- Albüm veya liste artık indirme listesinde tek satırdır: parçalar sırayla iner, ilerleme tek yüzde ve "Parça 3/12" olarak görünür, tek ayrıntı penceresi ve tek tamamlanma bildirimi açılır. Duraklatıp devam edince kalan parçadan sürer.
- Video ve müzik indirmelerinin geçici çalışma klasörü artık kayıt klasöründe (`.sdm-video-…`) değil, SDM'nin kendi veri klasöründedir ve indirme bitince silinir. 1.0.1'den önce duraklatılmış indirmeler eski klasörlerinden devam eder.
- Sayfa tarama: oynatıcıdaki videolar (sayfanın kendisi olarak), `<video>`/`<audio>` kaynakları ve sayfaya gömülü YouTube, Vimeo ve Dailymotion oynatıcıları da Video/Ses olarak listelenir.

Kurulumdan sonra tarayıcının eklentiler sayfasında SDM eklentisini bir kez Yeniden yükle; açık sayfaları yenile.
