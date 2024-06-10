# Install win10toast with pip
# pip install win10toast

from win10toast import ToastNotifier

# Create a toaster object
toaster = ToastNotifier()

# Show a toast notification
toaster.show_toast("Notification!", "Alert!", threaded=True, icon_path=None, duration=3)
