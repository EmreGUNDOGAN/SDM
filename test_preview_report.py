"""Preview reporting must reject missing, stale, blank and damaged images."""
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageColor
from theme_catalog import THEMES,palette
from tools.report_component_previews import validate_previews


class PreviewReportTests(unittest.TestCase):
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
            self.assertEqual(len(rows),8)
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
