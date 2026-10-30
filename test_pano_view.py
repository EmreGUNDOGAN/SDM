import unittest
from types import SimpleNamespace
from pano_view import current_transfer, transfer_counts
from atlas_view import matches_status, column_preferences, DEFAULT_COLUMNS


class PanoViewTests(unittest.TestCase):
    def test_tile_shadow_is_bounded_and_cached_images_are_isolated(self):
        from ui_surface import pano_tile_surface
        background='#f5f5f7'
        image=pano_tile_surface(200,100,background,'#ffffff')
        self.assertEqual(image.size,(200,100))
        self.assertEqual(image.getpixel((100,50)),(255,255,255))
        self.assertNotEqual(image.getpixel((100,98)),(245,245,247))
        image.putpixel((100,50),(0,0,0))
        self.assertEqual(pano_tile_surface(200,100,background,'#ffffff').getpixel((100,50)),(255,255,255))
        self.assertEqual(pano_tile_surface(1,1,background,'#ffffff').size,(1,1))

    def setUp(self):
        self.tasks={}
        self.app=SimpleNamespace(settings={'language':'tr'},video_tasks={},
            engine=SimpleNamespace(get_task=self.tasks.get))

    def record(self,did,status,**overrides):
        record=dict(id=did,filename=f'test-transfer-{did}.bin',status=status,
            downloaded_bytes=20,filesize=100,category='Diğer',
            date_added='2026-10-30',url='https://example.invalid/item',options_json='{}')
        return dict(record,**overrides)

    def test_live_task_beats_saved_status_and_exposes_following_queue(self):
        queued=self.record(1,'Kuyrukta');active=self.record(2,'Bekliyor')
        self.tasks[2]=SimpleNamespace(status='İndiriliyor',filesize=200,
            segments=[SimpleNamespace(downloaded_bytes=75)],current_speed=1024,eta=3)
        view=current_transfer(self.app,[queued,active])
        self.assertEqual(view['id'],2)
        self.assertEqual(view['status'],'İndiriliyor')
        self.assertEqual(view['progress'],.375)
        self.assertEqual(view['next_name'],queued['filename'])
        self.assertEqual(view['connections'],'—')

    def test_done_and_cancelled_are_not_current(self):
        self.assertIsNone(current_transfer(self.app,[]))
        self.assertIsNone(current_transfer(self.app,[self.record(1,'Tamamlandı'),self.record(2,'İptal Edildi')]))
        self.assertIsNone(current_transfer(self.app,[self.record(1,'Kuyrukta'),self.record(2,'Duraklatıldı')]))

    def test_fastest_active_wins_and_next_is_second_active(self):
        records=[self.record(1,'Kuyrukta'),self.record(2,'Bekliyor'),self.record(3,'Bekliyor')]
        for did,speed in ((2,100),(3,200)):
            self.tasks[did]=SimpleNamespace(status='İndiriliyor',filesize=100,
                segments=[SimpleNamespace(downloaded_bytes=10)],current_speed=speed,eta=2)
        view=current_transfer(self.app,records)
        self.assertEqual(view['id'],3)
        self.assertEqual(view['next_name'],records[1]['filename'])

    def test_summary_uses_live_status_and_distinct_filters(self):
        records=[self.record(1,'Bekliyor'),self.record(2,'Kuyrukta'),
            self.record(3,'Duraklatıldı'),self.record(4,'Tamamlandı'),self.record(5,'Hata')]
        self.tasks[1]=SimpleNamespace(status='İndiriliyor')
        self.assertEqual(transfer_counts(self.app,records),dict(Etkin=1,Kuyrukta=1,Duraklatılanlar=1,Tamamlananlar=1))
        self.assertFalse(matches_status('Duraklatıldı','Etkin'))
        self.assertFalse(matches_status('Tamamlandı','Kuyrukta'))
        self.assertTrue(matches_status('Bekliyor','Kuyrukta'))
        self.assertTrue(matches_status('Duraklatıldı','Devam Edenler'))

    def test_pano_column_defaults_leave_existing_defaults_intact(self):
        self.assertEqual(column_preferences('atlas'),('visible_columns',DEFAULT_COLUMNS))
        self.assertEqual(column_preferences('pano'),('pano_visible_columns',('filename','progress','size','status')))

    def test_column_save_and_apply_keep_other_design_preference(self):
        from gui import MainWindow
        from unittest.mock import Mock,patch
        for design,key,other in (('pano','pano_visible_columns','visible_columns'),('atlas','visible_columns','pano_visible_columns')):
            with self.subTest(design=design):
                settings=dict(visible_columns=['filename','eta'],pano_visible_columns=['filename','progress'])
                original=settings[other][:]
                window=SimpleNamespace(settings=settings,theme_family=design,tree=Mock(),
                    column_vars={'filename':SimpleNamespace(get=lambda:True),'size':SimpleNamespace(get=lambda:True)})
                window.apply_visible_columns=lambda:MainWindow.apply_visible_columns(window)
                with patch('gui.save_settings',return_value=True) as save:
                    MainWindow.save_columns(window)
                save.assert_called_once_with(settings)
                self.assertEqual(settings[key],['filename','size'])
                self.assertEqual(settings[other],original)
                suffix=['actions'] if design=='pano' else []
                window.tree.configure.assert_called_once_with(displaycolumns=['filename','size',*suffix])
                settings[key]=['not-a-column','speed']
                MainWindow.apply_visible_columns(window)
                window.tree.configure.assert_called_with(displaycolumns=['filename','speed',*suffix])

    def test_unknown_total_does_not_invent_progress(self):
        view=current_transfer(self.app,[self.record(1,'İndiriliyor',filesize=0)])
        self.assertEqual(view['progress'],0)
        self.assertEqual(view['total'],'Bilinmiyor')
        self.assertEqual(view['speed'],'—')

    def test_progress_bounds_and_display_language(self):
        for received,expected in ((-4,0),(200,1)):
            view=current_transfer(self.app,[self.record(1,'İndiriliyor',downloaded_bytes=received,filesize=100)])
            self.assertEqual(view['progress'],expected)
        self.app.settings['language']='en'
        view=current_transfer(self.app,[self.record(1,'İndiriliyor',filesize=1536)])
        self.assertIn('.',view['total'])
        self.app.settings['language']='tr'
        self.assertIn(',',current_transfer(self.app,[self.record(1,'İndiriliyor',filesize=1536)])['total'])


if __name__=='__main__':unittest.main()
