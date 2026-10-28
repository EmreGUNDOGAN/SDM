"""Presentation regressions: action safety, unknown sizes, actual connections."""
import unittest
from types import SimpleNamespace
from atlas_view import available_actions,domain,file_kind,matches_status,observed_parts,subtitle


class AtlasPresentationTests(unittest.TestCase):
    def test_finished_file_actions_and_empty_selection(self):
        self.assertFalse(any(available_actions(()).values()))
        actions=available_actions(('Tamamlandı',))
        self.assertTrue(actions['open'] and actions['verify'] and actions['remove'])
        self.assertFalse(actions['resume'] or actions['pause'] or actions['cancel'] or actions['queue'])

    def test_active_and_mixed_actions_preserve_single_file_requirements(self):
        active=available_actions(('İndiriliyor',))
        self.assertTrue(active['pause'] and active['cancel'])
        self.assertFalse(active['resume'] or active['verify'] or active['open'])
        mixed=available_actions(('İndiriliyor','Duraklatıldı','Tamamlandı'))
        self.assertTrue(mixed['resume'] and mixed['pause'] and mixed['cancel'] and mixed['queue'])
        self.assertFalse(mixed['open'] or mixed['folder'] or mixed['details'] or mixed['verify'])

    def test_error_filter_and_previous_unfinished_semantics(self):
        self.assertTrue(matches_status('Hata','Hatalı'))
        self.assertTrue(matches_status('İptal Edildi','Hatalı'))
        self.assertFalse(matches_status('Duraklatıldı','Hatalı'))
        self.assertTrue(matches_status('Kuyrukta','Devam Edenler'))
        self.assertFalse(matches_status('Tamamlandı','Devam Edenler'))
        self.assertTrue(matches_status('Tamamlandı','Tamamlananlar'))

    def test_domain_never_displays_url_credentials_or_query(self):
        record=dict(url='https://name:password@example.invalid/file?secret=value',category='Video',options_json='{"height":720}')
        self.assertEqual(domain(record),'example.invalid')
        self.assertEqual(subtitle(record),'Video · example.invalid · 720p')
        self.assertEqual(domain(dict(url='http://[bad')),'')
        self.assertEqual(subtitle(dict(category='Diğer',options_json='bad')),'Diğer')

    def test_disk_tile_and_category_tile(self):
        self.assertEqual(file_kind(dict(filename='synthetic.ISO',category='Arşivler')),'disk')
        self.assertEqual(file_kind(dict(filename='synthetic.mkv',category='Video')),'video')
        self.assertEqual(file_kind({}),'other')

    def test_configured_connections_are_not_reported_as_observed(self):
        record=dict(id=1,num_connections=32)
        app=SimpleNamespace(video_tasks={},engine=SimpleNamespace(get_task=lambda did:None))
        self.assertEqual(observed_parts(app,record),((),None))
        app.engine.get_task=lambda did:SimpleNamespace(transfer_snapshot=lambda:dict(rows=[],active_count=0))
        self.assertEqual(observed_parts(app,record),((),None))
        rows=[dict(index=1,received=10,total=20,active=True)]
        app.engine.get_task=lambda did:SimpleNamespace(transfer_snapshot=lambda:dict(rows=rows,active_count=1))
        actual,active=observed_parts(app,record)
        self.assertEqual(actual,tuple(rows));self.assertEqual(active,1)

    def test_video_unmeasured_stream_stays_unknown(self):
        app=SimpleNamespace(video_tasks={1:SimpleNamespace(transfer_details=SimpleNamespace(snapshot=lambda:[dict(rows=[],active_count=None)]))})
        self.assertEqual(observed_parts(app,dict(id=1)),((),None))


if __name__=='__main__':unittest.main()
