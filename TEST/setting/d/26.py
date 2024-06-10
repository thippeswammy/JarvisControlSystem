from win10toast import ToastNotifier

toast = ToastNotifier()
toast.show_toast(
    "Notification",
    "Thippeswamy",
    duration=3,
    # icon_path = "icon.ico",
    threaded=True,
)
