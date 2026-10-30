# HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
"""Light rpcd client for the read-only page polls; run as `python3 -I -S status_client.py <method>`.

It imports only os, sys, time and the C module _socket (the socket.py wrapper would load enum and
selectors and double the start-up cost), never the application: with -I the script directory is not
even on sys.path. It asks the monitor's status socket for the finished answer. When the socket is
missing, refuses, times out, answers FALLBACK or sends anything unexpected, it runs agent.py exactly as
the plugin always did, with the same request bytes on stdin, so every error code stays the same.
"""
import _socket
import os
import sys
import time

SOCKET = '/var/run/homensai-vpn/status.sock'
PYTHON = '/usr/bin/python3'
AGENT = '/usr/lib/homensai-vpn/agent.py'
METHODS = ('status', 'events', 'history', 'auto_live')
REQUEST_LIMIT = 65537            # the same read limit as agent.rpc
REPLY_LIMIT = 8 * 1024 * 1024
TIMEOUT = 10.0                   # the server gives up after 8 s; agent.py still fits rpcd's 30 s


def ask(method, request, path=SOCKET, timeout=TIMEOUT):
    """The served JSON line, or None when agent.py must answer."""
    if method not in METHODS:
        return None
    deadline = time.monotonic() + timeout
    chunks, size = [], 0
    try:
        connection = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
    except OSError:
        return None
    try:
        connection.settimeout(min(2.0, timeout))
        connection.connect(path)
        connection.settimeout(timeout)
        connection.sendall(method.encode('ascii') + b'\n' + request)
        connection.shutdown(_socket.SHUT_WR)
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return None
            connection.settimeout(left)
            chunk = connection.recv(262144)
            if not chunk:
                break
            size += len(chunk)
            if size > REPLY_LIMIT:
                return None
            chunks.append(chunk)
    except OSError:
        return None
    finally:
        connection.close()
    reply = b''.join(chunks)
    if not reply.startswith(b'OK\n{') or not reply.endswith(b'}\n'):
        return None
    return reply[3:]


def fallback(arguments, request, python=PYTHON, agent=AGENT):
    """Replace this process by agent.py with the request bytes as its stdin."""
    argv = [python, agent] + list(arguments)
    try:
        descriptor = os.memfd_create('homensai-rpc-request', 0)
        try:
            view = memoryview(request)
            while view:
                view = view[os.write(descriptor, view):]
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.dup2(descriptor, 0)
        finally:
            os.close(descriptor)
        os.execv(python, argv)
    except (AttributeError, OSError):
        pass
    import subprocess
    return subprocess.run(argv, input=request).returncode


def main(argv=None, stdin=None, stdout=None, path=SOCKET, python=PYTHON, agent=AGENT):
    argv = sys.argv[1:] if argv is None else list(argv)
    stdin = sys.stdin.buffer if stdin is None else stdin
    stdout = sys.stdout.buffer if stdout is None else stdout
    try:
        request = stdin.read(REQUEST_LIMIT) or b''
    except (OSError, ValueError):
        request = b''
    method = argv[0] if len(argv) == 1 else None
    body = ask(method, request, path) if method in METHODS else None
    if body is None:
        return fallback(['call'] + argv, request, python, agent)
    try:
        stdout.write(body)
        stdout.flush()
    except (OSError, ValueError):
        pass                     # rpcd went away; nothing can be repeated safely
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
