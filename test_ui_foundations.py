"""Migration/persistence tests; every file operation is in a temporary profile."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import utils
from preferences import validate_settings,import_settings,export_settings
from theme_catalog import migrate_settings,theme_key,palette,system_color_mode
from ui_tokens import PALETTES,DESIGNS,RADII,dimensions,status_colors
from ui_surface import surface,icon,NEW_ICON_NAMES


class MigrationTests(unittest.TestCase):
    def test_every_legacy_key_and_default_is_idempotent(self):
        cases={None:'light','unknown':'light','light':'light','cosmo':'light',
               'dark':'dark','system':'system'}
        cases.update({f'{family}_{mode}':mode for family in ('atlas','orbit','nova') for mode in ('light','dark')})
        for old,mode in cases.items():
            with self.subTest(old=old):
                original={'language':'en','download_dir':'fake-downloads','queues':[]}
                if old is not None:original['theme']=old
                result=migrate_settings(original)
                self.assertEqual((result['design'],result['color_mode']),('atlas',mode))
                self.assertNotIn('theme',result);self.assertEqual(result['language'],'en')
                self.assertEqual(result,migrate_settings(result))
                self.assertEqual(original.get('theme'),old)

    def test_new_explicit_keys_win_over_stale_theme(self):
        for design in DESIGNS:
            values=migrate_settings(dict(theme='nova_dark',design=design,color_mode='system'))
            self.assertEqual((values['design'],values['color_mode']),(design,'system'))
            for mode in ('light','dark'):
                with patch('theme_catalog.system_color_mode',return_value=mode):
                    self.assertEqual(theme_key(values),f'{design}_{mode}')
                    self.assertEqual(values['color_mode'],'system')

    def test_windows_system_read_and_missing_registry_fallback(self):
        import sys
        if sys.platform!='win32':
            self.assertEqual(system_color_mode(),'light');return
        with patch('winreg.OpenKey') as opened,patch('winreg.QueryValueEx',return_value=(0,4)):
            self.assertEqual(system_color_mode(),'dark')
            self.assertIn('Personalize',opened.call_args.args[1])
        with patch('winreg.OpenKey',side_effect=OSError):self.assertEqual(system_color_mode(),'light')

    def test_startup_migrates_before_defaults_and_only_writes_once(self):
        for old in ('nova_dark','orbit_light','system'):
            with self.subTest(old=old),tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'config.json';path.write_text(json.dumps({'theme':old,'language':'en'}))
                with patch.object(utils,'CONFIG_DIR',Path(folder)),patch.object(utils,'CONFIG_FILE',path):
                    first=utils.load_settings();saved=path.read_bytes()
                    self.assertEqual(first['color_mode'],migrate_settings({'theme':old})['color_mode'])
                    with patch.object(utils,'save_settings',wraps=utils.save_settings) as save:
                        self.assertEqual(utils.load_settings(),first);save.assert_not_called()
                    self.assertEqual(path.read_bytes(),saved);self.assertNotIn('theme',json.loads(saved))

    def test_backup_migration_validation_and_secret_exclusion(self):
        for old in ('atlas_light','atlas_dark','orbit_light','orbit_dark','nova_light','nova_dark','light','cosmo','dark','system'):
            result=validate_settings({'theme':old,'language':'en'})
            self.assertEqual(result,migrate_settings({'theme':old,'language':'en'}))
        for bad in ({'design':'orbit'},{'color_mode':'night'},{'theme':'bad'},
                    {'design':[]},{'color_mode':None}):
            with self.subTest(bad=bad),self.assertRaises(ValueError):validate_settings(bad)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'backup.json'
            export_settings(path,dict(utils.DEFAULT_SETTINGS,design='odak',color_mode='system',token='fake-credential'))
            self.assertNotIn('fake-credential',path.read_text())
            self.assertEqual(import_settings(path)['design'],'odak')
            path.write_text(json.dumps({'format':'sdm-settings-v1','settings':{'theme':'nova_dark'}}))
            self.assertEqual(import_settings(path),{'design':'atlas','color_mode':'dark'})

    def test_failed_migration_save_is_reported_without_losing_preferences(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'config.json';original=b'{"theme":"nova_dark","language":"en"}'
            path.write_bytes(original)
            with patch.object(utils,'CONFIG_DIR',Path(folder)),patch.object(utils,'CONFIG_FILE',path),patch.object(utils,'save_settings',return_value=False):
                with self.assertRaises(OSError):utils.load_settings()
            self.assertEqual(path.read_bytes(),original)


class RenderingTokenTests(unittest.TestCase):
    def test_role_parity_copy_isolation_and_design_dimensions(self):
        self.assertEqual(set(PALETTES['light']),set(PALETTES['dark']))
        p=palette('atlas_light');p['accent']='changed'
        self.assertEqual(palette('atlas_light')['accent'],'#2156d9')
        self.assertNotEqual(RADII['atlas']['button'],RADII['odak']['button'])
        self.assertEqual(dimensions('odak')['settings_nav'],232)
        for mode in ('light','dark'):
            self.assertEqual(status_colors('Tamamlandı',mode)[1],PALETTES[mode]['success_bg'])
            self.assertEqual(status_colors('İptal Edildi',mode)[1],PALETTES[mode]['danger_bg'])

    def test_cached_images_are_not_shared_mutable_buffers(self):
        first=surface(30,20,'#ffffff','#2156d9');expected=first.getpixel((15,10))
        first.putpixel((15,10),(0,0,0))
        self.assertEqual(surface(30,20,'#ffffff','#2156d9').getpixel((15,10)),expected)
        for name in NEW_ICON_NAMES:
            with self.subTest(name=name):
                glyph=icon(name,24,'#2156d9');self.assertIsNotNone(glyph.getbbox())
                self.assertNotEqual(glyph.tobytes(),icon('clock',24,'#2156d9').tobytes())


if __name__=='__main__':unittest.main()
