"""A17 consumes verified update selection; download/install logic stays intact."""
import tkinter as tk
import webbrowser
from urllib.parse import quote
from ui_dialog import AppWindow,AutoCard,label,action,step,caption
from theme_widgets import Button
from app_version import VERSION
from ui_tokens import text_px,YORUNGE_MONO_FAMILY
from ui_surface import TextLabel


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
        if self.p.get('design')=='yorunge':self.build_orbit(parent,update);return
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
    def build_orbit(self,parent,update):
        """F17: featured version panel, notes, one install-order panel, warning strip."""
        from ui_surface import surface,photo,icon
        from PIL import ImageDraw
        p=self.p;self.header.pack_forget();self.step_cards=[]
        def mono(parent_,text,size=10,fg=None,weight='Regular'):
            return TextLabel(parent_,text,size=size,weight=weight,fg=fg or p['muted'],family=YORUNGE_MONO_FAMILY)
        self.hero=AutoCard(self.body,dict(p,card=p['accent_soft'],line=p['accent']),padding=18);self.hero.pack_configure(pady=(18,12))
        bg=p['accent_soft'];mark=tk.Canvas(self.hero.content,width=56,height=56,bg=bg,highlightthickness=0);mark.pack(side='left',padx=(0,18))
        image=surface(56,56,bg,bg,None,0);ImageDraw.Draw(image).polygon(((28,2),(54,28),(28,54),(2,28)),outline=p['accent'],width=2)
        glyph=icon('refresh',20,p['accent']);image.paste(glyph,(18,18),glyph)
        mark.image=photo(image,mark);mark.create_image(0,0,image=mark.image,anchor='nw')
        info=tk.Frame(self.hero.content,bg=bg);info.pack(side='left',fill='x',expand=True)
        mono(info,'// YENİ SÜRÜM ALGILANDI',fg=p['accent']).pack(anchor='w')
        versions=tk.Frame(info,bg=bg);versions.pack(anchor='w',pady=(6,0))
        mono(versions,VERSION,16,p['muted'],'Bold').pack(side='left')
        mono(versions,' → '+update['version'].lstrip('v'),16,p['text'],'Bold').pack(side='left')
        card=AutoCard(self.body,p);card.brackets=False
        head=tk.Frame(card.content,bg=p['card']);head.pack(fill='x')
        mono(head,'// BU SÜRÜMDE').pack(side='left')
        if update.get('notes_url'):Button(head,'Tüm notlar >',lambda:webbrowser.open(update['notes_url']),palette=p,kind='link').pack(side='right')
        notes=[line.strip().lstrip('#*- ').strip() for line in update.get('notes','').splitlines() if line.strip()][:5]
        for note in notes or ['Sürüm notları alınamadı; tüm sürüm notlarını açabilirsin.']:
            row=tk.Frame(card.content,bg=p['card']);row.pack(fill='x',pady=(8,0))
            mono(row,'+',13,p['accent']).pack(side='left',anchor='n',padx=(0,10))
            item=tk.Label(row,text=note,justify='left',anchor='w',bg=p['card'],fg=p['text'],font=('Inter',text_px(13)),padx=0,pady=0,bd=0)
            item.pack(side='left',fill='x',expand=True);row.bind('<Configure>',lambda event,item=item:item.configure(wraplength=max(1,event.width-30)),add='+')
        order=AutoCard(self.body,p);order.brackets=False;mono(order.content,'// KURULUM SIRASI').pack(anchor='w',pady=(0,6))
        for index,(title,detail) in enumerate((('İndir ve doğrula','SHA-256'),('Duraklat ve kapat','SDM'),('Kur ve yeniden aç',update['version'].lstrip('v'))),1):
            row=tk.Frame(order.content,bg=p['card']);row.pack(fill='x',pady=6);self.step_cards.append(row)
            mono(row,f'{index:02}',12,p['accent'],'Bold').pack(side='left',padx=(0,22))
            mono(row,caption(title)[3:],12,p['text'],'SemiBold').pack(side='left')
            mono(row,detail,11).pack(side='right')
        active=parent.engine.get_active_count()+sum(task.status in ('İndiriliyor','Dönüştürülüyor') for task in parent.video_tasks.values())
        if active:
            warning=AutoCard(self.body,dict(p,card=p['card'],line=p['warning']),padding=12);warning.brackets=False
            mono(warning.content,caption(f'! {active} aktif aktarım duraklatılacak, sonra devam edecek')[3:],11,p['warning'],'SemiBold').pack(anchor='w')
        action(self.actionbar,'Şimdi güncelle',self.accept,p,'primary');action(self.actionbar,'Daha sonra',self.close,p,'secondary')

    def accept(self):self.result=True;self.destroy()


def confirm_update(parent,update):
    window=UpdateDialog(parent,update);window.transient(parent);window.grab_set();parent.wait_window(window);return window.result
