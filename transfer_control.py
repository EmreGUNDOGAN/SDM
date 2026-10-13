"""One global rate limiter shared by direct and video transfers."""
import threading
import time


class TransferLimiter:
    def __init__(self):
        self.lock = threading.Lock()
        self.rate = 0
        self.next_time = time.monotonic()

    def configure(self, kbs):
        with self.lock:
            self.rate = max(0, int(kbs)) * 1024
            self.next_time = time.monotonic()

    def consume(self, size, stopped=lambda: False):
        with self.lock:
            if not self.rate:
                return
            now = time.monotonic()
            self.next_time = max(now, self.next_time) + size / self.rate
            deadline = self.next_time
        while not stopped():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(.1, remaining))


GLOBAL_LIMITER = TransferLimiter()
