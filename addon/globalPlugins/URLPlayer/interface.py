import addonHandler
import config
import gui
import wx

from .interface_helpers import ConfigBoundSettingsPanel, MultilineTextListConverter, bind_with_config

addonHandler.initTranslation()


class URLPlayerSettingsPanel(ConfigBoundSettingsPanel):
    title = addonHandler.getCodeAddon().manifest['summary']

    def makeSettings(self, settings_sizer):
        self.config = config.conf['URLPlayer']
        sizer = gui.guiHelper.BoxSizerHelper(self, sizer=settings_sizer)
        self.url_field = bind_with_config(sizer.addLabeledControl('URL', wx.TextCtrl), 'url')
        self.resume_playback_after_start_checkbox = bind_with_config(wx.CheckBox(self, label=_('Resume playback after NVDA start')), 'resume_playback_after_start')
        sizer.addItem(self.resume_playback_after_start_checkbox)
        self.pause_playback_checkbox = bind_with_config(wx.CheckBox(self, label=_('Pause playback if another application is playing audio')), 'pause_playback')
        sizer.addItem(self.pause_playback_checkbox)
        self.pause_playback_checkbox.Bind(wx.EVT_CHECKBOX, self.on_pause_playback_checkbox)
        self.sound_monitor_type_choice = bind_with_config(sizer.addLabeledControl(_('Process monitoring method'), wx.Choice, choices=[_('State'), _('Peak volume')]), 'sound_monitor_type')
        self.sound_monitor_type_choice.Bind(wx.EVT_CHOICE, self.on_sound_monitor_type_choice)
        self.sound_monitor_min_peak_spin = bind_with_config(sizer.addLabeledControl(_('Minimum peak for triggering'), wx.SpinCtrl, min=0, max=100), 'sound_monitor_min_peak')
        self.excluded_processes_field = bind_with_config(sizer.addLabeledControl(_('Excluded processes (each process on a separate line)'), wx.TextCtrl, size=(300, 200), style=wx.TE_MULTILINE), 'excluded_processes', converter=MultilineTextListConverter)
        self.excluded_processes_field.Bind(wx.EVT_CHAR_HOOK, self.on_excluded_processes_field_char)
        self.ignore_background_processes_checkbox = bind_with_config(wx.CheckBox(self, label=_('Ignore background processes playing sound')), 'ignore_background_processes')
        sizer.addItem(self.ignore_background_processes_checkbox)
        self.pause_playback_controls = [self.sound_monitor_type_choice, self.sound_monitor_min_peak_spin, self.excluded_processes_field, self.ignore_background_processes_checkbox]
        self.on_pause_playback_checkbox(None)

    def on_excluded_processes_field_char(self, event):
        if event.KeyCode in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            self.excluded_processes_field.WriteText('\n')
        else:
            event.Skip()

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


def add_settings(on_save_callback):
    URLPlayerSettingsPanel.on_save_callback = on_save_callback
    gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(URLPlayerSettingsPanel)


def remove_settings():
    gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(URLPlayerSettingsPanel)


def open_settings():
    wx.CallAfter(gui.mainFrame._popupSettingsDialog, gui.NVDASettingsDialog, URLPlayerSettingsPanel)
