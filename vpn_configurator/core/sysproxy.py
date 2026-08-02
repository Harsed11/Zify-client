import sys

if sys.platform == "win32":
    import winreg
    import ctypes
else:
    winreg = None

PROXY_SERVER = "127.0.0.1:10809"
PROXY_OVERRIDE = "<local>"
INTERNET_SETTINGS = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
INTERNET_OPTION_SETTINGS_CHANGED = 39
INTERNET_OPTION_REFRESH = 37


def set_system_proxy(enable):
    """Enable or disable the Windows system proxy (WinINET) pointing at 127.0.0.1:10809."""
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, INTERNET_SETTINGS, 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1 if enable else 0)
        if enable:
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, PROXY_SERVER)
            winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, PROXY_OVERRIDE)
        winreg.CloseKey(key)

        ctypes.windll.wininet.InternetSetOptionW(None, INTERNET_OPTION_SETTINGS_CHANGED, None, 0)
        ctypes.windll.wininet.InternetSetOptionW(None, INTERNET_OPTION_REFRESH, None, 0)
        return True
    except Exception:
        return False


def system_proxy_enabled():
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, INTERNET_SETTINGS, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, "ProxyEnable")
        winreg.CloseKey(key)
        return bool(value)
    except Exception:
        return False
