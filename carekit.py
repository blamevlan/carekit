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
from rich.table import Table
from rich import box

console = Console()

DEFAULT_BACKUP_ITEMS = ["~/Documents", "~/Pictures", "~/Desktop"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def print_header(command: str) -> None:
    console.print()
    console.print(Panel(
        f"[bold]carekit[/]  [dim]github.com/blamevlan/carekit[/]\n"
        f"Command: [bold cyan]{command}[/]",
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


# ── Setup ─────────────────────────────────────────────────────────────────────

def cmd_setup(assume_yes: bool) -> int:
    print_header("setup")

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
    table.add_row("3", "Install baseline packages: git, curl, wget, vim, htop, tmux")
    console.print(table)
    console.print()

    if not assume_yes:
        answer = console.input("  Run setup now? [y/N]: ").strip().lower()
        console.print()
        if answer not in {"y", "yes", "j", "ja"}:
            console.print("  [dim]Cancelled.[/]\n")
            return 0

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


def check_disk() -> tuple[bool, str]:
    usage = shutil.disk_usage("/")
    pct = int((usage.used / usage.total) * 100)
    if pct >= 90:
        return False, f"{pct}% used — almost full"
    if pct >= 80:
        return True, f"{pct}% used — getting full"
    return True, f"{pct}% used"


def cmd_doctor() -> int:
    print_header("doctor")
    console.print("  [bold]Running diagnostics...[/]\n")

    checks = [
        ("dnf",            check_binary(pkg_manager())),
        ("flatpak",        check_binary("flatpak")),
        ("NetworkManager", check_service("NetworkManager")),
        ("pipewire",       check_service("pipewire", user=True)),
        ("wireplumber",    check_service("wireplumber", user=True)),
        ("disk /",         check_disk()),
    ]

    table = Table(box=box.SIMPLE, show_header=True, header_style="dim")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail", style="dim")

    failures = 0
    for name, (ok_flag, detail) in checks:
        if ok_flag:
            status = "[green]✓  OK[/]"
        else:
            status = "[red]✗  FAIL[/]"
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
    sub = parser.add_subparsers(dest="command", required=True)

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

    if args.command == "setup":
        return cmd_setup(assume_yes=args.yes)
    if args.command == "doctor":
        return cmd_doctor()
    if args.command == "backup":
        return cmd_backup(destination=args.dest, include_config=args.include_config)
    if args.command == "restore":
        return cmd_restore(archive_path=args.archive, destination=args.dest)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
