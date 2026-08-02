import atexit
import subprocess
import sys

RULE_NAME = "Zify client Kill Switch"
OLD_RULE_NAME = "Zify VPN Kill Switch"


def _run_netsh(args):
    if sys.platform != "win32":
        return False
    try:
        r = subprocess.run(
            ["netsh", "advfirewall"] + args,
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return r.returncode == 0
    except Exception:
        return False


def _is_admin():
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


DNS_RULE_NAME = RULE_NAME + " (dns)"
IPV6_RULE_NAME = RULE_NAME + " (ipv6)"


def _block_ipv6():
    if sys.platform != "win32":
        return False
    try:
        r = subprocess.run(
            ["netsh", "interface", "ipv6", "set", "subinterface",
             "name=all", "disabled=yes", "store=active"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return r.returncode == 0
    except Exception:
        return False


def _restore_ipv6():
    if sys.platform != "win32":
        return
    try:
        subprocess.run(
            ["netsh", "interface", "ipv6", "set", "subinterface",
             "name=all", "disabled=no", "store=active"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        pass


def killswitch_enable():
    """Block all outbound except loopback and private LAN."""
    if not _is_admin():
        return False
    _run_netsh(["firewall", "delete", "rule", "name=" + OLD_RULE_NAME])
    _run_netsh(["firewall", "delete", "rule", "name=" + OLD_RULE_NAME + " (loopback)"])
    _run_netsh(["firewall", "delete", "rule", "name=" + DNS_RULE_NAME])
    _run_netsh(["firewall", "delete", "rule", "name=" + IPV6_RULE_NAME])
    ok = _run_netsh(["firewall", "set", "profile", "state", "on"])
    if not ok:
        return False
    # Block DNS leaks — only allow DNS through tunnel (127.0.0.1:10809 is SOCKS,
    # but we force all DNS to use local stub or tunnel; block standard DNS)
    _run_netsh(["firewall", "add", "rule", "name=" + DNS_RULE_NAME,
                "dir=out", "action=block", "protocol=udp", "remoteport=53"])
    _run_netsh(["firewall", "add", "rule", "name=" + DNS_RULE_NAME + " (tcp)",
                "dir=out", "action=block", "protocol=tcp", "remoteport=53"])
    # Block IPv6 completely (no IPv6 support via tunnel)
    _run_netsh(["firewall", "add", "rule", "name=" + IPV6_RULE_NAME,
                "dir=out", "action=block", "remoteip=::/0"])
    _block_ipv6()
    # local subnet + loopback allowed first (higher priority by order)
    ok = _run_netsh(["firewall", "add", "rule", "name=" + RULE_NAME + " (loopback)",
                     "dir=out", "action=allow", "remoteip=127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"])
    if not ok:
        return False
    ok = _run_netsh(["firewall", "add", "rule", "name=" + RULE_NAME,
                     "dir=out", "action=block", "remoteip=any"])
    if ok:
        atexit.register(killswitch_disable)
    return ok


def killswitch_disable():
    if sys.platform != "win32":
        return False
    _run_netsh(["firewall", "delete", "rule", "name=" + RULE_NAME])
    _run_netsh(["firewall", "delete", "rule", "name=" + RULE_NAME + " (loopback)"])
    _run_netsh(["firewall", "delete", "rule", "name=" + DNS_RULE_NAME])
    _run_netsh(["firewall", "delete", "rule", "name=" + DNS_RULE_NAME + " (tcp)"])
    _run_netsh(["firewall", "delete", "rule", "name=" + IPV6_RULE_NAME])
    _run_netsh(["firewall", "delete", "rule", "name=" + OLD_RULE_NAME])
    _run_netsh(["firewall", "delete", "rule", "name=" + OLD_RULE_NAME + " (loopback)"])
    _restore_ipv6()
    return True


def killswitch_active():
    if sys.platform != "win32":
        return False
    try:
        r = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", "name=" + RULE_NAME],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return RULE_NAME in r.stdout
    except Exception:
        return False
