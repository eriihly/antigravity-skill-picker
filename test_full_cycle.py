import webview, threading, time, ctypes

user32 = ctypes.windll.user32
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2

class Api:
    def __init__(self):
        self.w = None
        self._prev_w = 1280
        self._prev_h = 850
        self._is_mini = False

    def enter_mini(self):
        print("enter_mini called")
        self._prev_w = self.w.width
        self._prev_h = self.w.height
        hwnd = self.w.native.Handle.ToInt64()
        dpi = user32.GetDpiForWindow(hwnd) or 96
        scale = dpi / 96.0
        phys_w = int(480 * scale)
        phys_h = int(120 * scale)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, phys_w, phys_h, 0x0002 | 0x0020 | 0x0040)
        self.w.evaluate_js("document.body.classList.add('mini')")
        print("mini set!")
        return True

    def exit_mini(self):
        print("exit_mini called")
        hwnd = self.w.native.Handle.ToInt64()
        dpi = user32.GetDpiForWindow(hwnd) or 96
        scale = dpi / 96.0
        phys_w = int(self._prev_w * scale)
        phys_h = int(self._prev_h * scale)
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, phys_w, phys_h, 0x0002 | 0x0020 | 0x0040)
        self.w.evaluate_js("document.body.classList.remove('mini')")
        print("restored!")
        return True

api = Api()
w = webview.create_window('test', html='<h1 id="h">Hello</h1>', js_api=api, width=1280, height=850, min_size=(320, 90), frameless=True)
api.w = w

def run():
    time.sleep(1)
    api.enter_mini()
    time.sleep(1)
    res = w.evaluate_js("document.body.className")
    print("Class after mini:", res)
    api.exit_mini()
    time.sleep(1)
    res2 = w.evaluate_js("document.body.className")
    print("Class after restore:", res2)
    time.sleep(1)
    w.destroy()

threading.Thread(target=run, daemon=True).start()
webview.start()
