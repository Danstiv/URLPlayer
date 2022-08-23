import enum
import os
import queue
import sys
from traceback import format_exc
import threading

import addonHandler
import api
import config
import configobj
import globalPluginHandler
import ui
from scriptHandler import script

from . import interface
from . import psutil
from . import sound_monitor
from . import url_player

addonHandler.initTranslation()

config.conf.spec['URLPlayer'] = {
    'volume': 'integer(default=5)',
    'playing': 'boolean(default=false)',
    'resume_playback_after_start': 'boolean(default=false)',
    'url': 'string(default="")',
    'device': 'string(default=None)',
    'pause_playback': 'boolean(default=false)',
    'excluded_processes': 'string_list()',
    'ignore_background_processes': 'boolean(default=false)',
    'sound_monitor_type': 'integer(default=0)',
    'sound_monitor_min_peak': 'integer(default=0)',
}


class Action(enum.IntEnum):
    TERMINATE_QUEUE_MONITOR = enum.auto()
    START_PLAYER = enum.auto()
    STOP_PLAYER = enum.auto()
    START_SOUND_MONITOR = enum.auto()
    STOP_SOUND_MONITOR = enum.auto()
    INITIALIZE_PLAYER = enum.auto()
    INITIALIZE_SOUND_MONITOR = enum.auto()


