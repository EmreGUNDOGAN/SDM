"""Preview reporting must reject missing, stale, blank and damaged images."""
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageColor
from theme_catalog import THEMES,palette
from tools.report_component_previews import validate_previews,validate_alignment
from tools.report_dialog_previews import P06_SOURCES,validate_pano_completion
from tools.report_settings_previews import PANO_SOURCES,PANO_STATES,validate_pano as validate_pano_settings


class PreviewReportTests(unittest.TestCase):
    def test_pano_settings_reject_stale_captures_and_invalid_counter_centres(self):
        import copy,hashlib,json
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);sources={};previews={}
            for name in PANO_SOURCES:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
                sources[name]=hashlib.sha256(b'fixture').hexdigest()
            for state in PANO_STATES:
                image=Image.new('RGB',(760,500),palette('pano_light')['dialog'])
                for x in range(64):image.putpixel((x,20),(x,0,0))
                path=root/f'pano-settings-{state}.png';image.save(path);previews[state]=hashlib.sha256(path.read_bytes()).hexdigest()
            data=dict(sources=sources,previews=previews,control_center_errors=[0,.5,0,.5])
            report=root/'pano-settings-layout.json';report.write_text(json.dumps(data))
            self.assertEqual(len(validate_pano_settings(root,root)),len(PANO_STATES))
            for values in ([0]*3,[0,0,0,1],[0,0,0,float('nan')],[0,0,0,float('inf')]):
                bad=copy.deepcopy(data);bad['control_center_errors']=values;report.write_text(json.dumps(bad))
                with self.assertRaisesRegex(ValueError,'alignment'):validate_pano_settings(root,root)
            report.write_text(json.dumps(data));(root/'queue_ui.py').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'sources'):validate_pano_settings(root,root)
            (root/'queue_ui.py').write_bytes(b'fixture');(root/'pano-settings-0.png').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'PNG'):validate_pano_settings(root,root)

    def test_pano_completion_rejects_misalignment_and_stale_sources_or_pngs(self):
        import copy,hashlib,json
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);sources={};previews={}
            for name in P06_SOURCES:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
                sources[name]=hashlib.sha256(path.read_bytes()).hexdigest()
            for state in ('pano','pano-scanned'):
                image=Image.new('RGB',(560,500),palette('pano_light')['dialog'])
                for x in range(64):image.putpixel((x,20),(x,0,0))
                path=root/f'p06-{state}.png';image.save(path);previews[state]=hashlib.sha256(path.read_bytes()).hexdigest()
            data=dict(sources=sources,previews=previews,stat_width_spread=0,stat_value_y_spread=0,card_edge_delta=0)
            path=root/'p06-layout.json';path.write_text(json.dumps(data))
            rows,_=validate_pano_completion(root,root);self.assertEqual(len(rows),2)
            for key,value in (('stat_width_spread',2),('stat_value_y_spread',1),('card_edge_delta',1),('stat_width_spread',float('nan'))):
                bad=copy.deepcopy(data);bad[key]=value;path.write_text(json.dumps(bad))
                with self.assertRaisesRegex(ValueError,'alignment'):validate_pano_completion(root,root)
            path.write_text(json.dumps(data));(root/'completion_dialog.py').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Stale P06 source'):validate_pano_completion(root,root)
            (root/'completion_dialog.py').write_bytes(b'fixture');(root/'p06-pano.png').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'Stale P06 PNG'):validate_pano_completion(root,root)

    def test_alignment_rejects_missing_measurements_wrong_geometry_and_stale_source(self):
        import hashlib,json,copy
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'alignment.json'
            with self.assertRaises(FileNotFoundError):validate_alignment(path,root)
            sources={}
            for name in ('ui_surface.py','theme_widgets.py','ui_controls.py'):
                (root/name).write_bytes(b'fixture')
                sources[name]=hashlib.sha256(b'fixture').hexdigest()
            metric=dict(center_errors=[.5]*12,baseline_spreads=[0,0],form_x_delta=0,action_y_delta=0,footer_gap=24)
            report=dict(sources=sources,themes={theme:copy.deepcopy(metric) for theme in THEMES})
            path.write_text(json.dumps(report));self.assertEqual(set(validate_alignment(path,root)),set(THEMES))
            for key,value in (('center_errors',[2]*12),('baseline_spreads',[0,1]),('form_x_delta',1),('action_y_delta',1),('footer_gap',23)):
                bad=copy.deepcopy(report);bad['themes']['yorunge_dark'][key]=value;path.write_text(json.dumps(bad))
                with self.assertRaisesRegex(ValueError,'alignment'):validate_alignment(path,root)
            path.write_text(json.dumps(report));(root/'ui_surface.py').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Stale'):validate_alignment(path,root)

    def fixtures(self,root):
        for theme in THEMES:
            p=palette(theme)
            for suffix in ('','-timeline'):
                image=Image.new('RGB',(64,48),p['bg'])
                image.putpixel((4,4),ImageColor.getrgb(p['accent']))
                image.save(root/f'phase1-components-{theme}{suffix}.png')

    def test_complete_palettes_and_views_have_real_byte_digests(self):
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.fixtures(root);rows=validate_previews(root)
            self.assertEqual(len(rows),len(THEMES)*2)
            for name,width,height,digest in rows:
                self.assertEqual((width,height),(64,48))
                self.assertEqual(digest,hashlib.sha256((root/name).read_bytes()).hexdigest())

    def test_missing_and_corrupt_previews_are_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaisesRegex(ValueError,'Missing'):validate_previews(root)
            self.fixtures(root)
            (root/'phase1-components-atlas_dark.png').write_bytes(b'not a PNG')
            with self.assertRaises(OSError):validate_previews(root)

    def test_wrong_palette_and_blank_capture_are_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.fixtures(root)
            Image.new('RGB',(64,48),'white').save(root/'phase1-components-atlas_dark.png')
            with self.assertRaisesRegex(ValueError,'background'):validate_previews(root)
            self.fixtures(root)
            Image.new('RGB',(64,48),'white').save(root/'phase1-components-atlas_light.png')
            with self.assertRaisesRegex(ValueError,'marker'):validate_previews(root)


if __name__=='__main__':unittest.main()
