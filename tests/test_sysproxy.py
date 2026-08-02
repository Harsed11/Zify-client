import vpn_configurator.core.sysproxy as sysproxy


def test_sysproxy_disabled_on_non_windows(monkeypatch):
    monkeypatch.setattr(sysproxy, "winreg", None)
    assert sysproxy.set_system_proxy(True) is False
    assert sysproxy.system_proxy_enabled() is False


def test_set_system_proxy_enable(monkeypatch):
    calls = []

    class FakeKey:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class FakeWinreg:
        HKEY_CURRENT_USER = object()
        REG_DWORD = 4
        REG_SZ = 1
        KEY_SET_VALUE = 2
        KEY_READ = 1

        @staticmethod
        def OpenKey(*args):
            calls.append(("open", args))
            return FakeKey()

        @staticmethod
        def SetValueEx(key, name, *args):
            calls.append(("set", name, args[1]))

        @staticmethod
        def CloseKey(key):
            calls.append(("close",))

    class FakeCtypes:
        windll = None

        class _windll:
            class wininet:
                @staticmethod
                def InternetSetOptionW(*args):
                    calls.append(("opt", args[1]))

        windll = _windll

    monkeypatch.setattr(sysproxy, "winreg", FakeWinreg)
    monkeypatch.setattr(sysproxy, "ctypes", FakeCtypes)

    assert sysproxy.set_system_proxy(True) is True
    set_names = [c[1] for c in calls if c[0] == "set"]
    assert set_names == ["ProxyEnable", "ProxyServer", "ProxyOverride"]
    assert calls[0][1][1] == sysproxy.INTERNET_SETTINGS
    opt_values = [c[1] for c in calls if c[0] == "opt"]
    assert sysproxy.INTERNET_OPTION_SETTINGS_CHANGED in opt_values


def test_set_system_proxy_disable(monkeypatch):
    calls = []

    class FakeKey:
        pass

    class FakeWinreg:
        HKEY_CURRENT_USER = object()
        REG_DWORD = 4
        KEY_SET_VALUE = 2

        @staticmethod
        def OpenKey(*args):
            calls.append(("open",))
            return FakeKey()

        @staticmethod
        def SetValueEx(key, name, *args):
            calls.append(("set", name, args[1]))

        @staticmethod
        def CloseKey(key):
            calls.append(("close",))

    class FakeCtypes:
        windll = None

        class _windll:
            class wininet:
                @staticmethod
                def InternetSetOptionW(*args):
                    calls.append(("opt",))

        windll = _windll

    monkeypatch.setattr(sysproxy, "winreg", FakeWinreg)
    monkeypatch.setattr(sysproxy, "ctypes", FakeCtypes)
    assert sysproxy.set_system_proxy(False) is True
    sets = {c[1] for c in calls if c[0] == "set"}
    assert sets == {"ProxyEnable"}


def test_system_proxy_enabled_reads_value(monkeypatch):
    class FakeWinreg:
        HKEY_CURRENT_USER = object()
        KEY_READ = 1
        _value = 1

        @staticmethod
        def OpenKey(*args):
            return FakeWinreg

        @staticmethod
        def QueryValueEx(key, name):
            return (FakeWinreg._value, 4)

        @staticmethod
        def CloseKey(key):
            pass

    monkeypatch.setattr(sysproxy, "winreg", FakeWinreg)
    assert sysproxy.system_proxy_enabled() is True
    FakeWinreg._value = 0
    assert sysproxy.system_proxy_enabled() is False