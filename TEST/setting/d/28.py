import tkinter as tk

from plyer import notification

root = tk.Tk()

tk.Label(root, text='NOTIFICATION DEVELOPER').grid(row=0, column=0)
tk.Label(root, text='Notification Title:').grid(row=3, column=0)
tk.Label(root, text='Notification Message').grid(row=4, column=0)
tk.Label(root, text='Seconds for which it appears').grid(row=5, column=0)

t1 = tk.Entry(root)
t1.grid(row=3, column=1)

m = tk.Entry(root)
m.grid(row=4, column=1)

tm = tk.Entry(root)
tm.grid(row=5, column=1)


def strt():
    a = int(tm.get())
    notification.notify(
        title=t1.get(),
        message=m.get(),
        timeout=a
    )


tk.Button(root, text='START NOTIFICATION', command=strt).grid(row=6, column=0)

root.mainloop()
