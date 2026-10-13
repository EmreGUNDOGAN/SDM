import threading
import tkinter as tk
from tkinter import filedialog,messagebox
from datetime import datetime
import ttkbootstrap as tb
from app_version import VERSION
from utils import save_settings,DEFAULT_SETTINGS
from capture_policy import normalize_domain
from preferences import export_settings,import_settings,validate_settings


class SettingsDialog(tb.Toplevel):
    def __init__(self,parent):
        super().__init__(parent);self.parent=parent;self.title('SDM · Ayarlar');self.geometry('740x610')
        self.settings=dict(parent.settings);self.vars={}
        frame=tb.Frame(self,padding=20);frame.pack(fill='both',expand=True)
        notebook=tb.Notebook(frame);notebook.pack(fill='both',expand=True)
        self.tabs={}
        for name in ['Genel','Tarayıcı','Kuyruk','Güncelleme','Yedekleme']:
            tab=tb.Frame(notebook,padding=20);notebook.add(tab,text=name);self.tabs[name]=tab
        general=self.tabs['Genel']
        self.field(general,'download_dir','Kayıt klasörü')
        tb.Button(general,text='Klasör seç',bootstyle='secondary-outline',command=self.browse).pack(anchor='w',pady=(0,10))
        self.field(general,'theme','Tema (light / dark / system)',choices=['light','dark','system'])
        for key,label in [('default_connections','Paralel bağlantı sayısı (1–32)'),('max_simultaneous_downloads','Eşzamanlı indirme (1–10)'),('speed_limit_kbs','Toplam hız sınırı (KB/sn, 0 = sınırsız)')]:self.field(general,key,label)
        for key,label in [('auto_open_details','Yeni indirmede ilerleme penceresini aç'),('completion_popup','İndirme tamamlandı penceresini göster'),('notifications_enabled','Masaüstü bildirimi göster'),('clipboard_monitoring','Panodaki bağlantıları izle'),('start_minimized','Simge durumunda başlat')]:self.check(general,key,label)
        browser=self.tabs['Tarayıcı'];self.check(browser,'browser_capture','Tarayıcı indirmelerini yakala')
        tb.Label(browser,text='Hariç tutulan siteler · Her satıra bir alan adı').pack(anchor='w',pady=(15,5))
        self.sites=tk.Text(browser,height=7,bg=parent.palette['panel'],fg=parent.palette['text'],insertbackground=parent.palette['text'],relief='flat',font=('Segoe UI',11))
        self.sites.pack(fill='x');self.sites.insert('1.0','\n'.join(self.settings.get('excluded_sites',['canva.com'])))
        self.extensions=tk.StringVar(value=', '.join(self.settings.get('capture_extensions',[])))
        tb.Label(browser,text='Yakalanacak uzantılar (zip, exe, mp4…) · Boş = tümü').pack(anchor='w',pady=(15,5))
        tb.Entry(browser,textvariable=self.extensions).pack(fill='x')
        tb.Label(browser,text='Canva ve hariç tutulan sitelerde indirme tarayıcıda kalır.\nSağ tık ile bir siteyi bu listeye ekleyebilirsin.',wraplength=620).pack(anchor='w',pady=15)
        queue=self.tabs['Kuyruk']
        self.field(queue,'scheduled_start','Kuyruğu başlatma zamanı · YYYY-MM-DD HH:MM')
        self.check(queue,'shutdown_after_queue','Kuyruk tamamlanınca bilgisayarı kapat (60 sn iptal süresi)')
        tb.Label(queue,text='Boş zaman alanı: Kuyruk yalnızca “Kuyruğu başlat” ile çalışır.\nZamanlama için SDM açık olmalıdır. Video ve normal dosyalar\naynı eşzamanlı indirme limitini paylaşır.',wraplength=600).pack(anchor='w',pady=20)
        update=self.tabs['Güncelleme']
        tb.Label(update,text=f'SDM {VERSION}',font=('Segoe UI',20,'bold')).pack(anchor='w')
        self.check(update,'update_check_on_start','Açılışta GitHub güncellemelerini kontrol et')
        tb.Label(update,text='Özel depo: EmreGUNDOGAN/SDM\nFine-grained token: yalnızca bu depo, Contents: Read.\nToken Windows hesabına bağlı şifrelenir; yedeğe eklenmez.',wraplength=620).pack(anchor='w',pady=15)
        self.token=tk.StringVar();tb.Entry(update,textvariable=self.token,show='•').pack(fill='x')
        tb.Label(update,text='Boş bırakırsan kayıtlı token korunur.').pack(anchor='w',pady=5)
        actions=tb.Frame(update);actions.pack(fill='x',pady=10)
        tb.Button(actions,text='Token kaydet',command=self.store_token).pack(side='left')
        tb.Button(actions,text='Token sil',bootstyle='secondary-outline',command=self.remove_token).pack(side='left',padx=10)
        tb.Button(update,text='Güncellemeleri kontrol et',command=lambda:parent.check_updates(False)).pack(anchor='w',pady=15)
        backup=self.tabs['Yedekleme']
        tb.Label(backup,text='Site istisnaları, klasör, sütunlar ve görünüm tercihlerini taşı.\nErişim bilgileri ve indirme geçmişi yedeğe alınmaz.',wraplength=600).pack(anchor='w',pady=15)
        tb.Button(backup,text='Ayarları dışa aktar',command=self.export).pack(anchor='w',pady=10)
        tb.Button(backup,text='Yedekten geri yükle',command=self.restore).pack(anchor='w',pady=10)
        buttons=tb.Frame(frame);buttons.pack(fill='x',pady=(15,0))
        tb.Button(buttons,text='Kaydet',command=self.save).pack(side='right');tb.Button(buttons,text='İptal',bootstyle='secondary-outline',command=self.destroy).pack(side='right',padx=10)

    def field(self,container,key,label,choices=None):
        value=self.settings.get(key,DEFAULT_SETTINGS.get(key,''))
        var=tk.StringVar(value='light' if key=='theme' and value=='cosmo' else str(value));self.vars[key]=var
        row=tb.Frame(container);row.pack(fill='x',pady=5)
        tb.Label(row,text=label).pack(side='left')
        widget=tb.Combobox(row,textvariable=var,values=choices,state='readonly',width=20) if choices else tb.Entry(row,textvariable=var,width=30)
        widget.pack(side='right')

    def check(self,container,key,label):
        var=tk.BooleanVar(value=self.settings.get(key,False));self.vars[key]=var
        tb.Checkbutton(container,text=label,variable=var).pack(anchor='w',pady=5)

    def browse(self):
        path=filedialog.askdirectory(parent=self,initialdir=self.vars['download_dir'].get())
        if path:self.vars['download_dir'].set(path)

    def collect(self):
        values=dict(self.settings)
        for key,var in self.vars.items():
            values[key]=int(var.get()) if type(DEFAULT_SETTINGS.get(key)) is int else var.get()
        values['excluded_sites']=sorted(set(normalize_domain(v) for v in self.sites.get('1.0','end').splitlines() if v.strip()))
        values['capture_extensions']=[v.strip().lower().lstrip('.') for v in self.extensions.get().split(',') if v.strip()]
        if values['scheduled_start']:
            datetime.strptime(values['scheduled_start'],'%Y-%m-%d %H:%M')
        validate_settings(values)
        return values

    def save(self):
        try:
            values=self.collect()
            if not save_settings(values):raise ValueError('Ayar dosyası kaydedilemedi.')
            self.parent.apply_settings(values);self.destroy()
        except Exception as error:messagebox.showerror('Ayarlar kaydedilemedi',str(error),parent=self)

    def store_token(self):
        try:
            if not self.token.get().strip():return
            from updater import save_token
            save_token(self.token.get());self.token.set('');messagebox.showinfo('GitHub','Token güvenli biçimde kaydedildi.',parent=self)
        except Exception as error:messagebox.showerror('GitHub',str(error),parent=self)

    def remove_token(self):
        from updater import save_token
        save_token('');self.token.set('')

    def export(self):
        path=filedialog.asksaveasfilename(parent=self,defaultextension='.json',initialfile='SDM-ayarlar.json')
        if path:
            try:export_settings(path,self.collect());messagebox.showinfo('Yedekleme','Ayarlar dışa aktarıldı.',parent=self)
            except Exception as error:messagebox.showerror('Yedekleme',str(error),parent=self)

    def restore(self):
        path=filedialog.askopenfilename(parent=self,filetypes=[('SDM ayar yedeği','*.json')])
        if path:
            try:
                values=dict(DEFAULT_SETTINGS);values.update(import_settings(path))
                if not save_settings(values):raise ValueError('Ayarlar kaydedilemedi.')
                self.parent.apply_settings(values);self.destroy()
            except Exception as error:messagebox.showerror('Yedekleme',str(error),parent=self)
