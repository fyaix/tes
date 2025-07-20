import os
import json
import re
import asyncio
from datetime import datetime
from rich.table import Table
from rich.console import Console
from rich.live import Live
from dotenv import load_dotenv

from github_client import GitHubClient
from core import (
    deduplicate_accounts, sort_priority, ensure_ws_path_field,
    build_final_accounts, load_template, test_all_accounts
)
from extractor import extract_accounts_from_config
from converter import parse_link, inject_outbounds_to_template

MAX_CONCURRENT_TESTS = 5
TEMPLATE_FILE = "template.json"
SPINNERS = ["◐", "◓", "◑", "◒"]
DOTS = ["⠁", "⠂", "⠄", "⠂"]

def get_user_vpn_links():
    console = Console()
    console.print(
        "\n[bold cyan]Paste akun baru (jika ada). Ketik 'selesai' di baris baru jika sudah.[/bold cyan]"
    )
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().lower() == "selesai":
            break
        lines.append(line)
    full_text = "\n".join(lines)
    vpn_pattern = r"(?:vless|vmess|trojan|ss)://[^\s]+"
    found_links = re.findall(vpn_pattern, full_text)
    if found_links:
        console.print(
            f"✔️ Ditemukan {len(found_links)} link VPN baru.", style="bold green"
        )
    return found_links

def get_spinner(frame):
    return SPINNERS[frame % len(SPINNERS)]

def get_dots(frame):
    return "." * ((frame % 4) + 1)

def generate_table(test_results, frame=0):
    table = Table(title="Hasil Tes Jaringan VPN")
    table.add_column("No", justify="right", style="dim")
    table.add_column("Type", justify="center", style="bold yellow")
    table.add_column("Country", justify="center")
    table.add_column("Provider", style="cyan")
    table.add_column("IP ", style="yellow")
    table.add_column("Latency", justify="right", style="magenta")
    table.add_column("Jitter", justify="right", style="blue")
    table.add_column("ICMP", justify="center", style="green")
    table.add_column("Status", justify="center")

    for i, res in enumerate(test_results):
        status = res.get("Status", "")
        retry = res.get("Retry", 0)
        is_waiting = status == "WAIT"
        is_testing = status.startswith("Testing...")
        is_retry = status.startswith("Retry(")
        is_success = status == "●"
        is_failed = status.startswith("✖")

        loading_anim = get_spinner(frame)
        dots = get_dots(frame)
        loading_str = f"{loading_anim}{dots}"

        if is_waiting:
            display = "[grey62]Waiting[/]"
            country_disp = provider_disp = ip_disp = latency_disp = jitter_disp = (
                icmp_disp
            ) = display
            status_disp = display
        elif is_testing:
            display = f"[cyan]{loading_str}[/]"
            country_disp = provider_disp = ip_disp = latency_disp = jitter_disp = (
                icmp_disp
            ) = display
            status_disp = "[bold blue]Testing...[/]"
        elif is_retry:
            display = f"[yellow]{loading_str}[/]"
            country_disp = provider_disp = ip_disp = latency_disp = jitter_disp = (
                icmp_disp
            ) = display
            status_disp = f"[yellow]Retry({retry})[/yellow]"
        elif is_success or is_failed:
            country_disp = str(res["Country"])
            provider_disp = str(res["Provider"])
            ip_disp = res["Tested IP"]
            latency_disp = f"{res['Latency']} ms" if res["Latency"] != -1 else "-"
            jitter_disp = f"{res['Jitter']} ms" if res["Jitter"] != -1 else "-"
            icmp_disp = res["ICMP"]
            status_disp = "[green]●[/green]" if is_success else "[red]✖[/red]"
        else:
            country_disp = provider_disp = ip_disp = latency_disp = jitter_disp = icmp_disp = "-"
            status_disp = "[grey62]Unknown[/]"

        table.add_row(
            str(i + 1),
            res.get("VpnType", "N/A").upper(),
            country_disp,
            provider_disp,
            ip_disp,
            latency_disp,
            jitter_disp,
            icmp_disp,
            status_disp,
        )
    return table

def get_source_config(github_client):
    console = Console()
    console.print("\n[bold cyan]Pilih sumber konfigurasi awal:[/bold cyan]")
    console.print("1. Buat config baru dari `template.json` lokal")
    console.print("2. Ambil dan tes ulang config dari GitHub")
    choice = input("Pilihan (1/2): ")
    if choice == "2" and github_client and github_client.token:
        files = github_client.list_files_in_repo()
        json_files = [
            f for f in files if f["type"] == "file" and f["name"].endswith(".json")
        ]
        if not json_files:
            console.print(
                "❌ Tidak ada file .json ditemukan di repo.", style="bold red"
            )
        else:
            console.print("\n[bold cyan]Pilih file dari repo GitHub:[/bold cyan]")
            for i, f in enumerate(json_files):
                console.print(f"{i + 1}. {f['name']}")
            try:
                file_choice = int(input(f"Pilihan (1-{len(json_files)}): ")) - 1
                if 0 <= file_choice < len(json_files):
                    selected_file = json_files[file_choice]
                    console.print(f"Mengambil '{selected_file['name']}'...")
                    content, sha = github_client.get_file(selected_file["path"])
                if content:
                    return json.loads(content), selected_file["path"], sha
            except (ValueError, IndexError):
                console.print("Pilihan tidak valid.", style="yellow")
    console.print(f"Membuat config baru dari template lokal: '{TEMPLATE_FILE}'")
    with open(TEMPLATE_FILE, "r") as f:
        return json.load(f), None, None

