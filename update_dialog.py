"""A17 consumes verified update selection; download/install logic stays intact."""
import tkinter as tk
import webbrowser
from urllib.parse import quote
from ui_dialog import AppWindow,AutoCard,label,action
from theme_widgets import Button
from app_version import VERSION


def attach_release_notes(updater,update):
    from updater import API
    try:
        with updater._get(API+'/releases/tags/'+quote(update['version'],safe='')) as response:release=response.json()
        update=dict(update,notes=release.get('body',''))
    except Exception:update=dict(update,notes='')
    update['notes_url']=API.replace('api.github.com/repos/','github.com/')+'/releases/tag/'+quote(update['version'],safe='')
    return update


class UpdateDialog(AppWindow):
    def __init__(self,parent,update):
        super().__init__(parent,'Yeni sürüm hazır',560,560);self.result=False
        label(self.body,VERSION+'  →  '+update['version'].lstrip('v'),palette=self.p,size=18,weight='SemiBold').pack(anchor='w',padx=24,pady=(0,16))
        card=AutoCard(self.body,self.p);label(card.content,'Bu sürümde',palette=self.p,weight='SemiBold').pack(anchor='w')
        notes=[line.strip().lstrip('#*- ').strip() for line in update.get('notes','').splitlines() if line.strip()][:5]
        text='\n'.join('• '+line for line in notes) if notes else 'Sürüm notları alınamadı; tüm sürüm notlarını açabilirsin.'
        tk.Label(card.content,text=text,wraplength=450,justify='left',anchor='w',bg=self.p['card'],fg=self.p['text'],font=('Inter',-13)).pack(fill='x',pady=12)
        if update.get('notes_url'):Button(card.content,'Tüm sürüm notları',lambda:webbrowser.open(update['notes_url']),palette=self.p,kind='link').pack(anchor='e')
        for index,text in enumerate(('Setup indirilir ve SHA-256 özeti doğrulanır','İndirmeler duraklar, SDM kapanır','Yeni sürüm kurulur ve SDM yeniden açılır'),1):
            # Numbers in their own column: '1' and '2' differ in width and shifted the text.
            row=tk.Frame(self.body,bg=self.p['dialog']);row.pack(fill='x',padx=24,pady=8)
            number_column=tk.Frame(row,bg=self.p['dialog'],width=24,height=20);number_column.pack(side='left');number_column.pack_propagate(False)
            label(number_column,str(index),palette=self.p,size=13,weight='SemiBold',muted=True).pack(side='left')
            label(row,text,palette=self.p,size=13).pack(side='left')
        active=parent.engine.get_active_count()+sum(task.status in ('İndiriliyor','Dönüştürülüyor') for task in parent.video_tasks.values())
        if active:label(self.body,f'{active} aktif indirme duraklatılacak; güncellemeden sonra sürdürülebilir.',palette=self.p,size=12).pack(anchor='w',padx=24,pady=12)
        action(self.actionbar,'Şimdi güncelle',self.accept,self.p,'primary');action(self.actionbar,'Daha sonra',self.close,self.p,'ghost')
    def accept(self):self.result=True;self.destroy()


def confirm_update(parent,update):
    window=UpdateDialog(parent,update);window.transient(parent);window.grab_set();parent.wait_window(window);return window.result
