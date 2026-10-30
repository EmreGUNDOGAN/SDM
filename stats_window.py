"""İstatistik: approved four-design board (canvas page "İ · İstatistik")."""
import tkinter as tk
from PIL import Image, ImageDraw
from atlas_view import CATEGORY_TILES, number
from stats import PERIODS, summarize
from ui_controls import SegmentedControl
from ui_dialog import AppWindow, AutoCard, label
from ui_indicators import Indicator, Summary
from ui_surface import TextLabel, text_on, font
from ui_tokens import SURFACE_SCALE, file_tile_colors
from utils import format_bytes

MONTHS = ('Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara')


def day_text(day):
    return f'{day.day} {MONTHS[day.month - 1]}'


class DailyBars(Indicator):
    """Bytes per day as bars; the y axis shows the peak, half of it and zero."""
    def __init__(self, master, palette, formatter, **kwargs):
        self.values = ();self.days = ();self.formatter = formatter
        super().__init__(master, palette, height=kwargs.pop('height', 200), **kwargs)

    def set(self, values, days):
        if (tuple(values), tuple(days)) != (self.values, self.days):
            self.values, self.days = tuple(values), tuple(days);self.draw()

    def draw(self):
        w, h = self.size();s = SURFACE_SCALE;p = self.p
        image = Image.new('RGB', (w * s, h * s), self.cget('bg'));d = ImageDraw.Draw(image)
        peak = max(self.values, default=0)
        ticks = [self.formatter(format_bytes(value)) if value else '0' for value in (peak, peak / 2, 0)]
        # The axis is as wide as its widest label, so '3,00 GB' is never clipped.
        left = 12 + max(font(11).getlength(text) for text in ticks)
        top, bottom, right = 8, 22, w - 4
        base = h - bottom;span = max(1, base - top)
        for y in (top, top + span / 2, base):d.line((left * s, y * s, right * s, y * s), fill=p['line_soft'], width=s)
        if self.values and peak:
            step = (right - left) / len(self.values);gap = max(1, step * .22)
            for i, value in enumerate(self.values):
                if value <= 0:continue
                x0 = left + i * step + gap / 2;top_y = base - value / peak * span
                d.rectangle((x0 * s, top_y * s, (x0 + step - gap) * s, base * s), fill=p['accent'])
        image = image.resize((w, h), Image.Resampling.LANCZOS)
        for y, text in zip((top, top + span / 2, base), ticks):
            text_on(image, (left - 8, y), text, 11, fill=p['muted'], anchor='rm')
        if self.days:
            step = (right - left) / len(self.days)
            for i in (0, 7, 14, 21):text_on(image, (left + i * step, h - 14), day_text(self.days[i]), 11, fill=p['muted'])
            text_on(image, (right, h - 14), 'Bugün', 11, fill=p['muted'], anchor='ra')
        self.present(image)


class ShareBar(Indicator):
    """One stacked bar: (size, colour) parts in order."""
    def __init__(self, master, palette, **kwargs):
        self.parts = ()
        super().__init__(master, palette, height=10, **kwargs)

    def set(self, parts):
        if tuple(parts) != self.parts:self.parts = tuple(parts);self.draw()

    def draw(self):
        w, h = self.size();s = SURFACE_SCALE
        image = Image.new('RGB', (w * s, h * s), self.cget('bg'));d = ImageDraw.Draw(image)
        total = sum(size for size, _ in self.parts);x = 0.0
        if not total:d.rectangle((0, 0, w * s, h * s), fill=self.p['subtle'])
        for size, color in self.parts:
            width = size / total * w * s if total else 0
            # A one-scale-pixel gap separates parts; slivers narrower than it are drawn without one.
            if width >= 1:d.rectangle((x, 0, x + max(width - s, 1), h * s), fill=color)
            x += width
        self.present(image.resize((w, h), Image.Resampling.LANCZOS))