def perform_final_action(config_str, github_client, github_path, sha):
    console = Console()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    new_filename = f"VortexVpn-{timestamp}.json"
    while True:
        console.print("\n[bold cyan]Pilih aksi selanjutnya:[/bold cyan]")
        console.print(f"1. Download file sebagai '{new_filename}'")
        console.print("2. Upload/Update file ke GitHub")
        console.print("3. Keluar")
        choice = input("Pilihan (1/2/3): ")
        if choice == "1":
            with open(new_filename, "w", encoding="utf-8") as f:
                f.write(config_str)
            console.print(
                f"✔️ Konfigurasi disimpan sebagai '{new_filename}'", style="bold green"
            )
        elif choice == "2":
            if not github_client or not github_client.token:
                console.print("❌ Token GitHub tidak diatur.", style="bold red")
                continue
            commit_msg = input("Masukkan pesan commit: ")
            upload_path = github_path if github_path else new_filename
            console.print(f"Mengunggah ke '{upload_path}' di GitHub...")
            github_client.update_or_create_file(
                upload_path, config_str, commit_msg, sha
            )
        elif choice == "3":
            break

async def main():
    console = Console()
    console.print("[bold green]--- Manajer Konfigurasi VortexVpn ---[/bold green]")
    load_dotenv()
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("tidak ada token")
    repo_owner = input("Masukkan Nama Pengguna/Owner Repo GitHub: ")
    repo_name = input("Masukkan Nama Repositori GitHub: ")
    github_client = (
        GitHubClient(github_token, repo_owner, repo_name) if github_token else None
    )

    source_config, github_path, sha = get_source_config(github_client)
    existing_accounts = extract_accounts_from_config(source_config)
    existing_accounts = ensure_ws_path_field(existing_accounts)

    console.print("\n[bold cyan]Paste akun baru (ketik 'selesai' jika sudah):[/bold cyan]")
    user_links = get_user_vpn_links()
    accounts_from_links = []

    for link in user_links:
        parsed = parse_link(link)
        if parsed:
            accounts_from_links.append(parsed)
        else:
            console.print(f"⚠️ Link tidak valid diabaikan: {link[:50]}...", style="yellow")

    if not isinstance(existing_accounts, list):
        existing_accounts = []
    if not isinstance(accounts_from_links, list):
        accounts_from_links = []

    all_accounts = deduplicate_accounts(existing_accounts + accounts_from_links)
    all_accounts = ensure_ws_path_field(all_accounts)

    if not all_accounts:
        console.print("❌ Tidak ada akun valid untuk dites.", style="bold red")
        return

    console.print(
        f"\n[bold]Memulai pengetesan untuk {len(all_accounts)} akun unik...[/bold]"
    )
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TESTS)

    live_results = [
        {
            "index": i,
            "OriginalTag": acc["tag"],
            "OriginalAccount": acc,
            "VpnType": acc.get("type", "-"),
            "Country": "❓",
            "Provider": "-",
            "Tested IP": "-",
            "Latency": -1,
            "Jitter": -1,
            "ICMP": "N/A",
            "Status": "WAIT",
        }
        for i, acc in enumerate(all_accounts)
    ]

    with Live(
        generate_table(live_results, 0), refresh_per_second=6, screen=True
    ) as live:
        frame = 0
        results = await test_all_accounts(all_accounts, semaphore, live_results)
        for res in results:
            frame += 1
            live.update(generate_table(live_results, frame))

    successful_accounts = [res for res in live_results if res["Status"] == "●"]

    if not successful_accounts:
        console.print("\nTidak ada akun yang berhasil lolos tes.", style="bold red")
        return

    successful_accounts.sort(key=sort_priority)
    final_accounts_to_inject = build_final_accounts(successful_accounts)

    console.print("\n--- HASIL AKHIR PENGETESAN (Prioritas Negara & Tag Bersih) ---")
    console.print(generate_table(successful_accounts))

    console.print("\n[bold]Membangun file konfigurasi akhir dari template.json lokal...[/bold]")
    try:
        fresh_template_data = load_template(TEMPLATE_FILE)
    except Exception as e:
        console.print(f"Gagal membaca template: {e}", style="red")
        return

    final_config_data = inject_outbounds_to_template(
        fresh_template_data, final_accounts_to_inject
    )
    final_config_str = json.dumps(final_config_data, indent=2, ensure_ascii=False)

    perform_final_action(final_config_str, github_client, github_path, sha)
    console.print("\n[bold green]Terima kasih![/bold green]")

if __name__ == "__main__":
    asyncio.run(main())