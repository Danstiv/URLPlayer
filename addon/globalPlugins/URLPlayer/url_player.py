from ctypes import c_char_p
from itertools import count
import locale
import threading
try:
    from .pybass import *
except ImportError:
    from pybass import *
from traceback import format_exc

DEBUG = False
ENCODING = locale.getpreferredencoding(False)
DP = DOWNLOADPROC(lambda *args: 0)
FAILED_TO_CONNECT = 0
PLAYBACK_STARTED = 1
CONNECTION_LOST = 2

stop_event = threading.Event()


def debug(message):
    if not DEBUG:
        return
    print(message)


class URLPlayer:

    def __init__(self, device, url, volume):
        debug('init called')
        self.device = device
        self.url = url
        self.volume = volume
        self.stream = None
        self.started = False
        self.lock = threading.Lock()
        debug('end init')

    def start(self):
        debug('start called')
        with self.lock:
            if self.started:
                debug('already started')
                return
            self.started = True
            debug('waiting previous thread to stop')
            self.wait_previous_thread()
            debug('stopped. Initializing thread.')
            self.thread = threading.Thread(target=self.loop)
            debug('starting thread.')
            self.thread.start()
            debug('end start')

    def stop(self):
        debug('stop called')
        with self.lock:
            if not self.started:
                debug('already stopped')
                return
            self.started = False
            debug(f'setting stop event. Now {stop_event.is_set()}')
            stop_event.set()
            debug(f'Set. Now {stop_event.is_set()}')
        debug('end stop')

    def wait_previous_thread(self):
        debug('wait previous thread called')
        while stop_event.is_set():
            pass
        debug('end wait previous thread')

    def restart(self):
        debug('restart called')
        self.stop()
        self.start()
        debug('end restart')

    def notify(self, event):
        pass

    def loop(self):
        debug('loop called')
        status = 0
        debug('trying to initialize bass')
        if not self.initialize():
            debug('failed to initialize bass.')
            status = 1
            self.notify(FAILED_TO_CONNECT)
        debug('entering loop.')
        while not stop_event.is_set():
            debug('start itiration')
            if status==0:
                debug('status==0')
                if not self.stream:
                    debug('not self.stream, somethin broke. Exiting loop.')
                    break
                if bass_call(BASS_ChannelIsActive, self.stream, zero_is_error=False)==BASS_ACTIVE_PLAYING:
                    debug(f'active playing. Waiting event 1 s. Event state {stop_event.is_set()}')
                    stop_event.wait(1)
                    debug(f'event.wait returned. Event state {stop_event.is_set()}. Next iteration.')
                    continue
                else:
                    debug('Not active playing.')
                    status = 1
                    debug('Calling free.')
                    self.free()
                    self.notify(CONNECTION_LOST)
            debug('Trying to initialize bass from loop.')
            if not self.initialize():
                debug(f'Failed to initialize bass from loop. Waiting event 3 s. Event state {stop_event.is_set()}')
                stop_event.wait(3)
                debug(f'event.wait returned. Event state {stop_event.is_set()}. Next iteration.')
                continue
            debug('Initialized from loop.')
            status = 0
            self.notify(PLAYBACK_STARTED)
            debug('End itiration')
        debug('Loop stopped. Calling free.')
        self.free()
        debug(f'clearing event. Now {stop_event.is_set()}')
        stop_event.clear()
        debug('end loop')


    def set_volume(self, volume):
        debug('set volume called')
        self.volume = volume
        if self.stream:
            debug('self.stream is True. Calling bass function to apply volume.')
            bass_call(BASS_ChannelSetAttribute, self.stream, BASS_ATTRIB_VOL, volume/100)
        debug('end set volume')

    def set_device(self, device):
        debug('set device called')
        self.device = device
        if self.started:
            debug('self.started is True. Restarting bass to apply changes.')
            self.restart()
        debug('end set device')

    def initialize(self):
        debug('initialize called.')
        try:
            debug('Calling bass init function.')
            bass_call(BASS_Init, self.device, 44100, 0, 0, None)
            debug('bass initialized. Calling bass stream create url.')
            self.stream=bass_call(BASS_StreamCreateURL, self.url.encode(), 0, 0, DP, None)
            debug('Stream created. Applying volume to a stream.')
            self.set_volume(self.volume)
            debug('volume applied. Calling bass channel play.')
            bass_call(BASS_ChannelPlay, self.stream, False)
            debug('channel play called. Returning True')
            return True
        except Exception:
            debug(f'Exception\n{format_exc()}')
            debug('calling free')
            self.free()
            debug('returning false')
            return False

    def free(self):
        debug('free called. Resetting self.stream to None.')
        self.stream = None
        debug('self.stream reset. Calling bass free.')
        BASS_Free()
        debug('bass free called.')
        debug('end free')

    def __del__(self):
        debug('__del__ called. Calling self.free')
        self.free()
        debug('end __del__')

    def get_track_name(self):
        debug('get trackname called.')
        track_name = ''
        if self.stream:
            debug('self.stream is True. Trying to get track name.')
            try:
                debug('Calling bass channel get tag.')
                data = c_char_p(bass_call(BASS_ChannelGetTags, self.stream, BASS_TAG_META)).value
                track_name = data[13:-2].decode()
                debug('track name received.')
            except Exception:
                debug(f'Exception\n{format_exc()}')
        debug('Returning track name')
        return track_name


def get_devices():
    debug('get devices called.')
    devices = []
    device_structure = BASS_DEVICEINFO()
    debug('Entering loop.')
    for device in count(start=1):
        debug(f'Trying get device {device}.')
        try:
            debug('calling bass get device info')
            bass_call(BASS_GetDeviceInfo, device, device_structure)
            debug('called bass get device info')
        except BassError as exc:
            debug(f'exception\n{format_exc()}')
            if exc.code != 23:
                debug(f'code not 23. reraising')
                raise
            debug('exiting loop.')
            break
        if not BASS_DEVICE_ENABLED&device_structure.flags:
            debug('device disabled. Skipping')
            continue
        debug('Appending device.')
        devices.append([device_structure.name.decode(ENCODING), device])
    if devices:
        debug('Devices found. Adding default device.')
        devices.insert(0, [None, -1])
    debug(f'Returning {len(devices)} devices.')
    return devices


class BassError(Exception):
    def __init__(self, code):
        self.code = code
        self.description = get_error_description(code)

    def __str__(self):
        return f'Bass error {self.code}, {self.description}'
    __repr__ = __str__


def bass_call(function, *args, zero_is_error=True):
    res = function(*args)
    if (zero_is_error and res == 0) or res == -1:
        code = BASS_ErrorGetCode()
        raise BassError(code)
    return res
