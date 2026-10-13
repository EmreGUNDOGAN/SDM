"""Six persisted design variants; legacy settings migrate to Atlas."""
FAMILIES=('atlas','orbit','nova')
THEMES=tuple(f'{family}_{mode}' for family in FAMILIES for mode in ('light','dark'))
def theme_key(settings):
    value=settings.get('theme','atlas_light')
    return value if value in THEMES else 'atlas_dark' if value=='dark' else 'atlas_light'
def theme_name(key,language='tr'):
    family,mode=key.split('_')
    suffix=('Açık Tema' if mode=='light' else 'Koyu Tema') if language=='tr' else mode.title()
    return f'{family.title()} — {suffix}'
def _palette(key):
    family,mode=key.split('_');dark=mode=='dark'
    if family=='nova':
        return dict(bg='#222529' if dark else '#fffdfa',panel='#2b2e32' if dark else '#f7f5f1',text='#f6f4ef' if dark else '#202429',muted='#b8b6b2' if dark else '#71716c',selected='#49352d' if dark else '#fff0e5',line='#414447' if dark else '#e7e1d9',accent='#f26b2f',hover='#373b40' if dark else '#eeeae4')
    return dict(bg=('#17212b' if family=='orbit' else '#111c2b') if dark else '#ffffff',panel=('#202c37' if family=='orbit' else '#182738') if dark else '#f7f9fc',text='#edf3fa' if dark else '#142331',muted='#adbbcd' if dark else '#637287',selected='#183e59' if dark else '#e3f2ff',line='#344456' if dark else '#e0e6ee',accent='#05c3ed' if dark else '#087dff',hover='#2a3b4d' if dark else '#edf3f9')

def palette(key):
    p=_palette(key);dark=key.endswith('dark');nova=key.startswith('nova')
    p.update(control=p['panel'] if dark else '#ffffff',disabled_bg='#303844' if dark else '#e6eaf0',disabled_text='#77859a' if dark else '#9aa7b8',accent_hover='#ff7d44' if nova else '#25ceee' if dark else '#2090ff',accent_pressed='#d85724' if nova else '#049bbb' if dark else '#0064db')
    return p
