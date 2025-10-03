from ctypes import CDLL, c_bool, c_int, c_void_p, c_char_p, c_float, POINTER
from ctypes.wintypes import DWORD, HWND
from pathlib import Path

from . import constants
from .structures import BASS_DEVICEINFO

_package_root = Path(__file__).parent
_bass_path = _package_root/'bass.dll'
bass = CDLL(_bass_path)

HSTREAM = DWORD

_CHECK_CODE_ALWAYS = object()

_functions = {
    "BASS_ErrorGetCode": (c_int, lambda r: True),
    "BASS_Init": (c_bool, lambda r: r, c_int, DWORD, DWORD, HWND, c_void_p),
    "BASS_Free": (c_bool, lambda r: r),
    "BASS_GetDeviceInfo": (c_bool, lambda r: r, DWORD, POINTER(BASS_DEVICEINFO)),
    "BASS_SetConfig": (c_bool, lambda r: r, DWORD, DWORD),
    "BASS_StreamCreateURL": (HSTREAM, lambda r: r != 0, c_char_p, DWORD, DWORD, c_void_p, c_void_p),
    "BASS_ChannelSetAttribute": (HSTREAM, lambda r: r != 0, c_char_p, DWORD, DWORD, c_void_p, c_void_p),
    "BASS_ChannelIsActive": (DWORD, lambda r: _CHECK_CODE_ALWAYS, DWORD),
    "BASS_ChannelSetAttribute": (c_bool, lambda r: r, DWORD, DWORD, c_float),
    "BASS_ChannelPlay": (c_bool, lambda r: r, DWORD, c_bool),
    "BASS_ChannelGetTags": (c_char_p, lambda r: r is not None, DWORD, DWORD),
}


class BassError(Exception):
    def __init__(self, code):
        self.code = code

    def __repr__(self):
        return f'BassError: {self.code}'


def errcheck(result, func, arguments):
    if (check_result := _functions[func.__name__][1](result)) and check_result is not _CHECK_CODE_ALWAYS:
        return result
    error_code = bass.BASS_ErrorGetCode()
    if check_result is not _CHECK_CODE_ALWAYS or error_code != constants.BASS_OK:
        raise BassError(error_code)
    return result


for func_name, (restype, success_predicate, *argtypes) in _functions.items():
    func = getattr(bass, func_name)
    func.restype = restype
    func.argtypes = argtypes
    func.errcheck = errcheck
