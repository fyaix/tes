import asyncio
import socket
import re
from utils import is_alive, geoip_lookup, get_network_stats
from converter import extract_ip_port_from_path

MAX_RETRIES = 3
RETRY_DELAY = 1.5  # detik

def get_first_nonempty(*args):
    for x in args:
        if x:
            return x
    return None

def get_test_target(account):
    # 1. Coba IP dari path
    path_str = account.get("_ss_path") or account.get("_ws_path") or ""
    target_ip, target_port = extract_ip_port_from_path(path_str)
    if target_ip:
        return target_ip, target_port or 443, "path"

    # 2. Fallback ke host/sni/server_name/server
    # Ambil host dari WebSocket headers
    host = None
    if "host" in account:
        host = account["host"]
    elif "transport" in account and isinstance(account["transport"], dict):
        host = account["transport"].get("headers", {}).get("Host")
    # Ambil sni/server_name dari TLS
    sni = None
    if "tls" in account and isinstance(account["tls"], dict):
        sni = account["tls"].get("sni") or account["tls"].get("server_name")

    server = account.get("server")
    # Jika host/sni/server_name == server, tetap test (tidak hapus)
    candidates = []
    # Jangan ulangi value
    if host and host != server:
        candidates.append(("host", host))
    if sni and sni != server and sni != host:
        candidates.append(("sni", sni))
    if server:
        candidates.append(("server", server))

    for label, cand in candidates:
        # Cek apakah cand adalah IP, kalau ya langsung
        try:
            socket.inet_aton(cand)
            return cand, account.get("server_port", 443), label
        except Exception:
            pass
        # Kalau bukan IP, resolve ke IP
        try:
            resolved_ip = socket.gethostbyname(cand)
            return resolved_ip, account.get("server_port", 443), label
        except Exception:
            continue
    # Jika tidak ada yang bisa, return None
    return None, None, None

async def test_account(account: dict, semaphore: asyncio.Semaphore, index: int, live_results=None) -> dict:
    tag = account.get('tag', 'proxy')
    vpn_type = account.get('type', 'N/A')
    result = {
        "index": index, "VpnType": vpn_type, "OriginalTag": tag, "Latency": -1, "Jitter": -1, "ICMP": "N/A",
        "Country": "❓", "Provider": "-", "Tested IP": "-", "Status": "WAIT",
        "OriginalAccount": account, "TestType": "N/A", "Retry": 0
    }

    async with semaphore:
        # === LOGIKA BARU ===
        test_ip, test_port, test_source = get_test_target(account)
        if not test_ip:
            result['Status'] = '❌'
            return result

        for attempt in range(MAX_RETRIES):
            result['Status'] = '🔄'
            result['Retry'] = attempt
            if live_results is not None:
                live_results[index].update(result)
                await asyncio.sleep(0)  # yield to event loop

            is_conn, latency = is_alive(test_ip, test_port)
            if is_conn:
                geo_info = geoip_lookup(test_ip)
                result.update({
                    "Status": "✅",
                    "TestType": f"{test_source.upper()} TCP",
                    "Tested IP": test_ip,
                    "Latency": latency,
                    "Jitter": 0,
                    "ICMP": "✔",
                    **geo_info
                })
                # Update live_results
                if live_results is not None:
                    live_results[index].update(result)
                return result

            if attempt < MAX_RETRIES - 1:
                result['Status'] = '🔁'
                result['Retry'] = attempt+1
                if live_results is not None:
                    live_results[index].update(result)
                    await asyncio.sleep(0)
                await asyncio.sleep(RETRY_DELAY)

        # Fallback ping jika TCP gagal semua
        for attempt in range(MAX_RETRIES):
            result['Status'] = '🔄'
            result['Retry'] = attempt
            if live_results is not None:
                live_results[index].update(result)
                await asyncio.sleep(0)  # yield to event loop

            stats = get_network_stats(test_ip)
            if stats.get("Latency") != -1:
                geo_info = geoip_lookup(test_ip)
                result.update({
                    "Status": "✅",
                    "TestType": f"{test_source.upper()} Ping",
                    "Tested IP": test_ip,
                    **stats,
                    **geo_info
                })
                # Update live_results
                if live_results is not None:
                    live_results[index].update(result)
                return result

            if attempt < MAX_RETRIES - 1:
                result['Status'] = '🔁'
                result['Retry'] = attempt+1
                if live_results is not None:
                    live_results[index].update(result)
                    await asyncio.sleep(0)
                await asyncio.sleep(RETRY_DELAY)

        # Semua cara sudah dicoba, masih gagal
        result['Status'] = '❌'
        result['Retry'] = MAX_RETRIES
    # Update live_results for failed case
    if live_results is not None:
        live_results[index].update(result)
    return result