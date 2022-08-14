import config
import wx
import gui
from .config_helpers import to_bool


class URLPlayerSettingsPanel(gui.SettingsPanel):
	title = 'URLPlayer'

	def makeSettings(self, settings_sizer):
		self.config = config.conf['URLPlayer']
		sizer = gui.guiHelper.BoxSizerHelper(self, sizer=settings_sizer)
		self.url_field = sizer.addLabeledControl('URL', wx.TextCtrl)
		self.url_field.SetValue(self.config.get('url', ''))
		self.resume_playback_after_start_checkbox = wx.CheckBox(self, label='Возобновлять воспроизведение после запуска NVDA')
		self.resume_playback_after_start_checkbox.SetValue(to_bool(self.config.get('resume_playback_after_start')))
		sizer.addItem(self.resume_playback_after_start_checkbox)
		self.pause_playback_checkbox = wx.CheckBox(self, label='Приостанавливать воспроизведение, если другое приложение проигрывает звук')
		self.pause_playback_checkbox.SetValue(to_bool(self.config.get('pause_playback', False)))
		sizer.addItem(self.pause_playback_checkbox)
		self.pause_playback_checkbox.Bind(wx.EVT_CHECKBOX, self.on_pause_playback_checkbox)
		self.sound_monitor_type_choice = sizer.addLabeledControl('Способ мониторинга процессов', wx.Choice, choices=['Состояние', 'Пиковая громкость'])
		self.sound_monitor_type_choice.SetSelection(int(self.config.get('sound_monitor_type', 0)))
		self.sound_monitor_type_choice.Bind(wx.EVT_CHOICE, self.on_sound_monitor_type_choice)
		self.sound_monitor_min_peak_spin = sizer.addLabeledControl('Минимальный пик для срабатывания', wx.SpinCtrl, min=0, max=100, initial=int(self.config.get('sound_monitor_min_peak', 0)))
		self.excluded_processes_field = sizer.addLabeledControl('Исключённые процессы через /', wx.TextCtrl)
		self.excluded_processes_field.SetValue(self.config.get('excluded_processes', ''))
		self.ignore_background_processes_checkbox = wx.CheckBox(self, label='Игнорировать звук фоновых процессов')
		self.ignore_background_processes_checkbox.SetValue(to_bool(self.config.get('ignore_background_processes', True)))
		sizer.addItem(self.ignore_background_processes_checkbox)
		self.pause_playback_controls = [self.sound_monitor_type_choice, self.sound_monitor_min_peak_spin, self.excluded_processes_field, self.ignore_background_processes_checkbox]
		self.on_pause_playback_checkbox(None)

	def on_pause_playback_checkbox(self, event):
		if self.pause_playback_checkbox.IsChecked():
			[c.Show() for c in self.pause_playback_controls]
		else:
			[c.Hide() for c in self.pause_playback_controls]
		self.on_sound_monitor_type_choice(None)

	def on_sound_monitor_type_choice(self, event):
		if self.sound_monitor_type_choice.GetSelection()==1 and self.sound_monitor_type_choice.IsShown():
			self.sound_monitor_min_peak_spin.Show()
		else:
			self.sound_monitor_min_peak_spin.Hide()

	def onSave(self):
		# config.conf['URLPlayer'].profiles=[{}]
		# config.conf['URLPlayer'].spec={}
		# config.conf['URLPlayer']._cache={}
		# config.conf['URLPlayer'] = self.config
		self.config['url'] = self.url_field.GetValue()
		self.config['resume_playback_after_start'] = self.resume_playback_after_start_checkbox.GetValue()
		self.config['pause_playback'] = self.pause_playback_checkbox.GetValue()
		self.config['sound_monitor_type'] = self.sound_monitor_type_choice.GetSelection()
		self.config['sound_monitor_min_peak'] = self.sound_monitor_min_peak_spin.GetValue()
		self.config['excluded_processes'] = self.excluded_processes_field.GetValue()
		self.config['ignore_background_processes'] = self.ignore_background_processes_checkbox.GetValue()
		self.on_save_callback()

def add_settings(on_save_callback):
	URLPlayerSettingsPanel.on_save_callback = on_save_callback
	gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(URLPlayerSettingsPanel)


def remove_settings():
	gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(URLPlayerSettingsPanel)


def open_settings():
	wx.CallAfter(gui.mainFrame._popupSettingsDialog, gui.NVDASettingsDialog, URLPlayerSettingsPanel)
