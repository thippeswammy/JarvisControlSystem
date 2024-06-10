import wmi


def get_brightness_level():
    brightness = 0
    try:
        w = wmi.WMI(namespace='wmi')
        brightness = w.WmiMonitorBrightness()[0].CurrentBrightness
    except Exception as e:
        print(f"Error: {e}")
    return brightness


# current_brightness = get_brightness_level()
print(f"Current Brightness Level: {get_brightness_level()}")
