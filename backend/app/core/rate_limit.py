"""Process-local admission limits with bounded memory and no persistent client addresses."""

import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock


@dataclass(slots=True)
class Window:
    expires_at: float
    count: int


class WindowLimiter:
    def __init__(self, *, capacity: int = 4096) -> None:
        self.capacity = capacity
        self.windows: OrderedDict[str, Window] = OrderedDict()
        self.lock = Lock()

    def allow(self, key: str, *, maximum: int, seconds: int) -> bool:
        now = time.monotonic()
        with self.lock:
            record = self.windows.get(key)
            if record is None or record.expires_at <= now:
                record = Window(expires_at=now + seconds, count=0)
                self.windows[key] = record
            self.windows.move_to_end(key)
            while len(self.windows) > self.capacity:
                self.windows.popitem(last=False)
            if record.count >= maximum:
                return False
            record.count += 1
            return True
