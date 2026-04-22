from pycaw.pycaw import AudioUtilities
import inspect
devices = AudioUtilities.GetSpeakers()
print("Has EndpointVolume:", hasattr(devices, "EndpointVolume"))
vol = devices.EndpointVolume
print(dir(vol))
print("Volume:", vol.GetMasterVolumeLevelScalar())
