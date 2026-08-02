import ctypes
import sys

MUTEX_NAME = "Local\\ZifyVPN_SingleInstance"


def acquire_single_instance(show_existing=True):
    """Returns True if this is the only instance, False if another is running.

    Uses a named kernel mutex. When another instance exists and show_existing
    is True, tries to raise the other window.
    """
    if sys.platform != "win32":
        return True

    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not mutex:
        return True

    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(mutex)
        if show_existing:
            _raise_existing_window()
        return False
    return True


def _raise_existing_window():
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "Zify client")
        if hwnd:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass
