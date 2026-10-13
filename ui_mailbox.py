"""Worker threads post data here; only the Tk thread touches the UI."""
import queue
import threading
import time


class UIMailbox:
    def __init__(self,owner):
        self.owner=owner
        self.queue=queue.SimpleQueue()
        self.lock=threading.Lock()
        self.latest={}
        self.closed=False
        self.timer=owner.after(25,self.drain)

    def post(self,callback,key=None):
        with self.lock:
            if self.closed:return
            if key is not None:
                existing=key in self.latest
                self.latest[key]=callback
                if existing:return
            self.queue.put((key,callback if key is None else None))

    def drain(self):
        deadline=time.monotonic()+.008
        for _ in range(100):
            if self.closed: return
            try:key,callback=self.queue.get_nowait()
            except queue.Empty:break
            if key is not None:
                with self.lock:callback=self.latest.pop(key,None)
            if callback:
                try:callback()
                except Exception as error:
                    self.owner.report_callback_exception(type(error),error,error.__traceback__)
            if time.monotonic()>=deadline:break
        if not self.closed:self.timer=self.owner.after(25,self.drain)

    def close(self):
        with self.lock:self.closed=True;self.latest.clear()
        self.owner.after_cancel(self.timer)
