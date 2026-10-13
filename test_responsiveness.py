"""Regression tests for engine callback lock inversion and worker UI dispatch."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from download_engine import DownloadEngine
from ui_mailbox import UIMailbox


class EngineResponsivenessTests(unittest.TestCase):
    def bounded(self,action):
        done=threading.Event();errors=[]
        def work():
            try:action()
            except Exception as error:errors.append(error)
            finally:done.set()
        threading.Thread(target=work,daemon=True).start()
        self.assertTrue(done.wait(2),'An engine callback deadlocked while accessing the engine')
        if errors:raise errors[0]

    def test_pause_cancel_remove_stop_callbacks_can_read_engine(self):
        with tempfile.TemporaryDirectory() as folder:
            for operation in ('pause','cancel','remove','stop'):
                with self.subTest(operation=operation):
                    engine=DownloadEngine()
                    def callback(did,state,error):
                        engine.get_task(did);engine.get_total_speed();engine.get_active_count()
                    task=engine.add_task(1,'https://example.com/file',Path(folder)/operation,
                                         auto_start=False,status_callback=callback)
                    task.status='İndiriliyor'
                    actions={'pause':lambda:engine.pause_task(1),'cancel':lambda:engine.cancel_task(1),
                             'remove':lambda:engine.remove_task(1),'stop':engine.stop_engine}
                    self.bounded(actions[operation])

    def test_dispatch_start_callback_can_cancel_without_starting_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            engine=DownloadEngine();cancelled=threading.Event();network=threading.Event()
            def callback(did,state,error):
                engine.get_task(did)
                if state=='İndiriliyor':engine.cancel_task(did);cancelled.set()
            task=engine.add_task(1,'https://example.com/file',Path(folder)/'test',status_callback=callback)
            task._run=network.set
            engine.start_engine()
            try:
                self.assertTrue(cancelled.wait(2),'Dispatcher called the callback while holding its lock')
                self.assertFalse(network.wait(.1));self.assertEqual(task.status,'İptal Edildi')
            finally:engine.stop_engine()

    def test_worker_posts_never_call_tk_and_progress_is_coalesced(self):
        main=threading.get_ident();calls=[];scheduled=[]
        class Owner:
            def after(self,delay,callback):
                self.assert_main();scheduled.append(callback);return len(scheduled)
            def after_cancel(self,timer):self.assert_main()
            def assert_main(self):
                if threading.get_ident()!=main:raise AssertionError('Worker touched Tk')
            def report_callback_exception(self,*args):raise AssertionError(args)
        mailbox=UIMailbox(Owner())
        def writer():
            for value in range(10000):mailbox.post(lambda v=value:calls.append(v),key='progress')
        worker=threading.Thread(target=writer);worker.start();worker.join(2)
        self.assertFalse(worker.is_alive());self.assertEqual(calls,[])
        mailbox.drain();self.assertEqual(calls,[9999]);mailbox.close()
        mailbox.post(lambda:calls.append('late'));self.assertEqual(calls,[9999])

    def test_remove_callback_waiting_for_ui_does_not_block_ui_engine_read(self):
        with tempfile.TemporaryDirectory() as folder:
            engine=DownloadEngine();waiting=threading.Event();ui_done=threading.Event();removed=threading.Event()
            def callback(did,state,error):
                waiting.set()
                if not ui_done.wait(2):raise AssertionError('UI could not read engine during removal')
            engine.add_task(1,'https://example.com/file',Path(folder)/'file',auto_start=False,status_callback=callback)
            def remove():engine.remove_task(1);removed.set()
            threading.Thread(target=remove,daemon=True).start()
            self.assertTrue(waiting.wait(1))
            def ui_read():engine.get_total_speed();ui_done.set()
            threading.Thread(target=ui_read,daemon=True).start()
            self.assertTrue(ui_done.wait(1),'UI blocked on engine mutex held by removal callback')
            self.assertTrue(removed.wait(1))


if __name__=='__main__':unittest.main()