class URLPlayer(url_player.URLPlayer):

    def notify(self, event):
        if event==url_player.FAILED_TO_CONNECT:
            ui.message(_('Failed to connect to URL stream.'))
        if event==url_player.CONNECTION_LOST:
            ui.message(_('Lost connection to URL stream.'))
        if event==url_player.PLAYBACK_STARTED:
            ui.message(_('URL stream is playing.'))


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = addonHandler.getCodeAddon().manifest['summary']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.actions_queue = queue.Queue()
        self.queue_monitor_thread = threading.Thread(target=self.queue_monitor)
        self.queue_monitor_thread.start()
        self.config = config.conf['URLPlayer']
        self.validate_config(self.config)
        if 'excluded_processes' not in self.config:
            self.config['excluded_processes'] = ['nvda.exe']
        interface.add_settings(self.on_save_callback)
        playing = self.config['playing']
        self.config['playing'] = False
        self.player = None
        self.sound_monitor = None
        self.initialize()
        if not self.initialized:
            return
        if self.config['resume_playback_after_start'] and playing:
            self.config['playing'] = True
            self.start_player()

    def validate_config(self, section):
        '''Tries to get all keys from a section, and recursively from nested sections.
        On validation errors, it removes the incorrect value.
        '''
        for key in list(section):
            try:
                value = section[key]
            except configobj.validate.ValidateError:
                for profile in section.profiles:
                    profile.pop(key, None)
                section._cache.pop(key, None)
            if isinstance(value, config.AggregatedSection):
                self.validate_config(value)

    def start_player(self):
        self.actions_queue.put(Action.START_PLAYER)

    def stop_player(self):
        self.actions_queue.put(Action.STOP_PLAYER)

    def initialize_player(self, *args, **kwargs):
        self.actions_queue.put(Action.INITIALIZE_PLAYER)
        self.actions_queue.put((args, kwargs))

    def start_sound_monitor(self):
        self.actions_queue.put(Action.START_SOUND_MONITOR)

    def stop_sound_monitor(self):
        self.actions_queue.put(Action.STOP_SOUND_MONITOR)

    def initialize_sound_monitor(self, *args, **kwargs):
        self.actions_queue.put(Action.INITIALIZE_SOUND_MONITOR)
        self.actions_queue.put((args, kwargs))

    def initialize(self):
        self.load_devices()
        if self.device_index==None:
            self.initialized = False
            self.initialization_error = _('No output devices found')
            return
        if not self.config['url']:
            self.initialized = False
            self.initialization_error = _('URL not specified')
            return
        if self.player:
            self.stop_player()
        if self.sound_monitor:
            self.stop_sound_monitor()
        self.initialize_player(self.devices[self.device_index][1], self.config['url'], int(self.config['volume']))
        if self.config['pause_playback']:
            self.initialize_sound_monitor(self.active_processes_callback, self.config['sound_monitor_type'], self.config['sound_monitor_min_peak'])
            self.start_sound_monitor()
        if self.config['playing']:
            self.start_player()
        self.initialized = True

    on_save_callback = initialize

    def active_processes_callback(self):
        if not self.config['pause_playback']:
            return
        if self.config['ignore_background_processes']:
            current_process_info = self.get_current_process_info(False)
        active_processes = dict(self.sound_monitor.active_processes)
        active_processes_count = len(active_processes)
        for pid, name in active_processes.items():
            if (name in self.config['excluded_processes']) or (self.config['ignore_background_processes'] and (current_process_info == None or current_process_info[1] != name)):
                active_processes_count -= 1
        if active_processes_count and self.config['playing'] and self.player.started:
            self.stop_player()
        if not active_processes_count and self.config['playing'] and not self.player.started:
            self.start_player()

    def terminate_queue_monitor(self):
        self.actions_queue.put(Action.TERMINATE_QUEUE_MONITOR)

    def queue_monitor(self):
        self.queue_monitor_terminated_event = threading.Event()
        while True:
            item = self.actions_queue.get()
            if item==Action.TERMINATE_QUEUE_MONITOR:
                break
            if item == Action.START_PLAYER:
                self.player.start()
            if item == Action.STOP_PLAYER:
                self.player.stop()
            if item == Action.START_SOUND_MONITOR:
                self.sound_monitor.start()
            if item == Action.STOP_SOUND_MONITOR:
                self.sound_monitor.stop()
            if item == Action.INITIALIZE_PLAYER:
                temp = self.actions_queue.get()
                self.player = URLPlayer(*temp[0], **temp[1])
            if item==Action.INITIALIZE_SOUND_MONITOR:
                temp = self.actions_queue.get()
                self.sound_monitor = sound_monitor.SoundMonitor(*temp[0], **temp[1])
        self.queue_monitor_terminated_event.set()

    def load_devices(self):
        self.devices = url_player.get_devices()
        self.device_index = 0
        for i, device in enumerate(self.devices):
            if device[0]==self.config['device']:
                self.device_index = i
                break

    @script(
        description=_('Start / stop playback'),
        gestures=['kb:nvda+control+shift+space', 'kb:pause'],
    )
    def script_player(self, gesture):
        if not self.initialized:
            ui.message(self.initialization_error)
            return
        if self.config['playing']:
            self.stop_player()
            self.config['playing'] = False
            ui.message(_('Stopped.'))
            return
        self.start_player()
        self.config['playing'] = True
        ui.message(_('Playing.'))

    @script(
        description=_('Increase volume'),
        gesture='kb:nvda+control+shift+upArrow',
    )
    def script_volume_up(self, gesture):
        self.change_volume(1)

    @script(
        description=_('Increase volume by 5%'),
        gesture='kb:nvda+control+shift+pageUp',
    )
    def script_volume_up_5(self, gesture):
        self.change_volume(5)

    @script(
        description=_('Set maximum volume'),
        gesture='kb:nvda+control+shift+home',
    )
    def script_volume_up_max(self, gesture):
        self.change_volume(100)

    @script(
        description=_('Decrease volume'),
        gesture='kb:nvda+control+shift+downArrow',
    )
    def script_volume_down(self, gesture):
        self.change_volume(-1)

    @script(
        description=_('Decrease volume by 5%'),
        gesture='kb:nvda+control+shift+pageDown',
    )
    def script_volume_down_5(self, gesture):
        self.change_volume(-5)

    @script(
        description=_('Set minimum volume'),
        gesture='kb:nvda+control+shift+end',
    )
    def script_volume_down_min(self, gesture):
        self.change_volume(-100)

    def change_volume(self, amount):
        volume = self.config['volume'] + amount
        volume = min(100, max(0, volume))
        self.config['volume'] = volume
        if self.player:
            self.player.set_volume(volume)
        ui.message(str(volume)+'%')

    @script(
        description=_('Refresh device list'),
        gesture='kb:nvda+control+shift+u',
    )
    def script_update_devices(self, gesture):
        self.load_devices()
        ui.message(_('Device list refreshed.'))

    @script(
        description=_('Previous device'),
        gesture='kb:nvda+control+shift+leftArrow',
    )
    def script_previous_device(self, gesture):
        self.change_device(-1)

    @script(
        description=_('Next device'),
        gesture='kb:nvda+control+shift+rightArrow',
    )
    def script_next_device(self, gesture):
        self.change_device(1)

    def change_device(self, direction):
        if not self.devices:
            ui.message(_('Devices not found.'))
            return
        previous_device_index = self.device_index
        self.device_index += direction
        if self.device_index>=len(self.devices):
            self.device_index = len(self.devices)-1
        if self.device_index<0:
            self.device_index = 0
        device_name = self.devices[self.device_index][0]
        if device_name is None:  # Default device
            device_name = _('Default device')
        ui.message(device_name)
        if previous_device_index == self.device_index:
            return
        self.config['device'] = self.devices[self.device_index][0]
        if self.player:
            self.player.set_device(self.devices[self.device_index][1])

    @script(
        description=_('Get track name'),
        gesture='kb:nvda+control+shift+t',
    )
    def script_get_track_name(self, gesture):
        if self.player and self.player.started:
            track_name = self.player.get_track_name()
            if not track_name:
                track_name = _('Unknown track')
            ui.message(track_name)
        else:
            ui.message(_('URL stream is not playing.'))

    def get_current_process_info(self, announce_error=True):
        try:
            process = psutil.Process(api.getFocusObject().appModule.processID)
            return process.pid, process.name()
        except Exception:
            if announce_error:
                ui.message(_('Failed to get process information.'))
            return

    @script(
        description=_('Add current window process to exceptions / remove from exceptions'),
        gesture='kb:nvda+control+shift+e',
    )
    def script_exclude_process(self, gesture):
        info = self.get_current_process_info()
        if not info:
            return
        process_name = info[1]
        if process_name in self.config['excluded_processes']:
            self.config['excluded_processes'].remove(process_name)
            ui.message(_('Process "{process_name}" removed from exceptions.').format(process_name=process_name))
        else:
            self.config['excluded_processes'].append(process_name)
            ui.message(_('Process "{process_name}" added to exceptions.').format(process_name=process_name))

    @script(
        description=_('Get the peak value of the process of the current window'),
        gesture='kb:nvda+control+shift+p',
    )
    def script_get_peak(self, gesture):
        info = self.get_current_process_info()
        if not info:
            return
        try:
            peak = sound_monitor.get_peak(info[0])
            if peak==None:
                ui.message(_('Unable to find audio session.'))
                return
        except Exception:
            ui.message(_('Failed to get peak value.'))
            return
        ui.message(f'{round(peak*100, 3)}%')

    @script(
        description = _('Open addon settings'),
        gesture = 'kb:nvda+control+shift+o',
    )
    def script_open_settings(self, gesture):
        interface.open_settings()

    @script(
        description=_('Enable / disable monitoring of other applications'),
        gesture='kb:nvda+control+shift+m',
    )
    def script_turn_monitoring(self, gesture):
        self.config['pause_playback'] = not self.config['pause_playback']
        ui.message(_('Monitoring enabled') if self.config['pause_playback'] else _('Monitoring disabled.'))
        self.initialize()

    def event_foreground(self, obj, nextHandler):
        if self.config['pause_playback'] and self.config['ignore_background_processes'] and self.sound_monitor.active_processes:
            self.active_processes_callback()
        nextHandler()

    def terminate(self):
        interface.remove_settings()
        if self.sound_monitor:
            self.stop_sound_monitor()
        if self.player:
            self.stop_player()
        self.terminate_queue_monitor()
        self.queue_monitor_terminated_event.wait()
