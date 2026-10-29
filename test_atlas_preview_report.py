import tempfile
from pathlib import Path
import unittest
from PIL import Image
from tools.report_atlas_previews import validate_previews


class AtlasPreviewReportTests(unittest.TestCase):
    def test_missing_preview_is_required(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'Missing Atlas preview'):validate_previews(Path(folder))

    def test_corrupt_png_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'phase2-atlas-light-main.png';path.write_bytes(b'not a PNG')
            with self.assertRaises(OSError):validate_previews(Path(folder))

    def test_blank_and_wrong_palette_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'phase2-atlas-light-main.png'
            image=Image.new('RGB',(1080,640),'white');image.save(path)
            with self.assertRaisesRegex(ValueError,'palette'):validate_previews(root)
            image.paste('#f6f7f9',(0,0,232,640));image.save(path)
            with self.assertRaisesRegex(ValueError,'Blank/incomplete'):validate_previews(root)


if __name__=='__main__':unittest.main()
