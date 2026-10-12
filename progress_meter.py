"""Thread-safe time-weighted transfer speed and conservative ETA."""
from collections import deque
import math
import threading
import time


class ProgressMeter:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.Lock()
        self.reset()

    def reset(self, received=0):
        with self.lock:
            now = self.clock()
            self.samples = deque([(now, received)])
            self.started = now
            self.speed = 0.0
            self.eta = None
            self.last_update = now

    def update(self, received, total):
        with self.lock:
            now = self.clock()
            elapsed = now - self.last_update
            if elapsed < 1.0:
                return self.speed, self.eta
            if received < self.samples[-1][1]:
                self.samples = deque([(now, received)])
                self.started = now
                self.speed = 0.0
                self.eta = None
                self.last_update = now
                return self.speed, self.eta
            self.samples.append((now, received))
            while len(self.samples) > 2 and now - self.samples[1][0] >= 8:
                self.samples.popleft()
            span = now - self.samples[0][0]
            rate = max(0, received - self.samples[0][1]) / span if span else 0
            alpha = 1 - math.exp(-elapsed / 3)
            self.speed = rate if not self.speed else self.speed + alpha * (rate - self.speed)
            self.eta = (max(0, total - received) / self.speed
                        if total > 0 and self.speed > 1 and now - self.started >= 3 else None)
            self.last_update = now
            return self.speed, self.eta
