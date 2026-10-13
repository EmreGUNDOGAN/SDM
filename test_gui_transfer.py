"""Explicit integration script; never runs on unittest discovery."""

def main():
    """Check dispatcher callbacks and completion UI against a local HTTP fixture."""
    import os
    if not os.environ.get('SDM_DATA_DIR'):raise RuntimeError('Set an isolated SDM_DATA_DIR first')
    import threading
    import time
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from pathlib import Path
    from gui import MainWindow
    from utils import ensure_config_dir,save_settings
    from app_dialogs import CompletionDialog

    DATA=b'GUI transfer test\x00'*100000
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            start,end=map(int,self.headers['Range'].split('=')[1].split('-'))
            self.send_response(206);self.send_header('Content-Length',str(end-start+1))
            self.send_header('Content-Range',f'bytes {start}-{end}/{len(DATA)}');self.end_headers()
            self.wfile.write(DATA[start:end+1])
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    app=MainWindow();app.settings['notifications_enabled']=False;app.settings['completion_popup']=True
    app.settings['auto_open_details']=True;app.settings['download_dir']=str(ensure_config_dir()/'downloads');save_settings(app.settings)
    target=Path(app.settings['download_dir'])/'fixture.bin'
    try:
        did=app.add_download_from_dialog(f'http://127.0.0.1:{server.server_port}/fixture.bin','fixture.bin',str(target))
        deadline=time.monotonic()+15
        state={'record':None,'done':False}
        def poll():
            record=app.db.get_download(did)
            state['record']=record
            if record['status']=='Tamamlandı':
                state['done']=True
                app.after(300,app.quit)
            elif time.monotonic()>=deadline:app.quit()
            else:app.after(30,poll)
        app.after(30,poll)
        app.mainloop()
        assert state['done'],state['record']
        assert target.read_bytes()==DATA
        assert any(isinstance(child,CompletionDialog) for child in app.winfo_children())
        assert did in app.detail_windows
        print('Real dispatcher callbacks, exact parallel download, automatic detail + completion: OK')
    finally:
        app.engine.stop_engine();app.destroy();server.shutdown();server.server_close()


if __name__ == "__main__":
    main()
