import re

VALID_ACCOUNT_TYPES = {"vmess", "vless", "trojan", "shadowsocks"}

def extract_path_from_plugin_opts(opts_string: str) -> str | None:
    """Ekstrak 'path' dari string plugin_opts."""
    if not isinstance(opts_string, str):
        return None
    match = re.search(r'path=([^;]+)', opts_string)
    if match:
        return match.group(1)
    return None

def extract_accounts_from_config(config_data: dict) -> list[dict]:
    """
    Ekstrak semua akun dari config dan tambahkan _ws_path/_ss_path jika ada.
    """
    accounts = []
    if not isinstance(config_data, dict):
        return []
    for outbound in config_data.get("outbounds", []):
        if outbound.get("type") in VALID_ACCOUNT_TYPES:
            # Shadowsocks
            if outbound.get("type") == "shadowsocks":
                plugin_opts = outbound.get("plugin_opts", "")
                path = extract_path_from_plugin_opts(plugin_opts)
                if path:
                    outbound["_ss_path"] = path
            # VLESS/trojan ws
            elif outbound.get("type") in ("vless", "trojan"):
                transport = outbound.get("transport", {})
                if isinstance(transport, dict) and transport.get("type") == "ws":
                    path = transport.get("path", "")
                    if path:
                        outbound["_ws_path"] = path
            accounts.append(outbound)
    print(f"✔️ Ditemukan dan diproses {len(accounts)} akun dari file konfigurasi.")
    return accounts