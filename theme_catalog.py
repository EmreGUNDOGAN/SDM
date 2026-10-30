"""Design/color-mode preferences and deterministic legacy settings migration."""
import sys
from ui_tokens import COLOR_MODES, DESIGNS, DESIGN_NAMES, FIXED_MODES, colors

FAMILIES = DESIGNS
THEMES = tuple(f'{design}_{mode}' for design in DESIGNS
               for mode in ((FIXED_MODES[design],) if design in FIXED_MODES else ('light', 'dark')))
LEGACY_THEMES = tuple(f'{family}_{mode}' for family in ('atlas', 'orbit', 'nova')
                      for mode in ('light', 'dark')) + ('light', 'cosmo', 'dark', 'system')


def migrate_settings(settings):
    """Copy settings; explicit new keys win. Never mutate the caller's backup."""
    result = dict(settings)
    old = result.pop('theme', None)
    mode = 'system' if old == 'system' else 'dark' if old in (
        'dark', 'atlas_dark', 'orbit_dark', 'nova_dark') else 'light'
    result['design'] = result.get('design') if result.get('design') in DESIGNS else 'atlas'
    result['color_mode'] = (result.get('color_mode') if result.get('color_mode')
                            in COLOR_MODES else mode)
    return result


def system_color_mode():
    if sys.platform == 'win32':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
                return 'light' if winreg.QueryValueEx(key, 'AppsUseLightTheme')[0] else 'dark'
        except OSError:
            pass
    return 'light'


def effective_mode(settings):
    normalized = migrate_settings(settings)
    if normalized['design'] in FIXED_MODES:return FIXED_MODES[normalized['design']]
    mode = normalized['color_mode']
    return system_color_mode() if mode == 'system' else mode


def theme_key(settings):
    normalized = migrate_settings(settings)
    return f"{normalized['design']}_{effective_mode(normalized)}"


def theme_name(key, language='tr'):
    design, mode = key.rsplit('_', 1)
    suffix = {'light': 'Açık', 'dark': 'Koyu', 'system': 'Sistem'}[mode]
    return f"{DESIGN_NAMES[design]} — {suffix if language == 'tr' else mode.title()}"


def palette(key):
    design, mode = key.rsplit('_', 1)
    if design not in DESIGNS or mode not in ('light', 'dark'):
        raise ValueError(f'Unknown resolved theme: {key}')
    if design in FIXED_MODES and mode!=FIXED_MODES[design]:
        raise ValueError(f'Unsupported color mode for design: {key}')
    p = colors(mode,design)
    # Compatibility roles for old layouts, retained until phase 6.
    p.update(panel=p['card'] if design in FIXED_MODES else p['side'], selected=p['accent_soft'], hover=p['subtle'],
             control=p['card'], disabled_bg=p['subtle'], disabled_text=p['muted'],
             accent_hover=p['accent'], accent_pressed=p['accent_text'], design=design, mode=mode)
    return p
