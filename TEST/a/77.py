import wmi


def set_brightness(brightness_level):
    brightness_level = min(100, max(0, brightness_level))  # Ensure brightness is between 0 and 100

    c = wmi.WMI(namespace='wmi')
    methods = c.WmiMonitorBrightnessMethods()[0]

    # Set the brightness level (between 0 and 100)
    methods.WmiSetBrightness(brightness_level, 0)


# Example: Set brightness to 50 (adjust as needed)
set_brightness(50)
