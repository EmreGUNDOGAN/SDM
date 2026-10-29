"""B03 live drawer; the same TransferContent used by Atlas's A05 window."""
import tkinter as tk
from ui_dialog import ScrollBody,label,action
from download_window import TransferContent
from theme_widgets import Button


class TransferDrawer(tk.Frame):
    def __init__(self,workspace,did):
        self.workspace=workspace;self.parent=workspace.app;self.download_id=did;self._timer=None
        super().__init__(workspace.content,bg=workspace.p['dialog'],width=460);self.pack_propagate(False)
        self.pack(side='right',fill='y',before=workspace.listing)
        head=tk.Frame(self,bg=workspace.p['dialog']);head.pack(fill='x',padx=16,pady=16)
        Button(head,'×',self.close,palette=workspace.p,kind='icon',width=34).pack(side='right')
        self.title_label=label(head,'İndirme ayrıntıları',palette=workspace.p,weight='SemiBold');self.title_label.max_width=340;self.title_label.pack(side='left')
        # Full-width footer with inner padding (an outer margin left a strip and put the button on the edge).
        bar=tk.Frame(self,bg=workspace.p['footer']);bar.pack(side='bottom',fill='x')
        tk.Frame(bar,bg=workspace.p['line'],height=1).pack(fill='x')
        foot=tk.Frame(bar,bg=workspace.p['footer']);foot.pack(fill='x',padx=16,pady=12)
        self.pause_button=action(foot,'Devam et',self.pause_resume,workspace.p,'primary')
        self.cancel_button=action(foot,'İptal et',self.cancel,workspace.p,'danger_ghost')
        Button(foot,'Klasörü aç',lambda:self.content.open_folder(),palette=workspace.p,kind='ghost').pack(side='left')
        scroll=ScrollBody(self,workspace.p);scroll.pack(fill='both',expand=True)
        self.content=TransferContent(scroll.content,self.parent,did);self.content.pack(fill='both',expand=True);self.values=self.content.values
        self.bind('<Destroy>',self.dispose);self.parent.detail_windows[did]=self;self.tick()
    def tick(self):
        state=self.content.refresh()
        if not state:return self.close()
        self.title_label.configure(text=state['record']['filename'])
        self.pause_button.configure(text='Duraklat' if state['state'] in ('İndiriliyor','Bekliyor') else 'Devam et',state='disabled' if state['state'] in ('Tamamlandı','Birleştiriliyor','Dönüştürülüyor') else 'normal')
        self.cancel_button.configure(text='Kapat' if state['state']=='Tamamlandı' else 'İptal et',command=self.close if state['state']=='Tamamlandı' else self.cancel)
        self._timer=self.after(500,self.tick)
    def pause_resume(self):self.workspace.card_action(self.download_id)
    def cancel(self):self.parent.cancel_download(self.download_id);self.close()
    def close(self):
        self.workspace.dismissed=self.download_id
        if self.workspace.drawer is self:self.workspace.drawer=None
        self.destroy()
    def dispose(self,event):
        if event.widget is self:
            if self._timer:self.after_cancel(self._timer);self._timer=None
            if self.parent.detail_windows.get(self.download_id) is self:self.parent.detail_windows.pop(self.download_id,None)
