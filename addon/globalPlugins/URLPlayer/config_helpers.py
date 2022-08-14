CONFIG_DEFAULTS = {
'volume': 5,
'playing': False,
'resume_playback_after_start': False,
'pause_playback': False,
}


def to_bool(value):
	if isinstance(value, bool):
		return value
	return False if value=='False' else True
