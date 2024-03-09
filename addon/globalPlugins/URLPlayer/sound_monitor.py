import os
import sys
import threading


sys.path.append(os.path.dirname(__file__))
from .pycaw.callbacks import AudioSessionEvents
from .pycaw.utils import AudioUtilities
from .pycaw.pycaw import IAudioMeterInformation
sys.path.pop(-1)

import comtypes

from . import psutil


class Callback(AudioSessionEvents):

    def __init__(self, controller, process_info, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller = controller
        self.process_info = process_info

    def on_state_changed(self, new_state, new_state_id):
        if new_state=='Active':
            self.controller.update(self.process_info, 1)
        if new_state=='Inactive':
            self.controller.update(self.process_info, 0)


class SoundMonitor:

    def __init__(self, callback, monitor_type=0, min_peak=1):
        self.callback = callback
        self.monitor_type = monitor_type
        self.min_peak = min_peak/100
        self.active_processes = {}
        self.registered_sessions = {}
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.started = False
        AudioUtilities.GetAllSessions()  # to avoid strange exception in thread

    def start(self):
        with self.lock:
            if self.started:
                return
            self.started = True
            self.wait_previous_thread()
            self.thread = threading.Thread(target=self.loop)
            self.thread.start()

    def stop(self):
        with self.lock:
            if not self.started:
                return
            self.started = False
            self.stop_event.set()

    def wait_previous_thread(self):
        while self.stop_event.is_set():
            pass

    def restart(self):
        self.stop()
        self.start()

    def loop(self):
        while not self.stop_event.is_set():
            try:
                # Here we can get an exception if, for example, there are no audio devices.
                sessions = AudioUtilities.GetAllSessions()
            except comtypes.COMError:
                self.stop_event.wait(10)
                continue
            if self.monitor_type==0:
                for session in sessions:
                    if not session.Process or session.Process.pid in self.registered_sessions:
                        continue
                    try:
                        callback = Callback(self, (session.Process.pid, session.Process.name()))
                    except Exception:
                        continue
                    session.register_notification(callback)
                    self.registered_sessions[session.Process.pid] = session
                    if session.State == 1:
                        self.update(callback.process_info, 1)
            if self.monitor_type==1:
                updated = False
                for session in sessions:
                    if not session.Process:
                        continue
                    try:
                        process_info = [session.Process.pid, session.Process.name()]
                    except Exception:
                        continue
                    peak = session._ctl.QueryInterface(IAudioMeterInformation).GetPeakValue()
                    if peak>self.min_peak and process_info[0] not in self.active_processes:
                        self.active_processes[process_info[0]] = process_info[1]
                    elif peak<=self.min_peak and process_info[0] in self.active_processes:
                        self.active_processes.pop(process_info[0])
                    else:
                        continue
                    updated = True
                if updated:
                    self.callback()
            self.stop_event.wait(0.25)
        if self.monitor_type==0:
            for session in AudioUtilities.GetAllSessions():
                try:
                    session.unregister_notification()
                except Exception:
                    pass
            del self.registered_sessions
        self.stop_event.clear()

    def update(self, process_info, state):
        if state==1 and process_info[0] not in self.active_processes:
            self.active_processes[process_info[0]] = process_info[1]
        elif state==0 and process_info[0] in self.active_processes:
            self.active_processes.pop(process_info[0])
        else:  # Nothing changed
            return
        self.callback()


def get_peak(pid):
    for session in AudioUtilities.GetAllSessions():
        if session.Process and session.Process.pid==pid:
            return session._ctl.QueryInterface(IAudioMeterInformation).GetPeakValue()
