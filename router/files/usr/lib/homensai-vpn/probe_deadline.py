"""One monotonic deadline across connect, TLS and every HTTP stream read."""
import io
import math
import socket
import time

HTTP_SECONDS = 6
# Owner decision 01.11.2026: during a dense confirmation (a channel already suspected by the heartbeat or a
# passive signal) the monitor's HTTPS checks wait at most DENSE_HTTP_SECONDS, so three failed checks of a cut
# channel take about 12 s instead of about 23 s. The failure count, the DNS check and Auto's own confirmation
# probe (native_switch, live_probe.lua) are unchanged.
DENSE_HTTP_SECONDS = 3


def remaining(deadline):
    try:valid=type(deadline) in (int,float) and math.isfinite(deadline)
    except OverflowError:valid=False
    if not valid:raise socket.timeout('invalid probe deadline')
    seconds = deadline-time.monotonic()
    if seconds <= 0:
        raise socket.timeout('probe deadline exceeded')
    return seconds  # the whole probe budget; a slow TCP tunnel is not a failure


class _Reader(io.RawIOBase):
    def __init__(self, sock, deadline):
        self.sock, self.deadline = sock, deadline

    def readable(self):
        return True

    def readinto(self, buffer):
        self.sock.settimeout(remaining(self.deadline))
        count = self.sock.recv_into(buffer)
        remaining(self.deadline)
        return count


class DeadlineSocket:
    """HTTPResponse adapter; checks time below its buffered header/body reader."""
    def __init__(self, sock, deadline):
        self.sock, self.deadline = sock, deadline

    def makefile(self, mode):
        if mode != 'rb':
            raise ValueError('probe stream mode')
        return io.BufferedReader(_Reader(self.sock, self.deadline), buffer_size=4096)
