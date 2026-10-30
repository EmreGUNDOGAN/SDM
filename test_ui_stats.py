"""İstatistik window in the four designs, from synthetic rows in the runner's fake profile."""
def main():
    import sqlite3
    from datetime import datetime, timedelta
    from pathlib import Path
    from gui import MainWindow
    from stats_window import StatsWindow
    from tools.window_capture import capture_client
    app=MainWindow();app.engine.stop_engine();errors=[]
    app.report_callback_exception=lambda *args:errors.append(args)
    now=datetime.now();stamp=lambda days:(now-timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    rows=[('https://www.youtube.com/watch?v=a','a.mkv','Video',3*1024**3,'Tamamlandı',0),
          ('https://music.youtube.com/watch?v=b','b.mp3','Müzik',8*1024**2,'Tamamlandı',1),
          ('https://github.com/x/releases/c.zip','c.zip','Arşivler',512*1024**2,'Tamamlandı',12),
          ('https://example.org/d.pdf','d.pdf','Belgeler',2*1024**2,'Tamamlandı',45),
          ('https://example.org/e.iso','e.iso','Diğer',0,'Hata',2),
          ('https://example.org/f.iso','f.iso','Diğer',0,'İptal Edildi',3)]
    with sqlite3.connect(str(app.db.db_path)) as db:
        for url,name,category,size,status,days in rows:
            db.execute("INSERT INTO downloads(url,filename,filepath,filesize,downloaded_bytes,status,date_added,date_completed,category) VALUES(?,?,?,?,?,?,?,?,?)",
                       (url,name,str(Path('build')/name),size,size,status,stamp(days),stamp(days) if status=='Tamamlandı' else None,category))
    try:
        for design,mode in (('atlas','light'),('odak','dark'),('pano','light'),('yorunge','dark')):
            app.apply_settings(dict(app.settings,design=design,color_mode=mode));app.update()
            window=app.open_stats();app.update()
            assert app.open_stats() is window,'A second click must reuse the open window'
            values={k:v.get() for k,v in window.values.items()}
            assert values['files']=='3' and values['failed']=='1 / 1' and values['done']=='3 · %60',values
            assert values['total'].startswith('3,5') and values['total'].endswith('GB'),values['total']
            assert window.bars.values[-1]==3*1024**3 and window.bars.values[-13]==512*1024**2 and sum(window.bars.values)==3*1024**3+8*1024**2+512*1024**2
            window.period.set('all');window.refresh();app.update()
            assert window.values['files'].get()=='4' and len(window.kind_rows.winfo_children())==4
            window.period.set('today');window.refresh();app.update();assert window.values['files'].get()=='1'
            window.period.set('30');window.refresh();app.update()
            # Every row's text stays inside its card (no label runs past the edge).
            for box in (window.kind_rows,window.site_rows):
                right=box.winfo_rootx()+box.winfo_width()
                for line in box.winfo_children():
                    for cell in line.winfo_children():
                        assert cell.winfo_rootx()+cell.winfo_width()<=right+1,(design,cell.winfo_width())
            app.update();capture_client(window).save(Path('build')/f'stats-{design}-{mode}.png')
            window.close();app.update()
        assert not errors,errors
        print('İstatistik: four designs, periods, daily bars, kinds and sites, single window: OK')
    finally:
        app.engine.stop_engine();app.destroy()


if __name__=='__main__':main()
