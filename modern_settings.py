"""A08–A13 settings content shared with Odak's embedded settings page."""
import copy
import logging
import threading
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as tb
from app_version import VERSION
from utils import DEFAULT_SETTINGS,save_settings
from preferences import export_settings,import_settings,validate_settings
from capture_policy import normalize_domain
from theme_catalog import migrate_settings,theme_key
from theme_widgets import Button
from ui_dialog import ScrollBody,AutoCard,label,field
from ui_controls import Switch,Select,SegmentedControl,RadioCard,ChipInput,TextInput,watch
from ui_surface import TextLabel

SECTIONS={'Genel':('sliders','Kayıt yeri, görünüm ve aktarım tercihleri'),
 'Tarayıcı':('globe','Yakalama, dosya türleri ve site istisnaları'),
 'Kuyruk':('queue','Adlandırılmış kuyruklar ve zamanlama'),
 'Araçlar':('wrench','Hız sınırı ve yardımcılar'),
 'Güncelleme':('refresh','Sürüm ve doğrulanmış kurulum akışı'),
 'Yedekleme':('folder','Tercihleri dışa aktarın veya geri yükleyin')}
BOUNDS={'default_connections':(1,32),'max_simultaneous_downloads':(1,10),'speed_limit_kbs':(0,1000000),'relax_limit_kbs':(1,1000000)}


class SectionDeck(tk.Frame):
    def __init__(self,master,palette,command):
        super().__init__(master,bg=palette['dialog']);self.current=None;self.command=command
    def select(self,tab=None):
        if tab is None:return str(self.current)
        tab=self.nametowidget(str(tab))
        if self.current:self.current.pack_forget()
        self.current=tab;tab.pack(fill='both',expand=True);self.command(tab)


