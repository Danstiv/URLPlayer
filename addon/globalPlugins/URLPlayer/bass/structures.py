from ctypes import Structure, c_char_p
from ctypes.wintypes import DWORD

class BASS_DEVICEINFO(Structure):
    _fields_ = [
        ("name", c_char_p),
        ("driver", c_char_p),
        ("flags", DWORD),
    ]
