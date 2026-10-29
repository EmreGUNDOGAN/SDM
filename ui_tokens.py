"""Approved tokens in logical px; Windows scaling belongs to Tk, never multiply twice."""
from types import MappingProxyType

DESIGNS = ('atlas', 'odak')
COLOR_MODES = ('light', 'dark', 'system')
DESIGN_NAMES = MappingProxyType({'atlas': 'Atlas Pro', 'odak': 'Odak Akışı'})
SPACING = (2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 28, 32)
FONT_FAMILY = 'Inter'
MONO_FAMILY = 'Consolas'
SURFACE_SCALE = 3
FOCUS_WIDTH = 2
FOCUS_GAP = 2
DISABLED_OPACITY = 0.55
TOAST_DURATION = 4000
TOAST_ACTION_DURATION = 8000
TOAST_LIMIT = 3
DRAWER_DURATION = 150

# role             light     dark
_COLOR_ROWS = """
bg                  ffffff    0e1116
side                f6f7f9    0b0d11
card                ffffff    161a21
dialog              ffffff    13171d
footer              fbfcfd    10141a
canvas              f3f5f8    0b0d11
line                e5e8ec    262c36
line_soft           eef0f3    1f242c
input_border        d9dee5    2f3743
subtle              f1f3f6    1d222b
track               e9edf2    262c36
text                111827    e8ecf2
text_2              1f2937    c5ccd6
muted               5b6472    9aa4b2
accent              2156d9    3ea6ff
on_accent           ffffff    0b1a2b
accent_soft         eef3fe    16283a
accent_nav          e4ebfb    1d2633
accent_text         1a44ad    7cc2ff
success             16a34a    3fcf8e
success_bg          e7f6ec    143a2a
success_fg          166534    3fcf8e
warning             d68a1a    f2b84b
warning_bg          fdf3e1    3a2e14
warning_fg          8a4b08    f2b84b
danger              d92d20    ff6b6b
danger_bg           fdecec    3a1d1f
danger_fg           b42318    ff8a8a
danger_solid        c4321f    ff6b6b
on_danger           ffffff    2a0b0b
info_bg             e8effd    16283a
info_fg             1d4ed8    7cc2ff
queued_bg           eef1f5    1d222b
queued_fg           475569    8b95a5
queued_bar          94a3b8    8b95a5
toast               111827    262d38
toast_text          f3f4f6    f3f4f6
toast_muted         aab3c2    b4bcc8
hud                 111827    111827
hud_accent          5b8cff    5b8cff
selected_card       eef3fe    18212d
selected_card_border 2156d9    2b4a6b
segment_selected    ffffff    262d38
"""
_rows = [row.split() for row in _COLOR_ROWS.splitlines() if row.strip()]
PALETTES = MappingProxyType({
    mode: MappingProxyType({row[0]: '#' + row[index] for row in _rows})
    for mode, index in (('light', 1), ('dark', 2))
})
FILE_TILES = MappingProxyType({
    'disk': (('#eef0fb', '#3b3f99'), ('#23264a', '#a9adff')),
    'video': (('#fdeeee', '#a3292b'), ('#3a1e22', '#ff9a9e')),
    'program': (('#eaf2fb', '#1e4f8a'), ('#1b2c42', '#8cc4ff')),
    'document': (('#fdf0ea', '#a1401c'), ('#3a2519', '#ffb08a')),
    'audio': (('#f1ecfb', '#5b3aa0'), ('#2b2142', '#c7a8ff')),
    'archive': (('#f3f1e8', '#6b5a1c'), ('#33301c', '#e6d38a')),
    'image': (('#e9f6f0', '#1c6b47'), ('#143a2a', '#7fe0b0')),
    'other': (('#eef1f5', '#475569'), ('#1d222b', '#c5ccd6')),
})
TYPOGRAPHY = MappingProxyType({
    'display': (30, 'Bold'), 'page_title': (20, 'Bold'), 'dialog_title': (18, 'Bold'),
    'item_title': (16, 'SemiBold'), 'section': (14, 'Bold'), 'body': (13, 'Regular'),
    'body_strong': (13, 'SemiBold'), 'small': (12, 'Regular'), 'caption': (11, 'Medium'),
    'mono': (13, 'Regular'),
})
SIZES = MappingProxyType(dict(
    window_min_width=1080, window_min_height=640, sidebar=232, icon_rail=68,
    rail_button=44, settings_nav=200, detail_panel=320, detail_drawer=460,
    table_header=38, table_row=54, button=38, toolbar_button=36, small_button=30,
    icon_button=34, icon=16, dropdown_icon=12, input=40, menu_row=34, menu_padding=6,
    menu_width=260, status_bar=40, switch_width=36, switch_height=20, checkbox=16,
    chip=26, badge=24, file_tile=34, progress=6, detail_progress=8, ring=128,
    ring_stroke=10, timeline=24, timeline_handle=10, hud=340, content_padding=24))
RADII = MappingProxyType({
    'atlas': MappingProxyType(dict(button=8, input=8, card=12, dialog=14, menu=12, tile=8)),
    'odak': MappingProxyType(dict(button=10, input=10, card=16, dialog=16, menu=12, tile=10)),
})

# Atlas workspace geometry, shared by the layout, renderer and native checks.
ATLAS = MappingProxyType(dict(header=68,toolbar=56,sidebar_padding=14,
    sidebar_top=20,nav_row=34,nav_gap=2,brand=30,brand_gap=10,group_gap=18,
    side_footer=124,header_gap=12,search_width=280,capture_width=176,
    detail_padding=20,detail_tile=44,detail_gap=18,selection_mark=3,
    cell_padding=12,file_padding=24,file_text_offset=70,row_title_baseline=22,
    row_subtitle_baseline=41,toolbar_gap=8,toolbar_resume=90,toolbar_pause=100,
    toolbar_cancel=80,toolbar_remove=100,toolbar_folder=122,toolbar_queue=92,
    toolbar_limit=158,empty_width=460,empty_icon=64,detail_font=14,
    footer_sparkline=60,footer_gap=16,disk_refresh_seconds=30,compact_workspace=880,
    compact_search=220,compact_title=160,wide_title=280))


def dimensions(design='atlas'):
    if design not in DESIGNS:
        raise ValueError('Unknown design')
    result = dict(SIZES)
    if design == 'odak':
        result.update(settings_nav=232, ring=112, ring_stroke=9, progress=4, content_padding=32)
    return result


def colors(mode='light'):
    return dict(PALETTES[mode])


def status_colors(status, mode='light'):
    p = PALETTES[mode]
    role = ('success' if status == 'Tamamlandı' else
            'warning' if status == 'Duraklatıldı' else
            'queued' if status in ('Kuyrukta', 'Bekliyor') else
            'info' if status in ('İndiriliyor', 'Birleştiriliyor', 'Dönüştürülüyor') else 'danger')
    bar = p['accent'] if role == 'info' else p['queued_bar'] if role == 'queued' else p[role]
    return bar, p[f'{role}_bg'], p[f'{role}_fg']


def file_tile_colors(kind, mode='light'):
    return FILE_TILES.get(kind, FILE_TILES['other'])[mode == 'dark']