class SettingsContent(tk.Frame):
    def __init__(self,master,parent,embedded=False,on_saved=None,on_cancel=None):
        self.app=parent;self.p=parent.palette;self.embedded=embedded;self.on_saved=on_saved;self.on_cancel=on_cancel
        super().__init__(master,bg=self.p['dialog'])
        self.settings=migrate_settings(copy.deepcopy(dict(DEFAULT_SETTINGS,**parent.settings)))
        self.vars={};self.inputs={};self._traces=[];self._initializing=True;self._timer=None
        self._preview_timer=None;self._appearance_closed=False;self._preview_embedded=embedded
        self.error=tk.StringVar(self,'');self.change_count=tk.IntVar(self,0)
        self.footer=tk.Frame(self,bg=self.p['footer']);self.footer.pack(side='bottom',fill='x')
        tk.Frame(self.footer,height=1,bg=self.p['line']).pack(fill='x')
        foot=tk.Frame(self.footer,bg=self.p['footer']);foot.pack(fill='x',padx=24,pady=12)
        self.caption=label(foot,'Görünüm anında önizlenir; Kaydet ile kalıcı olur.',palette=self.p,size=12,muted=True);self.caption.max_width=420;self.caption.pack(side='left')
        self.save_button=Button(foot,'Kaydet',self.save,palette=self.p,kind='primary');self.save_button.pack(side='right')
        Button(foot,'Geri al' if embedded else 'İptal',self.revert if embedded else self.cancel,palette=self.p,kind='ghost').pack(side='right',padx=8)
        # Packed only with an error: the empty line left a band under the buttons.
        error=TextLabel(self.footer,textvariable=self.error,fg=self.p['danger_fg'],size=12,max_width=700)
        def sync_error(*args):
            if self.error.get():error.pack(anchor='w',padx=24,pady=(0,8))
            else:error.pack_forget()
        watch(self,self.error,sync_error)
        self.side=tk.Frame(self,bg=self.p['side'],width=232 if embedded else 200);self.side.pack(side='left',fill='y');self.side.pack_propagate(False)
        label(self.side,'Ayarlar',palette=self.p,size=18,weight='Bold').pack(anchor='w',padx=20,pady=24)
        label(self.side,'SDM '+VERSION,palette=self.p,size=12,muted=True).pack(side='bottom',anchor='w',padx=20,pady=20)
        self.deck=SectionDeck(self,self.p,self.section_changed);self.deck.pack(side='left',fill='both',expand=True)
        self.tabs={};self.nav={}
        for name,(glyph,description) in SECTIONS.items():
            tab=ScrollBody(self.deck,self.p);self.tabs[name]=tab
            label(tab.content,name,palette=self.p,size=20,weight='Bold').pack(anchor='w',padx=24,pady=(24,6))
            title=label(tab.content,description,palette=self.p,size=12,muted=True);title.max_width=560;title.pack(anchor='w',padx=24,pady=(0,20))
            button=Button(self.side,name,lambda n=name:self.show_section(n),palette=self.p,kind='ghost',width=168)
            button.icon_name=glyph;button.pack(fill='x',padx=12,pady=3);self.nav[name]=button
        self.general();self.browser();self.queues();self.tools();self.update_page();self.backup()
        for variable in self.vars.values():self.watch(variable,self.changed)
        self.watch(self.site_values,self.changed);self.watch(self.extensions,self.extensions_changed)
        self._initializing=False;self.baseline=self.collect();self.changed();self.show_section('Genel')
        for key in ('design','color_mode'):self.watch(self.vars[key],self.request_preview)
        self.app._settings_editor=self
        self.bind('<Destroy>',self.dispose,add='+');self.update_status()

    def watch(self,var,callback):self._traces.append((var,var.trace_add('write',callback)))
    def card(self,section,title):
        card=AutoCard(self.tabs[section].content,self.p)
        label(card.content,title,palette=self.p,weight='SemiBold').pack(anchor='w',pady=(0,12));return card.content
    def text(self,parent,text):
        # No Tk border/padding: it indented every description 3 px from its title.
        item=tk.Label(parent,text=text,bg=parent.cget('bg'),fg=self.p['muted'],font=('Inter',-12),justify='left',anchor='w',wraplength=540,padx=0,pady=0,bd=0,highlightthickness=0)
        item.pack(fill='x',pady=6);item.bind('<Configure>',lambda e:item.configure(wraplength=max(80,e.width)));return item
    def value(self,key):
        if key not in self.vars:
            value=self.settings.get(key,DEFAULT_SETTINGS.get(key,''));self.vars[key]=tk.BooleanVar(self,value) if type(value) is bool else tk.StringVar(self,str(value))
        return self.vars[key]
    def field(self,parent,key,title,choices=None,actions=(),side=None,hint=''):
        var=self.value(key)
        if choices:
            self.text(parent,title);widget=Select(parent,choices,var,palette=self.p,width=260);widget.pack(fill='x',pady=5)
        else:widget=field(parent,title,var,self.p,width=160 if side else 220,actions=actions,side=side,hint=hint)
        self.inputs[key]=widget;return widget
    def check(self,parent,key,title,description=''):
        row=tk.Frame(parent,bg=self.p['card']);row.pack(fill='x',pady=6)
        Switch(row,self.value(key),palette=self.p).pack(side='right')
        text=label(row,title,palette=self.p);text.max_width=440;text.pack(anchor='w')
        if description:self.text(row,description)
    def general(self):
        c=self.card('Genel','Kayıt yeri');self.field(c,'download_dir','Kayıt klasörü',actions=[('Klasör seç',self.browse)])
        c=self.card('Genel','Görünüm');row=tk.Frame(c,bg=self.p['card']);row.pack(fill='x')
        for key,title,description in [('atlas','Atlas Pro','Kenar menü ve ayrıntılı tablo'),('odak','Odak Akışı','İkon şeridi ve indirme kartları')]:RadioCard(row,key,self.value('design'),title,description,self.p,width=230).pack(side='left',fill='x',expand=True,padx=4)
        SegmentedControl(c,{'light':'Açık','dark':'Koyu','system':'Sistem'},self.value('color_mode'),palette=self.p).pack(fill='x',pady=12)
        self.field(c,'language','Sayı biçimi · Türkçe (1,5) / English (1.5)',{'tr':'Türkçe (1,5)','en':'English (1.5)'})
        c=self.card('Genel','Aktarım')
        row=tk.Frame(c,bg=self.p['card']);row.pack(fill='x')
        for key,title,hint in [('default_connections','Paralel bağlantı','1–32 arası'),('max_simultaneous_downloads','Eşzamanlı indirme','1–10 arası'),('speed_limit_kbs','Toplam hız sınırı','KB/sn · 0 = sınırsız')]:self.field(row,key,title,side='left',hint=hint)
        c=self.card('Genel','Davranış')
        for key,title in [('auto_open_details','Yeni indirmede ayrıntıları aç'),('completion_popup','Tamamlandı penceresini göster'),('notifications_enabled','Masaüstü bildirimi göster'),('clipboard_monitoring','Panodaki bağlantıları izle'),('start_minimized','Simge durumunda başlat')]:self.check(c,key,title)
    def browser(self):
        c=self.card('Tarayıcı','Yakalama');self.check(c,'browser_capture','Tarayıcı indirmelerini yakala')
        self.browser_status=self.text(c,'Chrome / Opera · Henüz eklenti teması alınmadı.')
        Button(c,'Kurulum adımları',self.browser_help,palette=self.p,kind='soft').pack(anchor='w')
        c=self.card('Tarayıcı','Yakalanacak uzantılar');self.text(c,'Boş liste tüm dosya türlerini yakalar.')
        self.extensions=tk.StringVar(self,', '.join(self.settings['capture_extensions']))
        self.chips=ChipInput(c,self.settings['capture_extensions'],self.p,command=lambda:self.extensions.set(', '.join(self.chips.values)));self.chips.pack(fill='x')
        c=self.card('Tarayıcı','Hariç tutulan siteler');self.site_values=tk.StringVar(self,'\n'.join(self.settings['excluded_sites']))
        self.sites_input=TextInput(c,variable=self.site_values,palette=self.p,multiline=True,height=120);self.sites_input.pack(fill='x');self.sites=self.sites_input.entry
        self.new_site=tk.StringVar(self,'');self.site_input=TextInput(c,variable=self.new_site,palette=self.p,placeholder='example.com');self.site_input.pack(fill='x',pady=8)
        Button(c,'Ekle',self.add_site,palette=self.p,kind='soft').pack(side='left');Button(c,'Seçili satırı kaldır',self.remove_site,palette=self.p,kind='ghost').pack(side='left',padx=8)
    def queues(self):
        from queue_ui import QueueEditor
        self.queue_editor=QueueEditor(self.tabs['Kuyruk'].content,self.settings['queues'],palette=self.p,command=self.changed);self.queue_editor.pack(fill='both',expand=True,padx=16)
        c=self.card('Kuyruk','Tamamlanınca');self.check(c,'shutdown_after_queue','Kuyruk bitince bilgisayarı kapat','Kapatmadan önce 60 saniye iptal süresi verilir.')
    def tools(self):
        c=self.card('Araçlar','İnterneti rahatlat');self.field(c,'relax_limit_kbs','Hız · KB/sn')
        row=tk.Frame(c,bg=self.p['card']);row.pack(fill='x',pady=8)
        for value,title in [(256,'256 KB/sn'),(512,'512 KB/sn'),(1024,'1 MB/sn'),(2048,'2 MB/sn')]:Button(row,title,lambda v=value:self.vars['relax_limit_kbs'].set(str(v)),palette=self.p,kind='soft').pack(side='left',padx=3)
        c=self.card('Araçlar','Yardımcılar')
        for key,title,description in [('mini_hud','Açılışta masaüstü HUD','Hızı ve aktif dosyaları küçük pencerede gösterir.'),('duplicate_warning','Yinelenen bağlantı uyarısı','Aynı bağlantıyı eklerken seçim sunar.'),('disk_check','Boş alanı kontrol et','İndirmeye eklemeden önce hedef diski kontrol eder.'),('auto_extract','Arşivleri otomatik çıkar','Tamamlanan ZIP/RAR dosyalarını çıkarır.')]:self.check(c,key,title,description)
        self.field(c,'extract_dir','Arşiv çıktı klasörü · boş = dosyanın yanı',actions=[('Klasör seç',self.pick_extract)])
        c=self.card('Araçlar','Kaspersky');self.av_status=self.text(c,'Kurulum durumu kontrol ediliyor…');self.text(c,'Tarama yalnız Tamamlandı penceresindeki Virüs tarat eylemiyle başlar. Otomatik tarama yapılmaz.')
        def work():
            try:
                from antivirus import find_kaspersky
                find_kaspersky();text='Desteklenen Kaspersky kurulu.'
            except ValueError:text='Desteklenen Kaspersky bulunamadı.'
            self.app.post_ui(lambda:self.av_status.configure(text=text) if self.winfo_exists() else None)
        threading.Thread(target=work,daemon=True).start()
    def update_page(self):
        c=self.card('Güncelleme','SDM '+VERSION);self.version_status=self.text(c,'Henüz denetlenmedi.')
        Button(c,'Güncellemeleri denetle',lambda:self.app.check_updates(False),palette=self.p,kind='primary').pack(anchor='w',pady=8)
        self.check(c,'update_check_on_start','Açılışta güncellemeleri kontrol et')
        c=self.card('Güncelleme','Güncelleme nasıl çalışır')
        self.text(c,'1  Yeni setup indirilir.\n2  SHA-256 doğrulanır.\n3  Onayınla indirmeler duraklatılır ve kurulum başlar.')
        self.text(c,'Kaynak: EmreGUNDOGAN/SDM-Updates · Token gerekmez. Kaynak kod özel SDM deposunda kalır.')
        Button(c,'Kayıtlı tokenı sil',self.remove_token,palette=self.p,kind='danger_ghost').pack(anchor='w',pady=8)
    def backup(self):
        c=self.card('Yedekleme','Dışa aktar');self.text(c,'Ayarları JSON dosyasına kaydet. İndirme geçmişi taşınmaz.')
        Button(c,'Ayarları dışa aktar',self.export,palette=self.p,kind='soft').pack(anchor='w')
        c=self.card('Yedekleme','Geri yükle');self.text(c,'Yedek önce bu forma alınır. Kaydet’e basmadan uygulanmaz.')
        Button(c,'Yedekten geri yükle',self.restore,palette=self.p,kind='soft').pack(anchor='w')
        c=self.card('Yedekleme','Yedeğe girer')
        self.text(c,'Kayıt klasörü; kuyruklar ve zamanlamalar; aktarım sınırları; yakalama ve site istisnaları; uzantılar; görünür sütunlar; görünüm; sayı biçimi; davranış ve yardımcı tercihleri; HUD konumu. Geçici yakalama duraklatması sıfırlanır.')
        c=self.card('Yedekleme','Yedeğe girmez');self.text(c,'Token; eklenti bağlantı anahtarı; indirme veritabanı/geçmişi; indirilen dosyalar.')
    def show_section(self,name):self.deck.select(self.tabs[name])
    def section_changed(self,tab):
        for name,button in self.nav.items():button.selected=self.tabs[name] is tab;button.draw()
    def browser_help(self):
        from ui_messages import messagebox
        messagebox.showinfo('Eklenti kurulumu','Chrome / Opera eklenti sayfasında Geliştirici modu → Paketlenmemiş öğe yükle ile SDM extension klasörünü seçin.',parent=self)
    def browse(self):self.pick('download_dir')
    def pick_extract(self):self.pick('extract_dir')
    def pick(self,key):
        path=filedialog.askdirectory(parent=self.winfo_toplevel(),initialdir=self.vars[key].get() or None)
        if path:self.vars[key].set(path)
    def add_site(self):
        try:
            site=normalize_domain(self.new_site.get());self.site_values.set('\n'.join(sorted(set(self.site_values.get().splitlines()+[site]))));self.new_site.set('');self.site_input.set_error('')
        except ValueError as error:self.site_input.set_error(str(error))
    def remove_site(self):self.sites.delete('insert linestart','insert lineend +1c')
    def extensions_changed(self,*args):
        values=list(dict.fromkeys(v.strip().lower().lstrip('.') for v in self.extensions.get().split(',') if v.strip()))
        if values!=self.chips.values:self.chips.values=values;self.chips.refresh()
        self.changed()
    def collect(self):
        values=copy.deepcopy(self.settings)
        for key,var in self.vars.items():values[key]=int(var.get()) if type(DEFAULT_SETTINGS.get(key)) is int else var.get()
        values['excluded_sites']=sorted(set(normalize_domain(v) for v in self.site_values.get().splitlines() if v.strip()))
        values['capture_extensions']=[v.strip().lower().lstrip('.') for v in self.extensions.get().split(',') if v.strip()]
        values['queues']=self.queue_editor.collect();return validate_settings(values)
    def changed(self,*args):
        if self._initializing:return
        problems=[]
        for key,(low,high) in BOUNDS.items():
            try:value=int(self.vars[key].get());valid=low<=value<=high
            except ValueError:valid=False
            text='' if valid else f'{low}–{high} arasında bir sayı gir.';self.inputs[key].set_error(text)
            if text:problems.append(text)
        try:values=self.collect();self.error.set('');count=sum(values.get(k)!=self.baseline.get(k) for k in values)
        except (ValueError,TypeError,KeyError) as error:self.error.set(str(error));problems.append(str(error));count=max(1,self.change_count.get())
        self.change_count.set(count);self.caption.configure(text=f'Kaydedilmemiş {count} değişiklik · Görünüm önizlemesi' if count else 'Görünüm anında önizlenir; Kaydet ile kalıcı olur.')
        self.save_button.configure(state='disabled' if problems else 'normal')
    def request_preview(self,*args):
        if self._initializing or self._appearance_closed:return
        if self._preview_timer:self.after_cancel(self._preview_timer)
        self._preview_timer=self.after_idle(self.preview)
    def stop_preview_timer(self):
        if self._preview_timer:self.after_cancel(self._preview_timer);self._preview_timer=None
    def preview(self):
        self._preview_timer=None
        design=self.vars['design'].get();mode=self.vars['color_mode'].get();app=self.app
        if theme_key(dict(app.settings,design=design,color_mode=mode))==app.theme_family+'_'+app.ui_theme:return
        # Keep raw drafts, including invalid fields; preview must not validate or save them.
        draft=self.snapshot_draft();embedded=self._preview_embedded;dialog=self.winfo_toplevel()
        geometry=dialog.geometry() if not self.embedded else None
        self._appearance_closed=True
        if not self.embedded:dialog.destroy()
        app.preview_appearance(design,mode)
        if embedded and app.theme_family=='odak':
            app.open_settings_dialog();editor=app._atlas_workspace.settings_page
        else:
            dialog=SettingsDialog(app)
            if geometry:dialog.geometry(geometry)
            editor=dialog.content
        editor.restore_draft(draft);editor._preview_embedded=embedded
    def snapshot_draft(self):
        queue=self.queue_editor
        names=('name','limit','enabled','once_enabled','date_text','once_hour','once_minute')
        return dict(settings=copy.deepcopy(self.settings),baseline=copy.deepcopy(self.baseline),
                    values={key:var.get() for key,var in self.vars.items()},sites=self.site_values.get(),
                    extensions=self.extensions.get(),new_site=self.new_site.get(),
                    queues=copy.deepcopy(queue.queues),renames=queue.renames.copy(),index=queue.index,
                    queue_values={key:getattr(queue,key).get() for key in names},
                    days=[var.get() for var in queue.days],times={key:[v.get() for v in pair] for key,pair in queue.times.items()},
                    section=next(name for name,tab in self.tabs.items() if tab is self.deck.current),
                    scroll={name:tab.canvas.yview()[0] for name,tab in self.tabs.items()})
    def restore_draft(self,draft):
        self._initializing=True;self.settings=draft['settings'];self.baseline=draft['baseline']
        for key,value in draft['values'].items():self.vars[key].set(value)
        self.site_values.set(draft['sites']);self.extensions.set(draft['extensions']);self.new_site.set(draft['new_site'])
        queue=self.queue_editor;queue._loading=True;queue.queues=draft['queues'];queue.renames=draft['renames'];queue.index=draft['index']
        queue.names.configure(values=[q['name'] for q in queue.queues]);queue.names.current(queue.index)
        for key,value in draft['queue_values'].items():getattr(queue,key).set(value)
        for var,value in zip(queue.days,draft['days']):var.set(value)
        for key,values in draft['times'].items():
            for var,value in zip(queue.times[key],values):var.set(value)
        queue._loading=False;queue.update_summary();self._initializing=False;self.extensions_changed();self.changed()
        self.show_section(draft['section'])
        self.update_idletasks()
        for name,position in draft['scroll'].items():self.tabs[name].canvas.yview_moveto(position)
    def cancel_preview(self):
        self.stop_preview_timer();self._appearance_closed=True
        if theme_key(self.app.settings)!=self.app.theme_family+'_'+self.app.ui_theme:
            self.app.preview_appearance(self.app.settings['design'],self.app.settings['color_mode'])
    def cancel(self):
        self.cancel_preview()
        if self.on_cancel:self.on_cancel()
    def save(self):
        try:
            values=self.collect()
            if not save_settings(values):raise ValueError('Ayar dosyası kaydedilemedi.')
            for record in self.app.db.get_all_downloads():
                if record['queue_name'] in self.queue_editor.renames:self.app.db.set_queue(record['id'],self.queue_editor.renames[record['queue_name']])
            for key in ('_running_queues','_scheduled_queues'):setattr(self.app,key,{self.queue_editor.renames.get(name,name) for name in getattr(self.app,key)})
            self.baseline=copy.deepcopy(values);self.change_count.set(0);callback=self.on_saved;app=self.app
            self.stop_preview_timer();self._appearance_closed=True
            app.apply_settings(values)
            if callback:callback()
            app.notify('Ayarlar','Değişiklikler kaydedildi.',tone='success')
            return True
        except Exception as error:
            logging.getLogger('SDM.GUI').exception('Ayarlar kaydedilemedi')
            if self.winfo_exists():self._appearance_closed=False;self.error.set(str(error))
            return False
    def replace_values(self,values):
        self._initializing=True;self.settings=migrate_settings(copy.deepcopy(values))
        for key,var in self.vars.items():var.set(self.settings.get(key,DEFAULT_SETTINGS[key]))
        self.site_values.set('\n'.join(self.settings['excluded_sites']));self.extensions.set(', '.join(self.settings['capture_extensions']))
        self.queue_editor.replace(self.settings['queues']);self._initializing=False;self.extensions_changed();self.changed();self.request_preview()
    def revert(self):self.replace_values(self.baseline)
    def export(self):
        path=filedialog.asksaveasfilename(parent=self.winfo_toplevel(),defaultextension='.json',initialfile='SDM-ayarlar.json')
        if path:
            try:
                export_settings(path,self.collect())
                from pathlib import Path
                import os
                self.app.notify('Yedekleme','Ayarlar dışa aktarıldı.',('Klasörü aç',lambda:os.startfile(str(Path(path).parent))),tone='success')
            except Exception as error:self.error.set(str(error))
    def restore(self):
        path=filedialog.askopenfilename(parent=self.winfo_toplevel(),filetypes=[('SDM ayar yedeği','*.json')])
        if path:
            try:self.replace_values(dict(copy.deepcopy(DEFAULT_SETTINGS),**import_settings(path)))
            except Exception as error:self.error.set(str(error))
    def remove_token(self):
        from updater import save_token
        save_token('');self.app.notify('Güncelleme','Önceki token silindi. Yeni kaynak token kullanmaz.')
    def update_status(self):
        import time
        bridge=getattr(self.app,'_browser_bridge',None);clients=bridge.client_snapshot() if bridge else {}
        self.browser_status.configure(text='\n'.join(f'{name} · '+('Bağlı' if time.monotonic()-value['seen']<90 else 'Son temas 90 sn önce; canlı bağlantı doğrulanmadı')+' · eklenti '+value['version'] for name,value in clients.items()) if clients else 'Chrome / Opera · Henüz eklenti teması alınmadı. Kurulum adımlarını açabilirsiniz.')
        self.version_status.configure(text=getattr(self.app,'_update_result_text','Henüz denetlenmedi.'))
        self._timer=self.after(1000,self.update_status)
    def dispose(self,event):
        if event.widget is self:
            self.stop_preview_timer()
            if not self._appearance_closed and getattr(self.app,'_settings_editor',None) is self:
                def rollback():
                    if getattr(self.app,'_settings_editor',None) is self:self.cancel_preview()
                self.app.after_idle(rollback)
            if self._timer:self.after_cancel(self._timer)
            for var,token in self._traces:var.trace_remove('write',token)


class SettingsDialog(tb.Toplevel):
    def __init__(self,parent):
        super().__init__(parent);self.parent=parent;self.p=parent.palette;self.title('SDM · Ayarlar')
        self.geometry(f'{min(960,self.winfo_screenwidth()-80)}x{min(760,self.winfo_screenheight()-100)}');self.minsize(760,520)
        self.content=SettingsContent(self,parent,on_saved=self.destroy,on_cancel=self.destroy);self.content.pack(fill='both',expand=True)
        self.tabs=self.content.tabs;self.vars=self.content.vars;self.queue_editor=self.content.queue_editor
        self.bind('<Escape>',lambda e:self.content.cancel());self.protocol('WM_DELETE_WINDOW',self.content.cancel)
    def collect(self):return self.content.collect()
    def save(self):return self.content.save()
    def show_section(self,name):self.content.show_section(name)
