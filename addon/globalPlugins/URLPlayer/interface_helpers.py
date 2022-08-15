import gui
import wx

DEFAULT_CONVERTERS_MAP = {}


def converter(*classes):
    def decorator(cls):
        for key_cls in classes:
            if key_cls in DEFAULT_CONVERTERS_MAP:
                raise ValueError(f'Converter for {key_cls} already registered')
            DEFAULT_CONVERTERS_MAP[key_cls] = cls
        return cls
    return decorator


class BaseConverter:

    def __init__(self, control):
        self.control = control


@converter(wx.CheckBox)
class CheckBoxConverter(BaseConverter):

    def to_control(self, value):
        self.control.SetValue(value)

    def to_config(self):
        return self.control.IsChecked()


@converter(wx.TextCtrl, wx.SpinCtrl)
class TextCtrlConverter(BaseConverter):

    def to_control(self, value):
        self.control.SetValue(value)

    def to_config(self):
        return self.control.GetValue()


class MultilineTextListConverter(BaseConverter):

    def to_control(self, value):
        self.control.SetValue('\n'.join(value))

    def to_config(self):
        return self.control.GetValue().replace('\r', '').split('\n')


@converter(wx.Choice)
class ChoiceConverter(BaseConverter):

    def to_control(self, value):
        self.control.SetSelection(value)

    def to_config(self):
        return self.control.GetSelection()


def bind_with_config(control, config_key, converter=None):
    if converter is None:
        if control.__class__ not in DEFAULT_CONVERTERS_MAP:
            for k, v in DEFAULT_CONVERTERS_MAP.items():
                if isinstance(control, k):
                    converter = v
                    break
        else:
            converter = DEFAULT_CONVERTERS_MAP[control.__class__]
    if converter is None:
        raise ValueError(f'Converter for {control.__class__.__name__} control class is not registered')
    control.converter = converter(control)
    control.config_key = config_key
    config = None
    config_control = control
    while config_control:
        if hasattr(config_control, 'config'):
            config = config_control.config
            break
        config_control = config_control.Parent
    if not config:
        raise ValueError('Config attribute not found on no parent element')
    control.converter.to_control(config[config_key])
    return control


class ConfigBoundSettingsPanel(gui.SettingsPanel):

    def iter_controls(self, initial_control=None):
        if initial_control is None:
            initial_control = self
        for c in initial_control.Children:
            yield c
            yield from self.iter_controls(c)

    def onSave(self):
        for control in self.iter_controls():
            if not hasattr(control, 'config_key'):
                continue
            self.config[control.config_key] = control.converter.to_config()
        self.on_save_callback()
