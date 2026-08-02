# ZifyVPN

Desktop VPN client built on [Xray-core](https://github.com/XTLS/Xray-core) with a modern PySide6 (Qt6) interface.

Supports VLESS + Reality / gRPC / TCP, subscription import, split tunneling, Kill Switch, and more.

---

## Features

- VLESS protocol (Reality, gRPC, TCP, WebSocket)
- Subscription import (base64 / sing-box / v2ray)
- Node list with latency ping and country flags
- TUN mode (full / split tunneling)
- System Proxy mode
- Kill Switch (per-app and global)
- DNS over Xray (DoH / DoT)
- IPv6 support
- GeoIP / GeoSite routing rules (bypass / enforce)
- Dark theme (Ultra Black)
- Real-time traffic graph (Rx/Tx)
- Backup / restore configuration
- Auto-update Xray-core

## Requirements

- Windows 10/11 (x64)
- Python 3.10+ (for development)
- Administrator privileges (for TUN / firewall)

## Quick Start

### Download

Download the latest `ZifyClient.exe` from [Releases](https://github.com/Harsed11/ZifyVPN/releases).

### Build from source

```bash
pip install -r requirements.txt
python -m PyInstaller --noconfirm ZifyVPN.spec
```

Or use the build script:

```powershell
.\build.ps1
```

The compiled binary will appear in `dist/ZifyClient.exe`.

## Project Structure

```
ZifyVPN/
├── vpn_configurator/
│   ├── main.py              # Entry point
│   ├── core/
│   │   ├── xray_manager.py  # Xray process control
│   │   ├── config_parser.py # Subscription parsing
│   │   ├── storage.py       # JSON storage
│   │   ├── geo.py           # GeoIP/GeoSite
│   │   ├── split_tunnel.py  # Split tunneling
│   │   ├── firewall.py      # Kill Switch
│   │   ├── dns_override.py  # DNS config
│   │   ├── ipv6_support.py  # IPv6 handling
│   │   ├── healthcheck.py   # Connection health
│   │   ├── stats.py         # gRPC traffic stats
│   │   ├── xray_updater.py  # Auto-update Xray
│   │   └── logger.py        # Logging
│   ├── ui/
│   │   ├── main_window.py   # Main window (150KB)
│   │   ├── theme.py         # Dark theme
│   │   └── components/      # UI widgets
│   └── bin/                 # Xray-core binaries
├── tests/                   # pytest + pytest-qt
├── data/                    # Runtime data (gitignored)
└── build.ps1               # Build script
```

## Running Tests

```bash
pytest -v
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
