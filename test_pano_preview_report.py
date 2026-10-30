import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from tools.report_pano_previews import SOURCES,validate_measurements


class PanoReportTests(unittest.TestCase):
    def test_source_drift_and_geometry_regressions_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in SOURCES:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
            data=dict(sources={name:hashlib.sha256(b'fixture').hexdigest() for name in SOURCES},
                count_center_errors=[0,.5,1,1.5],metric_baseline_spread=0,
                wide=dict(viewport=[1440,900],hero=[670,400],list=[1000,350]),
                compact=dict(viewport=[1080,640],hero=[1000,400],list=[1000,350]))
            self.assertIs(validate_measurements(data,root),data)
            for field,value in (('count_center_errors',[0,0,0,2]),('count_center_errors',[0,0,0,float('nan')]),
                    ('count_center_errors',[]),('metric_baseline_spread',4),('metric_baseline_spread',None),
                    ('wide',dict(viewport=[1440,900],hero=[1800,400],list=[1000,350]))):
                bad=copy.deepcopy(data);bad[field]=value
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):validate_measurements(bad,root)
            (root/SOURCES[0]).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Stale'):validate_measurements(data,root)


    def test_dialog_report_rejects_shifted_cards_and_stale_png_sources(self):
        import json
        from PIL import Image
        from theme_catalog import palette
        from tools.report_pano_dialogs import SOURCES,STATES,validate
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in SOURCES:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
            data=dict(sources={name:hashlib.sha256(b'fixture').hexdigest() for name in SOURCES},previews={},save_width_delta=0,quality_y_delta=0,focus_coverage=[.95,.95])
            for state in STATES:
                image=Image.new('RGB',(560,800),palette('pano_light')['dialog'])
                for x in range(64):image.putpixel((x,20),(x,0,0))
                path=root/f'pano-dialog-{state}.png';image.save(path);data['previews'][state]=hashlib.sha256(path.read_bytes()).hexdigest()
            path=root/'pano-dialog-layout.json';path.write_text(json.dumps(data));self.assertEqual(len(validate(root,root)),7)
            for key,value in (('save_width_delta',2),('quality_y_delta',1),('quality_y_delta',None)):
                bad=copy.deepcopy(data);bad[key]=value;path.write_text(json.dumps(bad))
                with self.assertRaisesRegex(ValueError,'alignment'):validate(root,root)
            for value in ([.95,.5],[float('nan'),.95],[]):
                bad=copy.deepcopy(data);bad['focus_coverage']=value;path.write_text(json.dumps(bad))
                with self.assertRaisesRegex(ValueError,'stroke'):validate(root,root)
            path.write_text(json.dumps(data));(root/'batch_dialog.py').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Stale'):validate(root,root)
            (root/'batch_dialog.py').write_bytes(b'fixture');(root/'pano-dialog-batch.png').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'Stale'):validate(root,root)


if __name__=='__main__':unittest.main()
