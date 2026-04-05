#!/usr/bin/env python3
# carekit — Fedora workstation toolkit
# github.com/blamevlan/carekit

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box

console = Console()

DEFAULT_BACKUP_ITEMS = ["~/Documents", "~/Pictures", "~/Desktop"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def print_banner() -> None:
    console.print()
    console.print(Panel(
        "[bold]carekit[/]  [dim]github.com/blamevlan[/]\n"
        "[dim]Fedora workstation toolkit[/]",
        border_style="blue",
        padding=(0, 2),
    ))
    console.print()


def print_header(command: str) -> None:
    console.print()
    console.print(Panel(
        f"[bold]carekit[/]  [dim]github.com/blamevlan[/]\n"
        f"[dim]{command}[/]",
        border_style="blue",
        padding=(0, 2),
    ))
    console.print()


def run(cmd: list[str], check: bool = True) -> tuple[int, str, str]:
    result = subprocess.run(cmd, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result.returncode, result.stdout, result.stderr


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def pkg_manager() -> str:
    return "dnf5" if command_exists("dnf5") else "dnf"


def is_fedora() -> bool:
    p = Path("/etc/os-release")
    if not p.exists():
        return False
    content = p.read_text(errors="ignore").lower()
    return "id=fedora" in content or "id_like=fedora" in content


def with_sudo(cmd: list[str]) -> list[str]:
    if os.geteuid() == 0:
        return cmd
    if command_exists("sudo"):
        return ["sudo", *cmd]
    return cmd


# ── Interactive menu ──────────────────────────────────────────────────────────

def show_menu() -> None:
    while True:
        print_banner()

        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column("Key", style="bold cyan")
        table.add_column("Command")
        table.add_column("Description", style="dim")
        table.add_row("1", "setup",   "Enable RPM Fusion + Flathub, install baseline packages")
        table.add_row("2", "doctor",  "Quick system health check")
        table.add_row("3", "backup",  "Create a timestamped backup archive")
        table.add_row("4", "restore", "Restore a backup archive")
        table.add_row("q", "quit",    "Exit")
        console.print(table)
        console.print()

        choice = Prompt.ask("  Select", choices=["1", "2", "3", "4", "q"], default="q")
        console.print()

        if choice == "1":
            assume_yes = Confirm.ask("  Run without confirmation prompts?", default=False)
            console.print()
            cmd_setup(assume_yes=assume_yes)
        elif choice == "2":
            cmd_doctor()
        elif choice == "3":
            dest = Prompt.ask("  Backup destination", default=str(Path.home() / "Backups"))
            inc  = Confirm.ask("  Include ~/.config?", default=False)
            console.print()
            cmd_backup(destination=dest, include_config=inc)
        elif choice == "4":
            archive = Prompt.ask("  Path to archive (.tar.gz)")
            dest    = Prompt.ask("  Restore destination", default=str(Path.home() / "Restored"))
            console.print()
            cmd_restore(archive_path=archive, destination=dest)
        else:
            console.print("  [dim]Bye.[/]\n")
            sys.exit(0)

        console.print()
        input("  Press Enter to return to menu...")
        console.clear()


# ── Setup ─────────────────────────────────────────────────────────────────────

def cmd_setup(assume_yes: bool) -> int:
    print_header("setup — RPM Fusion · Flathub · baseline packages")

    if not is_fedora():
        console.print(Panel(
            "[yellow]This system does not appear to be Fedora.[/]\n"
            "carekit setup is designed for Fedora. Proceed at your own risk.",
            border_style="yellow",
        ))
        console.print()

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Step", style="dim")
    table.add_column("Action")
    table.add_row("1", "Enable RPM Fusion free + nonfree")
    table.add_row("2", "Add Flathub remote")
    table.add_row("3", "Install: git  curl  wget  vim  htop  tmux")
    console.print(table)
    console.print()

    if not assume_yes:
        if not Confirm.ask("  Run setup now?", default=False):
            console.print("  [dim]Cancelled.[/]\n")
            return 0
        console.print()

    failures: list[str] = []
    dnf = pkg_manager()

    console.print("  [bold]Enabling RPM Fusion...[/]")
    try:
        subprocess.run(
            ["bash", "-lc", " ".join(with_sudo([
                dnf, "install", "-y",
                "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm",
                "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm",
            ]))],
            check=True, text=True, capture_output=True,
        )
        console.print("  [green]✓[/] RPM Fusion enabled.\n")
    except subprocess.CalledProcessError as ex:
        failures.append("RPM Fusion")
        console.print(f"  [red]✗[/] RPM Fusion failed: {ex.stderr.strip()[:200]}\n")

    console.print("  [bold]Enabling Flathub...[/]")
    try:
        run(["flatpak", "remote-add", "--if-not-exists", "flathub",
             "https://flathub.org/repo/flathub.flatpakrepo"])
        console.print("  [green]✓[/] Flathub enabled.\n")
    except (subprocess.CalledProcessError, FileNotFoundError) as ex:
        failures.append("Flathub")
        console.print(f"  [red]✗[/] Flathub failed: {str(ex)[:200]}\n")

    pkgs = ["git", "curl", "wget", "vim", "htop", "tmux"]
    console.print("  [bold]Installing baseline packages...[/]")
    try:
        run(with_sudo([dnf, "install", "-y", *pkgs]))
        console.print("  [green]✓[/] Packages installed.\n")
    except (subprocess.CalledProcessError, FileNotFoundError) as ex:
        failures.append("packages")
        console.print(f"  [red]✗[/] Package install failed: {str(ex)[:200]}\n")

    if failures:
        console.print(Panel(
            f"[yellow]Setup completed with issues:[/] {', '.join(failures)}",
            border_style="yellow",
        ))
    else:
        console.print(Panel("[green]Setup completed successfully.[/]", border_style="green"))
    console.print()
    return 1 if failures else 0


# ── Doctor ────────────────────────────────────────────────────────────────────

def check_binary(name: str) -> tuple[bool, str]:
    path = shutil.which(name)
    return (True, str(path)) if path else (False, "not found")


def check_service(name: str, user: bool = False) -> tuple[bool, str]:
    cmd = ["systemctl", "--user", "is-active", name] if user else ["systemctl", "is-active", name]
    try:
        _, out, _ = run(cmd, check=False)
        state = out.strip()
        return state == "active", state or "inactive"
    except FileNotFoundError:
        return False, "systemctl not available"


def check_failed_services() -> tuple[bool, str]:
    try:
        _, out, _ = run(["systemctl", "--failed", "--no-legend", "--no-pager"], check=False)
        lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
        if not lines:
            return True, "none"
        return False, ", ".join(lines[:3]) + ("..." if len(lines) > 3 else "")
    except FileNotFoundError:
        return False, "systemctl not available"


def check_disk() -> tuple[bool, str]:
    usage = shutil.disk_usage("/")
    pct = int((usage.used / usage.total) * 100)
    total_gb = usage.total // (1024 ** 3)
    free_gb  = (usage.total - usage.used) // (1024 ** 3)
    detail = f"{pct}% used — {free_gb} GB free of {total_gb} GB"
    if pct >= 90:
        return False, f"{detail} — almost full"
    if pct >= 80:
        return True, f"{detail} — getting full"
    return True, detail


def check_ram() -> tuple[bool, str]:
    try:
        mem = Path("/proc/meminfo").read_text()
        total = free = available = 0
        for line in mem.splitlines():
            if line.startswith("MemTotal:"):
                total = int(line.split()[1])
            elif line.startswith("MemAvailable:"):
                available = int(line.split()[1])
        used = total - available
        pct = int((used / total) * 100) if total else 0
        total_gb   = round(total / (1024 ** 2), 1)
        used_gb    = round(used  / (1024 ** 2), 1)
        detail = f"{used_gb} GB used of {total_gb} GB ({pct}%)"
        return pct < 90, detail
    except Exception:
        return False, "could not read"


def check_updates() -> tuple[bool, str]:
    try:
        code, out, _ = run([pkg_manager(), "check-update", "--quiet"], check=False)
        if code == 0:
            return True, "up to date"
        lines = [l for l in out.strip().splitlines() if l.strip() and not l.startswith("Last")]
        count = len(lines)
        return False, f"{count} update(s) available"
    except FileNotFoundError:
        return False, "dnf not available"


def check_flatpak_count() -> tuple[bool, str]:
    if not command_exists("flatpak"):
        return True, "flatpak not installed"
    try:
        _, out, _ = run(["flatpak", "list", "--app", "--columns=name"], check=False)
        count = len([l for l in out.strip().splitlines() if l.strip()])
        return True, f"{count} app(s) installed"
    except Exception:
        return False, "could not read"


def check_kernel() -> tuple[bool, str]:
    try:
        _, out, _ = run(["uname", "-r"])
        return True, out.strip()
    except Exception:
        return False, "could not read"


def check_uptime() -> tuple[bool, str]:
    try:
        with open("/proc/uptime") as f:
            seconds = float(f.read().split()[0])
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return True, f"{h}h {m}m"
    except Exception:
        return False, "could not read"


def cmd_doctor() -> int:
    print_header("doctor — system health check")
    console.print("  [bold]Running diagnostics...[/]\n")

    checks = [
        ("kernel",          check_kernel()),
        ("uptime",          check_uptime()),
        ("RAM",             check_ram()),
        ("disk /",          check_disk()),
        ("dnf updates",     check_updates()),
        ("failed services", check_failed_services()),
        ("NetworkManager",  check_service("NetworkManager")),
        ("pipewire",        check_service("pipewire", user=True)),
        ("wireplumber",     check_service("wireplumber", user=True)),
        ("flatpak apps",    check_flatpak_count()),
    ]

    table = Table(box=box.SIMPLE, show_header=True, header_style="dim")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail", style="dim")

    failures = 0
    for name, (ok_flag, detail) in checks:
        status = "[green]✓  OK[/]" if ok_flag else "[red]✗  FAIL[/]"
        if not ok_flag:
            failures += 1
        table.add_row(name, status, detail)

    console.print(table)
    console.print()

    if failures:
        console.print(Panel(
            f"[yellow]{failures} problem(s) found.[/] Review the table above.",
            border_style="yellow",
        ))
    else:
        console.print(Panel("[green]All checks passed.[/]", border_style="green"))
    console.print()
    return 1 if failures else 0


# ── Backup ────────────────────────────────────────────────────────────────────

def cmd_backup(destination: str, include_config: bool) -> int:
    print_header("backup")

    items = DEFAULT_BACKUP_ITEMS.copy()
    if include_config:
        items.append("~/.config")

    sources = []
    for item in items:
        p = Path(os.path.expanduser(item)).resolve()
        if p.exists():
            sources.append(p)
        else:
            console.print(f"  [yellow]⚠[/]  Skipped (not found): {p}")

    if not sources:
        console.print(Panel("[red]No valid source paths found.[/]", border_style="red"))
        console.print()
        return 1

    target_dir = Path(destination).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    backup_file = target_dir / f"carekit-backup-{timestamp}.tar.gz"

    console.print(f"  [bold]Creating archive:[/] [dim]{backup_file}[/]\n")
    with tarfile.open(backup_file, mode="w:gz") as tar:
        for source in sources:
            tar.add(source, arcname=source.name)
            console.print(f"  [green]✓[/] {source}")

    console.print()
    console.print(Panel(
        f"[green]Backup created:[/]\n[dim]{backup_file}[/]",
        border_style="green",
    ))
    console.print()
    return 0


# ── Restore ───────────────────────────────────────────────────────────────────

def cmd_restore(archive_path: str, destination: str) -> int:
    print_header("restore")

    archive = Path(archive_path).expanduser().resolve()
    if not archive.exists():
        console.print(Panel(f"[red]Archive not found:[/] {archive}", border_style="red"))
        console.print()
        return 1

    target = Path(destination).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    console.print(f"  [bold]Extracting to:[/] [dim]{target}[/]\n")

    with tarfile.open(archive, mode="r:gz") as tar:
        unsafe = [
            m.name for m in tar.getmembers()
            if not str((target / m.name).resolve()).startswith(str(target))
        ]
        if unsafe:
            console.print(Panel(
                f"[red]Unsafe paths in archive — restore aborted.[/]\n[dim]{unsafe[:3]}[/]",
                border_style="red",
            ))
            console.print()
            return 1
        tar.extractall(path=target)

    console.print(Panel("[green]Restore completed.[/]", border_style="green"))
    console.print()
    return 0


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(prog="carekit", description="Fedora workstation toolkit")
    sub = parser.add_subparsers(dest="command")

    s = sub.add_parser("setup", help="Enable RPM Fusion + Flathub, install baseline packages")
    s.add_argument("-y", "--yes", action="store_true", help="skip confirmation prompt")

    sub.add_parser("doctor", help="Run a quick system health check")

    b = sub.add_parser("backup", help="Create a backup archive")
    b.add_argument("--dest", required=True, help="destination directory")
    b.add_argument("--include-config", action="store_true", help="also include ~/.config")

    r = sub.add_parser("restore", help="Restore a backup archive")
    r.add_argument("--archive", required=True, help="path to .tar.gz backup file")
    r.add_argument("--dest", required=True, help="restore destination directory")

    args = parser.parse_args()

    if not args.command:
        show_menu()
        return 0

    if args.command == "setup":
        return cmd_setup(assume_yes=args.yes)
    if args.command == "doctor":
        return cmd_doctor()
    if args.command == "backup":
        return cmd_backup(destination=args.dest, include_config=args.include_config)
    if args.command == "restore":
        return cmd_restore(archive_path=args.archive, destination=args.dest)

    return 0


if __name__ == "__main__":
    sys.exit(main())
