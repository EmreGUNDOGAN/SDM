"""A17 consumes verified update selection; download/install logic stays intact."""
import tkinter as tk
import webbrowser
from urllib.parse import quote
from ui_dialog import AppWindow,AutoCard,label,action,step
from theme_widgets import Button
from app_version import VERSION
from ui_tokens import text_px


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
        pano=self.p.get('design')=='pano'
        if pano:
            self.header.pack_forget()
            self.hero=AutoCard(self.body,dict(self.p,card=self.p['accent'],line=self.p['accent'],text=self.p['on_accent']),padding=20);self.hero.radius=22
            self.hero.pack_configure(pady=(18,12))
            from ui_surface import surface,photo,icon
            mark=tk.Canvas(self.hero.content,width=52,height=52,bg=self.p['accent'],highlightthickness=0);mark.pack(side='left',padx=(0,16))
            image=surface(52,52,self.p['accent'],self.p['accent_text'],radius=16);glyph=icon('refresh',26,self.p['on_accent']);image.paste(glyph,(13,13),glyph)
            mark.image=photo(image,mark);mark.create_image(0,0,image=mark.image,anchor='nw')
            info=tk.Frame(self.hero.content,bg=self.p['accent']);info.pack(side='left',fill='x',expand=True)
            label(info,'Yeni sürüm hazır',palette=self.hero.p,size=19,weight='Bold').pack(anchor='w')
            label(info,VERSION+'  →  '+update['version'].lstrip('v'),palette=self.hero.p,size=14,weight='SemiBold').pack(anchor='w',pady=(8,0))
        else:label(self.body,VERSION+'  →  '+update['version'].lstrip('v'),palette=self.p,size=18,weight='SemiBold').pack(anchor='w',padx=24,pady=(0,16))
        card=AutoCard(self.body,self.p);label(card.content,'Bu sürümde',palette=self.p,weight='SemiBold').pack(anchor='w')
        if pano:card.radius=22
        notes=[line.strip().lstrip('#*- ').strip() for line in update.get('notes','').splitlines() if line.strip()][:5]
        text='\n'.join('• '+line for line in notes) if notes else 'Sürüm notları alınamadı; tüm sürüm notlarını açabilirsin.'
        tk.Label(card.content,text=text,wraplength=450,justify='left',anchor='w',bg=self.p['card'],fg=self.p['text'],font=('Inter',text_px(13))).pack(fill='x',pady=12)
        if update.get('notes_url'):Button(card.content,'Tüm sürüm notları',lambda:webbrowser.open(update['notes_url']),palette=self.p,kind='link').pack(anchor='e')
        self.step_cards=[]
        if pano:
            steps=tk.Frame(self.body,bg=self.p['dialog']);steps.pack(fill='x',padx=24,pady=(0,12));steps.columnconfigure((0,1,2),weight=1,uniform='update')
        for index,text in enumerate(('Setup indirilir ve SHA-256 özeti doğrulanır','İndirmeler duraklar, SDM kapanır','Yeni sürüm kurulur ve SDM yeniden açılır'),1):
            if pano:
                holder=tk.Frame(steps,bg=self.p['dialog']);holder.grid(row=0,column=index-1,sticky='nsew',padx=((0,6),(3,3),(6,0))[index-1])
                tile=AutoCard(holder,self.p,padding=12);tile.radius=18;tile.pack_configure(padx=0,pady=0,fill='both',expand=True);self.step_cards.append(tile)
                heading=step(tile.content,index,('İndir ve doğrula','Duraklat','Kur ve aç')[index-1],self.p);heading.pack(anchor='w')
                for widget in heading.pack_slaves():widget.pack_configure(side='top',anchor='w',padx=0)
                heading.title.pack_configure(pady=(10,4))
                note=tk.Label(tile.content,text=text,wraplength=120,justify='left',anchor='w',bg=self.p['card'],fg=self.p['muted'],font=('Inter',text_px(12)));note.pack(fill='x')
                tile.content.bind('<Configure>',lambda event,note=note:note.configure(wraplength=event.width),add='+')
                continue
            # Numbers in their own column: '1' and '2' differ in width and shifted the text.
            row=tk.Frame(self.body,bg=self.p['dialog']);row.pack(fill='x',padx=24,pady=8)
            number_column=tk.Frame(row,bg=self.p['dialog'],width=24,height=20);number_column.pack(side='left');number_column.pack_propagate(False)
            label(number_column,str(index),palette=self.p,size=13,weight='SemiBold',muted=True).pack(side='left')
            label(row,text,palette=self.p,size=13).pack(side='left')
        active=parent.engine.get_active_count()+sum(task.status in ('İndiriliyor','Dönüştürülüyor') for task in parent.video_tasks.values())
        if active:
            message=f'{active} aktif indirme duraklatılacak; güncellemeden sonra sürdürülebilir.'
            if pano:
                warning=AutoCard(self.body,dict(self.p,card=self.p['warning_bg'],line=self.p['warning_bg']),padding=12);warning.radius=16
                tk.Label(warning.content,text=message,wraplength=450,justify='left',bg=self.p['warning_bg'],fg=self.p['warning_fg'],font=('Inter',text_px(12))).pack(fill='x')
            else:label(self.body,message,palette=self.p,size=12).pack(anchor='w',padx=24,pady=12)
        action(self.actionbar,'Şimdi güncelle',self.accept,self.p,'start' if pano else 'primary');action(self.actionbar,'Daha sonra',self.close,self.p,'secondary' if pano else 'ghost')
    def accept(self):self.result=True;self.destroy()


def confirm_update(parent,update):
    window=UpdateDialog(parent,update);window.transient(parent);window.grab_set();parent.wait_window(window);return window.result
