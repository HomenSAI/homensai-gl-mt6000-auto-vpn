"""One monotonic deadline across connect, TLS and every HTTP stream read."""
import io
import math
import socket
import time

HTTP_SECONDS = 6


def remaining(deadline):
    try:valid=type(deadline) in (int,float) and math.isfinite(deadline)
    except OverflowError:valid=False
    if not valid:raise socket.timeout('invalid probe deadline')
    seconds = deadline-time.monotonic()
    if seconds <= 0:
        raise socket.timeout('probe deadline exceeded')
    return min(3, seconds)


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