class StatsWindow(AppWindow):
    def __init__(self, parent):
        super().__init__(parent, 'İstatistik', 960, 720, 'Tamamlanan indirmelerden')
        self.period = tk.StringVar(self, '30')
        line = tk.Frame(self.header, bg=self.p['dialog']);line.pack(fill='x', pady=(6, 0))
        self.description_label.pack_forget();self.description_label.pack(in_=line, side='left');tk.Misc.tkraise(self.description_label, line)
        SegmentedControl(self.header, PERIODS, self.period, command=self.refresh, palette=self.p).pack(in_=line, side='right')
        cards = tk.Frame(self.body, bg=self.p['dialog']);cards.pack(fill='x', padx=24, pady=(0, 16))
        self.values = {}
        for key, title in (('total', 'İndirilen veri'), ('files', 'Dosya'), ('done', 'Tamamlanan'), ('failed', 'Hatalı / iptal')):
            self.values[key] = tk.StringVar(self, '—')
            Summary(cards, title, self.values[key], self.p).pack(side='left', fill='x', expand=True, padx=(0 if key == 'total' else 8, 0))
        chart = AutoCard(self.body, self.p, padding=14)
        head = tk.Frame(chart.content, bg=self.p['card']);head.pack(fill='x', pady=(0, 8))
        label(head, 'Günlük indirme', palette=self.p, weight='SemiBold').pack(side='left')
        self.peak_text = tk.StringVar(self, '');label(head, variable=self.peak_text, palette=self.p, size=12, muted=True).pack(side='left', padx=10)
        self.bars = DailyBars(chart.content, self.p, lambda text: number(parent, text), width=880, height=200);self.bars.pack(fill='x')
        lower = tk.Frame(self.body, bg=self.p['dialog']);lower.pack(fill='x', padx=24, pady=(0, 16))
        lower.columnconfigure((0, 1), weight=1, uniform='half')
        self.kind_box = self.box(lower, 'Türlere göre', 0)
        self.share = ShareBar(self.kind_box, self.p, width=400);self.share.pack(fill='x', pady=(0, 6))
        self.kind_rows = tk.Frame(self.kind_box, bg=self.p['card']);self.kind_rows.pack(fill='x')
        self.site_rows = self.box(lower, 'En çok indirilen siteler', 1)
        label(self.actionbar, 'Listeden kaldırılan indirmeler sayılmaz · hız ve süre kalıcı kaydedilmez', palette=self.p, size=12, muted=True).pack(side='left')
        self.refresh()

    def box(self, parent, title, column):
        # The shared card keeps each design's corners and border; it lays out in a grid here.
        cell = tk.Frame(parent, bg=self.p['dialog']);cell.grid(row=0, column=column, sticky='new', padx=(0, 8) if column == 0 else (8, 0))
        card = AutoCard(cell, self.p, padding=14);card.pack_configure(padx=0, pady=0)
        label(card.content, title, palette=self.p, weight='SemiBold').pack(anchor='w', pady=(0, 8))
        return card.content

    def row(self, parent, cells, color=None):
        line = tk.Frame(parent, bg=self.p['card']);line.pack(fill='x', pady=3)
        if color:tk.Frame(line, bg=color, width=10, height=10).pack(side='left', padx=(0, 8))
        for index, (text, muted) in enumerate(cells):
            TextLabel(line, text, size=13, fg=self.p['muted'] if muted else self.p['text'], max_width=230 if index == 0 else None).pack(side='left' if index == 0 else 'right', padx=(0 if index == 0 else 12, 0))

    def refresh(self):
        app = self.parent;data = summarize(app.db.get_all_downloads(), self.period.get())
        size = lambda value: number(app, format_bytes(value))
        finished = data['done'] + data['failed'] + data['cancelled']
        self.values['total'].set(size(data['total']));self.values['files'].set(str(data['files']))
        self.values['done'].set(f"{data['done']}" + (f" · %{round(data['done'] / finished * 100)}" if finished else ''))
        self.values['failed'].set(f"{data['failed']} / {data['cancelled']}")
        self.bars.set(data['daily'], data['days'])
        peak = max(data['daily'], default=0)
        self.peak_text.set(f"en yoğun gün {size(peak)} · {day_text(data['days'][data['daily'].index(peak)])}" if peak else 'Son 30 günde tamamlanan indirme yok')
        mode = getattr(app, 'ui_theme', 'light');design = self.p.get('design', 'atlas')
        color = lambda name: file_tile_colors(CATEGORY_TILES.get(name, ('', 'other'))[1], mode, design)[1]
        total = sum(value for _, value, _ in data['kinds'])
        self.share.set([(value, color(name)) for name, value, _ in data['kinds']])
        for frame in (self.kind_rows, self.site_rows):
            for child in frame.winfo_children()[(0 if frame is self.kind_rows else 1):]:child.destroy()
        for name, value, count in data['kinds']:
            self.row(self.kind_rows, ((name, False), (f'%{round(value / total * 100)}' if total else '—', True), (size(value), False)), color(name))
        for site, value, count in data['sites']:
            self.row(self.site_rows, ((site, False), (size(value), False), (f'{count} dosya', True)))
        if not data['kinds']:label(self.kind_rows, 'Bu dönemde tamamlanan indirme yok', palette=self.p, size=12, muted=True).pack(anchor='w')
        if not data['sites']:label(self.site_rows, 'Bu dönemde tamamlanan indirme yok', palette=self.p, size=12, muted=True).pack(anchor='w')
