"""Download statistics from the downloads table; no extra history is stored.

A finished download counts on its completion day, anything else on the day it
was added. Removed rows are gone from the table, so they are not counted.
Speed and duration are session-only and therefore not reported here.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from urllib.parse import urlsplit

PERIODS = {'today': 'Bugün', '7': '7 gün', '30': '30 gün', 'all': 'Tümü'}
DAYS = 30  # the daily chart always shows the last 30 days
DONE, FAILED, CANCELLED = 'Tamamlandı', 'Hata', 'İptal Edildi'


def _when(record):
    stamp = (record.get('status') == DONE and record.get('date_completed')) or record.get('date_added')
    try:return datetime.strptime(str(stamp)[:19], '%Y-%m-%d %H:%M:%S')
    except ValueError:return None


def _site(url):
    host = (urlsplit(str(url or '')).hostname or '').lower()
    return host[4:] if host.startswith('www.') else host


def summarize(records, period='30', now=None):
    """Totals, results, kinds and sites for `period`, plus the last 30 days by day."""
    if period not in PERIODS:raise ValueError('Bilinmeyen dönem')
    now = now or datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = None if period == 'all' else today - timedelta(days=0 if period == 'today' else int(period) - 1)
    results = Counter();kinds = defaultdict(lambda: [0, 0]);sites = defaultdict(lambda: [0, 0])
    daily = [0] * DAYS;total = files = 0
    for record in records:
        when = _when(record)
        if when is None:continue
        status = record.get('status')
        if status == DONE:
            size = max(0, int(record.get('filesize') or 0))
            offset = (today - when.replace(hour=0, minute=0, second=0, microsecond=0)).days
            if 0 <= offset < DAYS:daily[DAYS - 1 - offset] += size
        if start is not None and when < start:continue
        if status in (DONE, FAILED, CANCELLED):results[status] += 1
        if status != DONE:continue
        total += size;files += 1
        kind = kinds[record.get('category') or 'Diğer'];kind[0] += size;kind[1] += 1
        site = sites[_site(record.get('url')) or 'Bilinmeyen'];site[0] += size;site[1] += 1
    order = lambda item: (-item[1][0], -item[1][1], item[0])
    return dict(period=period, total=total, files=files,
                done=results[DONE], failed=results[FAILED], cancelled=results[CANCELLED],
                daily=daily, days=[today - timedelta(days=DAYS - 1 - i) for i in range(DAYS)],
                kinds=[(name, size, count) for name, (size, count) in sorted(kinds.items(), key=order)],
                sites=[(name, size, count) for name, (size, count) in sorted(sites.items(), key=order)][:5])
