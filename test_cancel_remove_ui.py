"""Run in a subprocess with a timeout: repeated cancel/remove must not freeze Tk."""
def main():
    import os
    if not os.environ.get('SDM_DATA_DIR'):raise RuntimeError('Use isolated SDM_DATA_DIR')
    from pathlib import Path
    import threading,time
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from unittest.mock import patch
    from gui import MainWindow
    from utils import ensure_config_dir,save_settings
    DATA=b'responsiveness fixture\x00'*200000
    streamed=threading.Event();release_body=threading.Event()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            start,end=map(int,self.headers['Range'].split('=')[1].split('-'))
            try:
                self.send_response(206);self.send_header('Content-Length',str(end-start+1))
                self.send_header('Content-Range',f'bytes {start}-{end}/{len(DATA)}');self.end_headers()
                first_end=min(end+1,start+65536)
                self.wfile.write(DATA[start:first_end]);self.wfile.flush()
                if end>start:
                    # Hold an actual response AFTER sending data. Otherwise a
                    # fast local transfer can finish before the UI's first poll,
                    # so the test never exercises cancellation at all.
                    streamed.set();release_body.wait(3)
                for offset in range(first_end,end+1,65536):
                    self.wfile.write(DATA[offset:min(end+1,offset+65536)]);time.sleep(.02)
            except OSError:pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    app=MainWindow();app.settings.update(auto_open_details=False,completion_popup=False,notifications_enabled=False,
                                      download_dir=str(ensure_config_dir()/'downloads'))
    save_settings(app.settings)
    state={'count':0,'id':None,'removed':False,'heartbeat':0,'max_gap':0,'last':time.monotonic()}
    deadline=time.monotonic()+25
    def heartbeat():
        now=time.monotonic();state['max_gap']=max(state['max_gap'],now-state['last']);state['last']=now
        state['heartbeat']+=1
        # These are the UI reads that deadlocked with worker cancellation in 0.3.1.
        app.engine.get_active_count();app.engine.get_total_speed()
        app.after(25,heartbeat)
    def cycle():
        if time.monotonic()>deadline:return app.quit()
        did=state['id']
        if did is None:
            streamed.clear();release_body.clear()
            name=f'fixture-{state["count"]}.bin'
            state['id']=app.add_download_from_dialog(f'http://127.0.0.1:{server.server_port}/{name}',name,
                                                       str(Path(app.settings['download_dir'])/name))
        elif not state['removed']:
            task=app.engine.get_task(did)
            if task and task.status=='İndiriliyor' and streamed.is_set():
                app.refresh_downloads()
                for item in app.tree.get_children():
                    if int(app.tree.item(item,'values')[0])==did:app.tree.selection_set(item);break
                app.cancel_selected()
                release_body.set()
                app.delete_selected(delete_file=state['count']%2==0)
                state['removed']=True
        elif app.db.get_download(did) is None and did not in app._deleting:
            state['count']+=1;state['id']=None;state['removed']=False
            if state['count']==12:return app.quit()
        app.after(25,cycle)
    try:
        with patch('gui.messagebox.askyesno',return_value=True):
            app.after(25,heartbeat);app.after(25,cycle);app.mainloop()
        if state['count']!=12:
            task=app.engine.get_task(state['id'])
            state['task_status']=getattr(task,'status',None)
            record=app.db.get_download(state['id']) if state['id'] else None
            state['record_status']=record.get('status') if record else None
        assert state['count']==12,state
        assert state['heartbeat']>50,state
        assert state['max_gap']<1.5,state
        print(f'12 live cancel/remove cycles; Tk heartbeat continued; worst delay {state["max_gap"]:.3f}s: OK')
    finally:
        release_body.set()
        app.engine.stop_engine();app.destroy();server.shutdown();server.server_close()


if __name__=='__main__':main()
