"""A19 named decisions and errors, preserving the old call-site return values."""
import tkinter as tk
from ui_overlays import MessageDialog


def owner_and_palette(parent=None):
    parent=parent or tk._default_root
    if parent is None:raise RuntimeError('An application window is required')
    window=parent.winfo_toplevel()
    palette=getattr(window,'p',None) or getattr(window,'palette',None)
    if palette is None:palette=getattr(window,'parent',parent).palette
    return window,palette


def choose(parent,title,message,actions,items=(),technical='',default='cancel'):
    owner,palette=owner_and_palette(parent)
    window=MessageDialog(owner,title,message,palette,items=items,technical=technical,tone='danger' if any('danger' in kind for _,_,kind in actions) else 'info')
    for key,label,kind in actions:window.add_action(key,label,kind)
    window.show()
    if default in window.actions:window.actions[default].focus_set()
    owner.wait_window(window);return window.result


def show_error(parent,title,message,technical='',actions=()):
    owner,palette=owner_and_palette(parent)
    window=MessageDialog(owner,title,message,palette,technical=technical,tone='error')
    for key,label,callback in actions:
        button=window.add_action(key,label,'primary')
        button.configure(command=lambda cb=callback,k=key:(window.finish(k),cb()))
    window.add_action('close','Kapat','secondary');window.show();return window


class MessageAPI:
    def askyesno(self,title,message,parent=None,**kwargs):
        label='Devam et';kind='primary'
        if title=='Onayla':label='Dosyaları sil' if 'kalıcı' in message else 'Listeden kaldır';kind='danger_solid' if 'kalıcı' in message else 'primary'
        elif title=='Sıfırdan indir':label='Sıfırdan başlat'
        elif title=='Taşıma önizlemesi':label='Dosyaları taşı'
        elif title=='SDM güncellemesi':label='Şimdi güncelle'
        label=kwargs.get('affirmative',label)
        if kwargs.get('danger'):kind='danger_solid'
        return choose(parent,title,message,(('yes',label,kind),('cancel','Vazgeç','ghost')),items=kwargs.get('items',()))=='yes'

    def askyesnocancel(self,title,message,parent=None,**kwargs):
        result=choose(parent,title,'Aynı adresten bir indirme var. Ne yapalım?',
            (('yes','Mevcut indirmeyi göster','primary'),('no','Yine de yeni indir','secondary'),('cancel','Vazgeç','ghost')),technical=message)
        return True if result=='yes' else False if result=='no' else None

    def showerror(self,title,message,parent=None,**kwargs):
        owner,_=owner_and_palette(parent);app=owner
        while not hasattr(app,'notify') and getattr(app,'parent',None):app=app.parent
        actions=[]
        if title in ('GitHub güncellemesi','Güncelleme') and hasattr(app,'check_updates'):actions=[('retry','Tekrar dene',lambda:app.check_updates(False))]
        elif title=='Ayarlar kaydedilemedi' and hasattr(owner,'save'):actions=[('retry','Tekrar dene',owner.save)]
        return show_error(parent,title,message,actions=actions)

    def showinfo(self,title,message,parent=None,**kwargs):
        owner,_=owner_and_palette(parent)
        app=owner
        while not hasattr(app,'notify') and getattr(app,'parent',None):app=app.parent
        if hasattr(app,'notify'):return app.notify(title,message,tone='success' if title in ('SHA-256','Yedekleme') else 'info')
        return show_error(parent,title,message)

    def showwarning(self,title,message,parent=None,**kwargs):
        owner,_=owner_and_palette(parent);app=owner
        while not hasattr(app,'notify') and getattr(app,'parent',None):app=app.parent
        if hasattr(app,'notify'):return app.notify(title,message,tone='warning')
        return show_error(parent,title,message)


messagebox=MessageAPI()
