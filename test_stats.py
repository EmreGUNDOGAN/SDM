"""Statistics are derived only from synthetic rows; no user database is read."""
import unittest
from datetime import datetime

from stats import summarize, DAYS

NOW = datetime(2026, 10, 30, 15, 0, 0)


def row(status, size, added, completed=None, category='Video', url='https://www.youtube.com/watch?v=x'):
    return dict(status=status, filesize=size, date_added=added, date_completed=completed, category=category, url=url)


ROWS = [
    row('Tamamlandı', 1000, '2026-10-01 10:00:00', '2026-10-30 09:00:00'),            # added long ago, finished today
    row('Tamamlandı', 500, '2026-10-29 10:00:00', '2026-10-29 11:00:00', 'Müzik', 'https://music.youtube.com/watch?v=y'),
    row('Tamamlandı', 300, '2026-10-20 10:00:00', '2026-10-20 10:30:00', 'Arşivler', 'https://github.com/a.zip'),
    row('Tamamlandı', 200, '2026-08-01 10:00:00', '2026-08-01 10:30:00', 'Arşivler', 'https://github.com/b.zip'),  # outside 30 days
    row('Hata', 900, '2026-10-30 08:00:00'),
    row('İptal Edildi', 900, '2026-10-25 08:00:00'),
    row('İndiriliyor', 900, '2026-10-30 08:00:00'),                                  # in progress: counted nowhere
    row('Tamamlandı', 50, 'bozuk tarih'),                                             # unreadable date is skipped
]


class StatsTest(unittest.TestCase):
    def test_periods(self):
        today = summarize(ROWS, 'today', NOW)
        self.assertEqual((today['total'], today['files'], today['done'], today['failed'], today['cancelled']), (1000, 1, 1, 1, 0))
        week = summarize(ROWS, '7', NOW)
        self.assertEqual((week['total'], week['files'], week['cancelled']), (1500, 2, 1))
        month = summarize(ROWS, '30', NOW)
        self.assertEqual((month['total'], month['files']), (1800, 3))
        every = summarize(ROWS, 'all', NOW)
        self.assertEqual((every['total'], every['files'], every['done']), (2000, 4, 4))

    def test_daily_chart_is_last_30_days_of_finished_bytes(self):
        data = summarize(ROWS, 'today', NOW)  # the chart ignores the period
        self.assertEqual(len(data['daily']), DAYS)
        self.assertEqual((data['daily'][-1], data['daily'][-2], data['daily'][-11]), (1000, 500, 300))
        self.assertEqual(sum(data['daily']), 1800)
        self.assertEqual((data['days'][-1].day, data['days'][0].day), (30, 1))

    def test_kinds_and_sites_sorted_by_size(self):
        data = summarize(ROWS, 'all', NOW)
        self.assertEqual(data['kinds'], [('Video', 1000, 1), ('Arşivler', 500, 2), ('Müzik', 500, 1)])  # tie: more files first
        self.assertEqual(data['sites'], [('youtube.com', 1000, 1), ('github.com', 500, 2), ('music.youtube.com', 500, 1)])

    def test_empty_and_bad_period(self):
        empty = summarize([], 'all', NOW)
        self.assertEqual((empty['total'], empty['kinds'], empty['sites'], sum(empty['daily'])), (0, [], [], 0))
        with self.assertRaises(ValueError):summarize([], '90', NOW)


if __name__ == '__main__':
    unittest.main()
