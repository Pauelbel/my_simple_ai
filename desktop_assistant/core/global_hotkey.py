"""Small X11 global hotkey bridge used by the desktop overlay."""
import ctypes
import ctypes.util
import os
import threading
import time

from PySide6.QtCore import QObject, Signal


class GlobalHotkey(QObject):
    activated = Signal()

    def __init__(self, sequence: str = "") -> None:
        super().__init__()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.set_sequence(sequence)

    def set_sequence(self, sequence: str) -> None:
        self.stop()
        sequence = sequence.strip()
        if not sequence or os.environ.get("QT_QPA_PLATFORM") in ("offscreen", "minimal"):
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._listen, args=(sequence,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread is not None:
            self._stop.set()
            self._thread.join(timeout=0.3)
            self._thread = None

    def _listen(self, sequence: str) -> None:
        library = ctypes.util.find_library("X11")
        if not library:
            return
        x11 = ctypes.cdll.LoadLibrary(library)
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        x11.XDefaultRootWindow.restype = ctypes.c_ulong
        x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
        x11.XStringToKeysym.restype = ctypes.c_ulong
        x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x11.XKeysymToKeycode.restype = ctypes.c_uint
        x11.XGrabKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_ulong,
                                 ctypes.c_int, ctypes.c_int, ctypes.c_int]
        x11.XUngrabKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_ulong]
        x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        x11.XPending.argtypes = [ctypes.c_void_p]
        x11.XPending.restype = ctypes.c_int
        x11.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        error_handler_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
        x11.XSetErrorHandler.restype = ctypes.c_void_p
        display = x11.XOpenDisplay(None)
        if not display:
            return
        try:
            parts = [part.strip() for part in sequence.split("+") if part.strip()]
            if not parts:
                return
            names = {"space": "space", "esc": "Escape", "escape": "Escape",
                     "return": "Return", "enter": "Return", "tab": "Tab"}
            key_name = names.get(parts[-1].casefold(), parts[-1])
            keysym = x11.XStringToKeysym(key_name.encode("ascii", errors="ignore"))
            keycode = x11.XKeysymToKeycode(display, keysym)
            if not keycode:
                return
            modifiers = 0
            for part in parts[:-1]:
                modifier = part.casefold()
                if modifier in ("ctrl", "control"): modifiers |= 4
                elif modifier == "shift": modifiers |= 1
                elif modifier in ("alt", "option"): modifiers |= 8
                elif modifier in ("meta", "super", "win"): modifiers |= 64
            root = x11.XDefaultRootWindow(display)
            # Also grab variants with Caps Lock and Num Lock enabled.
            # A conflicting system shortcut raises asynchronous BadAccess.
            # Ignore it while registering instead of letting Xlib abort the app.
            ignore_x_error = error_handler_type(lambda _display, _error: 0)
            previous_handler = x11.XSetErrorHandler(ignore_x_error)
            try:
                for lock_mask in (0, 2, 16, 18):
                    x11.XGrabKey(display, keycode, modifiers | lock_mask, root, True, 1, 1)
                x11.XSync(display, False)
            finally:
                x11.XSetErrorHandler(previous_handler)
            last_activation = 0.0
            event = (ctypes.c_long * 24)()
            while not self._stop.wait(0.015):
                while x11.XPending(display):
                    x11.XNextEvent(display, ctypes.byref(event))
                    # XKeyEvent.type is the first native long; 2 means KeyPress.
                    if event[0] == 2 and time.monotonic() - last_activation > 0.35:
                        last_activation = time.monotonic()
                        self.activated.emit()
        finally:
            x11.XUngrabKey(display, keycode if 'keycode' in locals() else 0, 32768, root if 'root' in locals() else 0)
            x11.XCloseDisplay(display)

    def __del__(self) -> None:
        self.stop()
