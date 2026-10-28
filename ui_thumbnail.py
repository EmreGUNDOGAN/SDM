"""Bounded public image fetches; live UI and user files are never read by workers."""
import io
import queue
import threading
import weakref
import tkinter as tk
from PIL import Image,ImageOps
from ui_surface import surface,icon,photo

_jobs=queue.Queue(maxsize=128)
_started=False
_lock=threading.Lock()


def fetch_image(url):
    import requests
    from urllib.parse import urljoin
    from browser_files import validate_file_url
    for _ in range(6):
        url=validate_file_url(url)
        with requests.get(url,stream=True,timeout=8,allow_redirects=False) as response:
            if response.is_redirect:url=urljoin(url,response.headers['Location']);continue
            response.raise_for_status()
            data=bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data)>2*1024*1024:raise ValueError('Thumbnail is too large')
            with Image.open(io.BytesIO(data)) as image:
                if image.width*image.height>20000000:raise ValueError('Thumbnail dimensions are too large')
                image.load();return ImageOps.contain(image.convert('RGB'),(640,360)).copy()
    raise ValueError('Too many thumbnail redirects')


def _worker():
    while True:
        url,reference,app=_jobs.get();widget=reference()
        if widget is None or widget._closed:continue
        try:image=fetch_image(url)
        except Exception:continue
        def done(ref=reference,data=image,source=url):
            item=ref()
            if item is not None and not item._closed and item.source==source:item.image=data;item.draw()
        app.post_ui(done)


class Thumbnail(tk.Canvas):
    def __init__(self,master,app,palette,width=96,height=54,source=None):
        super().__init__(master,width=width,height=height,bg=master.cget('bg'),highlightthickness=0)
        self.app=app;self.p=palette;self.image=None;self.source=None;self._closed=False
        self.bind('<Destroy>',self.dispose);self.bind('<Configure>',lambda e:self.draw());self.set_source(source);self.draw()

    def set_source(self,source):
        if not source or source==self.source:return
        self.source=source
        global _started
        with _lock:
            if not _started:
                for _ in range(3):threading.Thread(target=_worker,daemon=True).start()
                _started=True
        try:_jobs.put_nowait((source,weakref.ref(self),self.app))
        except queue.Full:pass

    def draw(self):
        if self._closed:return
        w=self.winfo_width() if self.winfo_width()>1 else int(self.cget('width'));h=self.winfo_height() if self.winfo_height()>1 else int(self.cget('height'))
        image=surface(w,h,self.cget('bg'),self.p['hud'],radius=8)
        if self.image:image=ImageOps.fit(self.image,(w,h),method=Image.Resampling.LANCZOS)
        else:
            glyph=icon('play-circle',28,self.p['toast_text']);image.paste(glyph,((w-28)//2,(h-28)//2),glyph)
        self._image=photo(image,self);self.delete('all');self.create_image(0,0,image=self._image,anchor='nw')

    def dispose(self,event):
        if event.widget is self:self._closed=True
