import math


def media_time_to_str(duration) -> str:
    """
    Convert media time value to hh:mm:ss or mm:ss textual representation.

    :param duration: time value in milliseconds
    :return: str
    """
    duration_s = math.floor(duration / 1000)
    hours = duration_s // 3600
    minutes = duration_s % 3600 // 60
    seconds = duration_s % 3600 % 60
    if not hours:
        text = '{:02d}:{:02d}'.format(minutes, seconds)
    else:
        text = '{:02d}:{:02d}:{:02d}'.format(hours, minutes, seconds)

    return text
