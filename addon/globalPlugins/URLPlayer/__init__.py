import globalPluginHandler
import ui
import config
from scriptHandler import script
import api
import sys
import os
import queue
import threading
from traceback import format_exc
sys.path.append(os.path.dirname(__file__))
from . import interface
from . import url_player
from .config_helpers import CONFIG_DEFAULTS, to_bool
from . import sound_monitor
from . import psutil
del sys.path[-1]


class URLPlayer(url_player.URLPlayer):

	def notify(self, event):
		if event==url_player.FAILED_TO_CONNECT:
			ui.message('Не удалось подключиться к URL-потоку.')
		if event==url_player.CONNECTION_LOST:
			ui.message('Потеряно соединение с URL-потоком.')
		if event==url_player.PLAYBACK_STARTED:
			ui.message('URL-поток воспроизводится.')


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = 'URLPlayer'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.actions_queue = queue.Queue()
		self.queue_monitor_thread = threading.Thread(target=self.queue_monitor)
		self.queue_monitor_thread.start()
		if 'URLPlayer' not in config.conf:
			config.conf['URLPlayer'] = CONFIG_DEFAULTS
		self.config = config.conf['URLPlayer']
		interface.add_settings(self.on_save_callback)
		playing = to_bool(self.config['playing'])
		self.config['playing'] = False
		self.player = None
		self.sound_monitor = None
		self.sound_monitor_active_processes = []
		self.initialize()
		if not self.initialized:
			return
		if to_bool(self.config['resume_playback_after_start']) and playing:
			self.config['playing'] = True
			self.start_player()

	def start_player(self):
		self.actions_queue.put(1)

	def stop_player(self):
		self.actions_queue.put(2)

	def initialize_player(self, *args, **kwargs):
		self.actions_queue.put(5)
		self.actions_queue.put((args, kwargs))

	def start_sound_monitor(self):
		self.actions_queue.put(3)

	def stop_sound_monitor(self):
		self.actions_queue.put(4)

	def initialize_sound_monitor(self, *args, **kwargs):
		self.actions_queue.put(6)
		self.actions_queue.put((args, kwargs))

	def initialize(self):
		self.load_devices()
		if self.device_index==None:
			self.initialized = False
			self.initialization_error = 'Устройства вывода не найдены'
			return
		if 'url' not in self.config or not self.config['url']:
			self.initialized = False
			self.initialization_error = 'URL не указан'
			return
		if self.player:
			self.stop_player()
		if self.sound_monitor:
			self.stop_sound_monitor()
		self.sound_monitor_active_processes = []
		self.initialize_player(self.devices[self.device_index][1], self.config['url'], int(self.config['volume']))
		if to_bool(self.config.get('pause_playback', False)):
			self.initialize_sound_monitor(self.active_processes_callback, int(self.config.get('sound_monitor_type', 0)), int(self.config.get('sound_monitor_min_peak', 0)))
			self.start_sound_monitor()
		if to_bool(self.config['playing']):
			self.start_player()
		self.initialized = True

	on_save_callback = initialize

	def print(self, message):
		self.actions_queue.put(7)
		self.actions_queue.put(message)

	def active_processes_callback(self, processes):
		if not to_bool(self.config['pause_playback']):
			return
		self.sound_monitor_active_processes = dict(processes)
		excluded_processes = [i for i in self.config.get('excluded_processes', '').split('/') if i]
		excluded_processes.append('nvda.exe')
		ignore = to_bool(self.config.get('ignore_background_processes', True))
		if ignore:
			current_process_info = self.get_current_process_info(False)
		for pid, name in list(processes.items()):
			if (name in excluded_processes) or (ignore and (current_process_info==None or current_process_info[1]!=name)):
				processes.pop(pid)
				continue
		if processes and to_bool(self.config['playing']) and self.player.started:
			self.stop_player()
		if not processes and to_bool(self.config['playing']) and not self.player.started:
			self.start_player()

	def terminate_queue_monitor(self):
		self.actions_queue.put(0)

	def queue_monitor(self):
		self.queue_monitor_terminated_event = threading.Event()
		while True:
			item = self.actions_queue.get()
			if item==0:
				break
			if item==1:
				self.player.start()
			if item==2:
				self.player.stop()
			if item==3:
				self.sound_monitor.start()
			if item==4:
				self.sound_monitor.stop()
			if item==5:
				temp = self.actions_queue.get()
				self.player = URLPlayer(*temp[0], **temp[1])
			if item==6:
				temp = self.actions_queue.get()
				self.sound_monitor = sound_monitor.SoundMonitor(*temp[0], **temp[1])
			if item==7:
				print(self.actions_queue.get())
		self.queue_monitor_terminated_event.set()

	def load_devices(self):
		self.devices = url_player.get_devices()
		self.device_index = None
		if 'device' in self.config:
			for i, device in enumerate(self.devices):
				if device[0]==self.config['device']:
					self.device_index = i
					break
		if self.device_index==None and self.devices:
			self.device_index = 0

	@script(
		description = 'Запуск / остановка воспроизведения',
		gestures = ['kb:nvda+control+shift+space', 'kb:pause'],
	)
	def script_player(self, gesture):
		if not self.initialized:
			ui.message(self.initialization_error)
			return
		if to_bool(self.config['playing']):
			self.stop_player()
			self.config['playing'] = False
			ui.message('Остановлено.')
			return
		self.start_player()
		self.config['playing'] = True
		ui.message('Воспроизводится')

	@script(
		description = 'Увеличить громкость',
		gesture = 'kb:nvda+control+shift+upArrow',
	)
	def script_volume_up(self, gesture):
		self.change_volume(1)

	@script(
		description = 'Увеличить громкость на 5%',
		gesture = 'kb:nvda+control+shift+pageUp',
	)
	def script_volume_up_5(self, gesture):
		self.change_volume(5)

	@script(
		description = 'Установить максимальную громкость',
		gesture = 'kb:nvda+control+shift+home',
	)
	def script_volume_up_max(self, gesture):
		self.change_volume(100)

	@script(
		description = 'Уменьшить громкость',
		gesture = 'kb:nvda+control+shift+downArrow',
	)
	def script_volume_down(self, gesture):
		self.change_volume(-1)

	@script(
		description = 'Уменьшить громкость на 5%',
		gesture = 'kb:nvda+control+shift+pageDown',
	)
	def script_volume_down_5(self, gesture):
		self.change_volume(-5)

	@script(
		description = 'Установить минимальную громкость',
		gesture = 'kb:nvda+control+shift+end',
	)
	def script_volume_down_min(self, gesture):
		self.change_volume(-100)

	def change_volume(self, amount):
		volume = int(self.config['volume'])+amount
		volume = min(100, max(0, volume))
		self.config['volume'] = volume
		self.player.set_volume(volume)
		ui.message(str(volume)+'%')

	@script(
		description = 'Обновить список устройств',
		gesture = 'kb:nvda+control+shift+u',
	)
	def script_update_devices(self, gesture):
		self.load_devices()
		ui.message('Устройства обновлены.')

	@script(
		description = 'Предыдущее устройство',
		gesture = 'kb:nvda+control+shift+leftArrow',
	)
	def script_previous_device(self, gesture):
		self.change_device(-1)

	@script(
		description = 'Следующее устройство',
		gesture = 'kb:nvda+control+shift+rightArrow',
	)
	def script_next_device(self, gesture):
		self.change_device(1)

	def change_device(self, direction):
		if not self.devices:
			ui.message('Устройства не найдены.')
			return
		previous_device_index = self.device_index
		self.device_index += direction
		if self.device_index>=len(self.devices):
			self.device_index = len(self.devices)-1
		if self.device_index<0:
			self.device_index = 0
		ui.message(self.devices[self.device_index][0])
		if previous_device_index == self.device_index:
			return
		self.config['device'] = self.devices[self.device_index][0]
		self.player.set_device(self.devices[self.device_index][1])

	@script(
		description = 'Узнать название трека',
		gesture = 'kb:nvda+control+shift+t',
	)
	def script_get_track_name(self, gesture):
		if to_bool(self.config['playing']):
			ui.message(self.player.get_track_name())
		else:
			ui.message('URL-поток не воспроизводится.')

	def get_current_process_info(self, announce_error=True):
		try:
			process = psutil.Process(api.getFocusObject().appModule.processID)
			return process.pid, process.name()
		except Exception:
			if announce_error:
				ui.message('Не удалось получить информацию о процессе.')
			return

	@script(
		description = 'Добавить процесс текущего окна в исключения / убрать из исключений',
		gesture = 'kb:nvda+control+shift+e',
	)
	def script_exclude_process(self, gesture):
		info = self.get_current_process_info()
		if not info:
			return
		process_name = info[1]
		excluded_processes = [i for i in self.config.get('excluded_processes', '').split('/') if i]
		if process_name in excluded_processes:
			excluded_processes.remove(process_name)
			ui.message(f'Процесс "{process_name}" удалён из исключений.')
		else:
			excluded_processes.append(process_name)
			ui.message(f'Процесс "{process_name}" добавлен в исключения.')
		self.config['excluded_processes'] = '/'.join(excluded_processes)

	@script(
		description = 'Узнать пиковое значение процесса текущего окна',
		gesture = 'kb:nvda+control+shift+p',
	)
	def script_get_peak(self, gesture):
		info = self.get_current_process_info()
		if not info:
			return
		try:
			peak = sound_monitor.get_peak(info[0])
			if peak==None:
				ui.message('Не удалось найти сессию.')
				return
		except Exception:
			ui.message('Не удалось получить пиковое значение.')
			return
		ui.message(f'{round(peak*100, 3)}%')

	@script(
		description = 'Открыть настройки дополнения',
		gesture = 'kb:nvda+control+shift+o',
	)
	def script_open_settings(self, gesture):
		interface.open_settings()

	@script(
		description = 'Включить / выключить мониторинг других приложений',
		gesture = 'kb:nvda+control+shift+m',
	)
	def script_turn_monitoring(self, gesture):
		self.config['pause_playback'] = not to_bool(self.config['pause_playback'])
		ui.message('Мониторинг включён' if to_bool(self.config['pause_playback']) else 'Мониторинг выключен')
		self.initialize()

	def event_foreground(self, obj, nextHandler):
		if self.sound_monitor_active_processes:
			self.active_processes_callback(self.sound_monitor_active_processes)
		nextHandler()

	def terminate(self):
		interface.remove_settings()
		if self.sound_monitor:
			self.stop_sound_monitor()
		if self.player:
			self.stop_player()
		self.terminate_queue_monitor()
		self.queue_monitor_terminated_event.wait()
