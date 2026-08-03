import json
import base64
import ssl
import urllib.request
from urllib.parse import urlparse, parse_qs, unquote


def _pad_b64(data):
    data = data.strip().replace("-", "+").replace("_", "/")
    r = len(data) % 4
    if r:
        data += "=" * (4 - r)
    return data


def _b64decode(data):
    try:
        return base64.b64decode(_pad_b64(data)).decode("utf-8")
    except Exception:
        return None


def _getq(params):
    return {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in params.items()}


def fetch_subscription_text(url):
    ctx = ssl.create_default_context()

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "v2rayN/6.23",
            "Accept": "*/*",
        },
    )

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            content = response.read().decode("utf-8").strip()
    except ssl.SSLCertVerificationError:
        # Fallback for self-signed subscription servers — warn but allow
        ctx_fallback = ssl.create_default_context()
        ctx_fallback.check_hostname = False
        ctx_fallback.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, context=ctx_fallback, timeout=15) as response:
            content = response.read().decode("utf-8").strip()

    try:
        decoded = base64.b64decode(content).decode("utf-8")
        return decoded
    except Exception:
        return content


def parse_subscription(url):
    all_results = parse_subscription_all(url)
    if not all_results:
        raise ValueError("No valid proxy link found in subscription")
    return all_results[0]


def parse_subscription_all(url):
    try:
        text = fetch_subscription_text(url)
    except Exception as e:
        raise ValueError(f"Failed to fetch subscription URL: {e}")

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    results = []

    for line in lines:
        try:
            result = parse_config(line, _from_sub=True)
            if "subscription_url" not in result:
                result["subscription_url"] = url
            results.append(result)
        except ValueError:
            continue

    return results


def parse_config(url, _from_sub=False):
    url = url.strip()
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme in ("http", "https"):
        if _from_sub:
            raise ValueError("Nested subscription URLs not supported")
        return parse_subscription(url)
    elif scheme == "vless":
        return parse_vless(url)
    elif scheme == "vmess":
        return parse_vmess(url)
    elif scheme == "trojan":
        return parse_trojan(url)
    elif scheme == "ss":
        return parse_shadowsocks(url)
    else:
        raise ValueError(f"Unsupported configuration type: {scheme}")


def parse_vless(url):
    parsed = urlparse(url)
    q = _getq(parse_qs(parsed.query))
    fragment = (parsed.fragment or "").strip()

    network = q.get("type", "tcp")
    path = unquote(q.get("path", ""))
    if network == "grpc" and not path:
        path = unquote(q.get("serviceName", ""))

    return {
        "type": "vless",
        "uuid": unquote(parsed.username) if parsed.username else q.get("uuid", ""),
        "host": parsed.hostname or "",
        "port": parsed.port or 443,
        "network": network,
        "security": q.get("security", "none"),
        "path": path,
        "sni": q.get("sni", q.get("host", "")),
        "alpn": q.get("alpn", ""),
        "fp": q.get("fp", ""),
        "pbk": q.get("pbk", ""),
        "sid": q.get("sid", ""),
        "spx": q.get("spx", ""),
        "encryption": q.get("encryption", "none"),
        "flow": q.get("flow", ""),
        "authority": unquote(q.get("authority", "")),
        "ps": unquote(fragment),
        "raw_url": url,
    }


def parse_vmess(url):
    raw = url[8:]

    decoded = _b64decode(raw)
    if decoded:
        try:
            data = json.loads(decoded)
            try:
                port = int(data.get("port", 443) or 443)
            except (ValueError, TypeError):
                port = 443
            return {
                "type": "vmess",
                "uuid": data.get("id", ""),
                "host": data.get("add", ""),
                "port": port,
                "network": data.get("net", "tcp"),
                "security": "tls" if data.get("tls") == "tls" else "none",
                "path": data.get("path", ""),
                "sni": data.get("sni", data.get("host", "")),
                "alpn": data.get("alpn", ""),
                "fp": data.get("fp", ""),
                "pbk": data.get("pbk", data.get("reality_pbk", "")),
                "sid": data.get("sid", ""),
                "encryption": data.get("scy", "auto"),
                "aid": data.get("aid", 0),
                "ps": data.get("ps", ""),
                "raw_url": url,
            }
        except json.JSONDecodeError:
            pass

    parsed = urlparse(url)
    q = _getq(parse_qs(parsed.query))
    return {
        "type": "vmess",
        "uuid": parsed.username or q.get("id", ""),
        "host": parsed.hostname or "",
        "port": parsed.port or 443,
        "network": q.get("type", "tcp"),
        "security": q.get("security", "none"),
        "path": unquote(q.get("path", "")),
        "sni": q.get("sni", ""),
        "alpn": q.get("alpn", ""),
        "fp": q.get("fp", ""),
        "encryption": q.get("encryption", "auto"),
        "aid": int(q.get("aid", 0)),
        "raw_url": url,
    }


def parse_trojan(url):
    parsed = urlparse(url)
    q = _getq(parse_qs(parsed.query))
    fragment = (parsed.fragment or "").strip()

    return {
        "type": "trojan",
        "uuid": parsed.password or "",
        "host": parsed.hostname or "",
        "port": parsed.port or 443,
        "network": q.get("type", "tcp"),
        "security": q.get("security", "tls") if q.get("security") else "tls",
        "path": unquote(q.get("path", "")),
        "sni": q.get("sni", q.get("host", parsed.hostname or "")),
        "alpn": q.get("alpn", ""),
        "fp": q.get("fp", ""),
        "encryption": "none",
        "ps": unquote(fragment),
        "raw_url": url,
    }


def parse_shadowsocks(url):
    parsed = urlparse(url)
    q = _getq(parse_qs(parsed.query))
    fragment = (parsed.fragment or "").strip()

    host = ""
    port = 443
    method = ""
    password = ""
    plugin = q.get("plugin", "")

    netloc = parsed.netloc

    if "@" in netloc:
        user_part, host_part = netloc.rsplit("@", 1)
        host = host_part.split(":")[0]
        try:
            port = int(host_part.split(":")[1])
        except (IndexError, ValueError, TypeError):
            port = 443

        decoded = _b64decode(user_part)
        if decoded and ":" in decoded:
            method, password = decoded.split(":", 1)
        elif ":" in user_part:
            method, password = user_part.split(":", 1)
        else:
            method = user_part
    else:
        decoded = _b64decode(netloc)
        if decoded and "@" in decoded:
            user_part, host_part = decoded.rsplit("@", 1)
            host = host_part.split(":")[0] if ":" in host_part else host_part
            try:
                port = int(host_part.split(":")[1])
            except (IndexError, ValueError, TypeError):
                port = 443
            if ":" in user_part:
                method, password = user_part.split(":", 1)
        elif decoded and ":" in decoded:
            parts = decoded.split(":")
            if len(parts) >= 3:
                method = parts[0]
                password = ":".join(parts[1:-1])
                try:
                    port = int(parts[-1].split("@")[0] if "@" in parts[-1] else parts[-1])
                except (ValueError, TypeError):
                    pass
                h = parts[-1].split("@")[-1] if "@" in parts[-1] else ""
                host = h

    label = unquote(fragment) or ""
    name = label if label else f"{host}:{port}"

    return {
        "type": "ss",
        "uuid": f"{method}:{password}" if method and password else "",
        "host": host,
        "port": port,
        "network": "tcp",
        "security": "none",
        "path": "",
        "sni": "",
        "alpn": "",
        "fp": "",
        "encryption": method,
        "plugin": plugin,
        "ps": name,
        "raw_url": url,
    }
