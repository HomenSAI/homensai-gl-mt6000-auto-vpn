"""Refresh libc timezone on full and reduced OpenWrt Python builds."""
import time


def refresh_timezone():
    native=getattr(time,'tzset',None)
    if callable(native):
        native()
    else:
        import ctypes
        libc=ctypes.CDLL(None)
        libc.tzset.argtypes=[]
        libc.tzset.restype=None
        libc.tzset()
