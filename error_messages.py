def explain_error(error):
    value = str(error).lower()
    if any(word in value for word in ('disk', 'space', 'winerror 112', 'errno 28')):
        return ('Disk alanı yetersiz', 'Kayıt diskinde yer açın veya başka bir klasör seçin.', 'Başka klasöre indir')
    if '403' in value or 'forbidden' in value:
        return ('Sunucu indirmeye izin vermedi (403)', 'Bu hata bağlantının süresinin dolduğunu tek başına göstermez. Video bağlantısını yenileyerek tekrar deneyin; site oturum veya erişim doğrulaması istiyor olabilir.', 'Tekrar dene')
    if '401' in value:
        return ('Oturum gerekiyor (401)', 'Kaynak site bu dosya için oturum açılmasını istiyor. Kaynak sayfayı tarayıcıda açın.', 'Kaynak sayfayı aç')
    if any(word in value for word in ('410', 'expired', 'oturum')):
        return ('Bağlantı veya erişim süresi doldu', 'Kaynak sayfadan yeni bir indirme bağlantısı alın.', 'Kaynak sayfayı aç')
    if any(word in value for word in ('range', '416')):
        return ('Sunucu devam etmeyi desteklemiyor', 'Bu indirmeyi sıfırdan başlatmayı deneyin.', 'Sıfırdan indir')
    if any(word in value for word in ('timed out', 'timeout', 'connection', 'bağlan', 'resolve', 'network')):
        return ('Bağlantı tamamlanamadı', 'İnternet bağlantısını kontrol edin ve yeniden deneyin.', 'Tekrar dene')
    return ('İndirme tamamlanamadı', 'Yeniden deneyin veya kaynak bağlantının çalıştığını kontrol edin.', 'Tekrar dene')
