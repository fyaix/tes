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

def build_final_accounts(successful_results, custom_servers=None):
    """
    Build final accounts untuk config dengan optional server replacement
    
    Args:
        successful_results: Test results yang successful
        custom_servers: Optional list server baru untuk replacement
    """
    final_accounts = []
    
    # Jika ada custom servers, buat random distribution
    server_assignments = None
    if custom_servers:
        server_assignments = generate_server_assignments(successful_results, custom_servers)
        print(f"🔄 Config: Applying server replacement dengan {len(custom_servers)} servers")
        print(f"🔄 Config: Custom servers = {custom_servers}")
        print(f"🔄 Config: Server assignments = {server_assignments}")
    else:
        print(f"🔄 Config: No custom servers found - using original servers")
    
    for i, res in enumerate(successful_results):
        account_obj = res["OriginalAccount"].copy()  # Copy untuk avoid mutation
        country = res["Country"]
        provider = clean_provider_name(res["Provider"])
        tag = f"{country} {provider} -{i+1}"
        tag = " ".join(tag.split())  # Hilangkan spasi ganda
        
        # 🔄 APPLY SERVER REPLACEMENT untuk config final (bukan testing)
        if server_assignments and i < len(server_assignments):
            original_server = account_obj.get('server', '')
            new_server = server_assignments[i]
            account_obj['server'] = new_server
            print(f"🔄 Config: Account {i+1} server {original_server} → {new_server}")
            print(f"🔄 Config: Updated account server field = {account_obj.get('server')}")
        else:
            print(f"🔄 Config: Account {i+1} keeping original server = {account_obj.get('server')}")
        
        # 🔄 RESTORE original domain values (yang di-clean untuk testing)
        restore_original_domains_for_config(account_obj)
        
        account_obj["tag"] = tag
        final_accounts.append(clean_account_dict(account_obj))
    
    return final_accounts

def generate_server_assignments(successful_results, custom_servers):
    """
    Generate random server assignments untuk successful accounts
    """
    import random
    
    account_count = len(successful_results)
    server_count = len(custom_servers)
    
    # Calculate even distribution
    accounts_per_server = account_count // server_count
    remainder = account_count % server_count
    
    # Create assignment list
    assignments = []
    for i, server in enumerate(custom_servers):
        # Add extra account to first few servers if there's remainder
        count = accounts_per_server + (1 if i < remainder else 0)
        assignments.extend([server] * count)
    
    # Random shuffle assignments
    random.shuffle(assignments)
    
    print(f"🎲 Generated {account_count} assignments across {server_count} servers")
    return assignments

def restore_original_domains_for_config(account_obj):
    """
    Restore original domain values yang mungkin di-clean untuk testing
    Pastikan SNI/Host kembali ke nilai asli untuk config final
    """
    # Original values sudah tersimpan di account_obj, tidak perlu restore
    # Karena kita menggunakan copy() di build_final_accounts
    # Dan testing menggunakan fungsi terpisah yang tidak mengubah original
    
    print(f"🔄 Config: Using original domains for {account_obj.get('server', '')}")
    pass

def load_template(template_file):
    with open(template_file, "r") as f:
        return json.load(f)