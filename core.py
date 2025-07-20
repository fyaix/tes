import re
import json
import asyncio
from converter import extract_ip_port_from_path
from tester import test_account

def clean_account_dict(account: dict) -> dict:
    return {k: v for k, v in account.items() if not k.startswith("_")}

def deduplicate_accounts(accounts: list) -> list:
    # Simple: no deduplication. Add logic if needed.
    return accounts

def sort_priority(res):
    country = res.get("Country", "")
    if "🇮🇩" in country:
        return (0,)
    if "🇸🇬" in country:
        return (1,)
    if "🇯🇵" in country:
        return (2,)
    if "🇰🇷" in country:
        return (3,)
    if "🇺🇸" in country:
        return (4,)
    return (5, country)

def clean_provider_name(provider):
    provider = re.sub(r"\(.*?\)", "", provider)
    provider = provider.replace(",", "")
    provider = provider.strip()
    return provider

def ensure_ws_path_field(accounts: list) -> list:
    """
    Pastikan setiap akun memiliki _ws_path atau _ss_path.
    Jika belum ada, coba ambil dari plugin_opts/transport.
    """
    for acc in accounts:
        if acc.get("type") == "shadowsocks" and not acc.get("_ss_path"):
            plugin_opts = acc.get("plugin_opts", "")
            m = re.search(r'path=([^;]+)', plugin_opts)
            if m:
                acc["_ss_path"] = m.group(1)
        elif acc.get("type") in ("vless", "trojan") and not acc.get("_ws_path"):
            transport = acc.get("transport", {})
            if isinstance(transport, dict) and transport.get("type") == "ws":
                acc["_ws_path"] = transport.get("path", "")
    return accounts

async def test_all_accounts(accounts: list, semaphore, live_results):
    tasks = [
        test_account(acc, semaphore, i, live_results)
        for i, acc in enumerate(accounts)
    ]
    results = []
    for future in asyncio.as_completed(tasks):
        result = await future
        live_results[result["index"]].update(result)
        results.append(result)
    return results

def build_final_accounts(successful_results):
    final_accounts = []
    for i, res in enumerate(successful_results):
        account_obj = res["OriginalAccount"]
        country = res["Country"]
        provider = clean_provider_name(res["Provider"])
        tag = f"{country} {provider} -{i+1}"
        tag = " ".join(tag.split())  # Hilangkan spasi ganda
        account_obj["tag"] = tag
        final_accounts.append(clean_account_dict(account_obj))
    return final_accounts

def load_template(template_file):
    with open(template_file, "r") as f:
        return json.load(f)