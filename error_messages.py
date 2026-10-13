def explain_error(error):
    value = str(error).lower()
    if any(word in value for word in ('disk', 'space', 'winerror 112', 'errno 28')):
        return ('Disk alanı yetersiz', 'Kayıt diskinde yer açın veya başka bir klasör seçin.', 'Başka klasöre indir')
    if any(word in value for word in ('403', '401', '410', 'expired', 'oturum')):
        return ('Bağlantı veya erişim süresi doldu', 'Kaynak sayfadan yeni bir indirme bağlantısı alın.', 'Kaynak sayfayı aç')
    if any(word in value for word in ('range', '416')):
        return ('Sunucu devam etmeyi desteklemiyor', 'Bu indirmeyi sıfırdan başlatmayı deneyin.', 'Sıfırdan indir')
    if any(word in value for word in ('timed out', 'timeout', 'connection', 'bağlan', 'resolve', 'network')):
        return ('Bağlantı tamamlanamadı', 'İnternet bağlantısını kontrol edin ve yeniden deneyin.', 'Tekrar dene')
    return ('İndirme tamamlanamadı', 'Yeniden deneyin veya kaynak bağlantının çalıştığını kontrol edin.', 'Tekrar dene')
