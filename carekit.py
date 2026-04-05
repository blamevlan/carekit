#!/usr/bin/env python3
"""Fedora Care Kit: setup, diagnostics, backup and restore helpers."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Iterable


APP_NAME = "Fedora Care Kit"
DEFAULT_BACKUP_ITEMS = [
    "~/Documents",
    "~/Pictures",
    "~/Desktop",
]


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def info(msg: str) -> None:
    print(f"{Colors.BLUE}[*]{Colors.RESET} {msg}")


def ok(msg: str) -> None:
    print(f"{Colors.GREEN}[OK]{Colors.RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")


def err(msg: str) -> None:
    print(f"{Colors.RED}[ERR]{Colors.RESET} {msg}")


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def pkg_manager_cmd() -> str:
    if command_exists("dnf"):
        return "dnf"
    if command_exists("dnf5"):
        return "dnf5"
    return "dnf"


def is_fedora() -> bool:
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        return False
    content = os_release.read_text(encoding="utf-8", errors="ignore").lower()
    return "id=fedora" in content or "id_like=fedora" in content


def require_fedora() -> None:
    if not is_fedora():
        warn("This tool is Fedora-first. Some actions may not work on your distro.")


def has_admin_rights() -> bool:
    return os.geteuid() == 0


def with_privileges(base_cmd: list[str]) -> list[str]:
    if has_admin_rights():
        return base_cmd
    if command_exists("sudo"):
        return ["sudo", *base_cmd]
    return base_cmd


def print_setup_plan() -> None:
    info("Setup plan:")
    print("  1) Enable RPM Fusion free/nonfree")
    print("  2) Add Flathub remote")
    print("  3) Install baseline packages")


def run_setup(assume_yes: bool) -> int:
    require_fedora()
    print_setup_plan()

    if not has_admin_rights():
        warn("You are not root. Some steps require sudo.")

    if not assume_yes:
        answer = input("Run setup now? [y/N]: ").strip().lower()
        if answer not in {"y", "yes", "j", "ja"}:
            info("Cancelled.")
            return 0

    failures: list[str] = []

    dnf_cmd = pkg_manager_cmd()
    rpm_urls = [
        "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm",
        "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm",
    ]

    info("Enabling RPM Fusion ...")
    try:
        subprocess.run(
            ["bash", "-lc", " ".join(with_privileges([dnf_cmd, "install", "-y", *rpm_urls]))],
            check=True,
            text=True,
            capture_output=True,
        )
        ok("RPM Fusion enabled.")
    except subprocess.CalledProcessError as ex:
        failures.append("RPM Fusion")
        err(f"RPM Fusion failed: {ex.stderr.strip()[:240]}")

    info("Enabling Flathub ...")
    try:
        run_command(
            [
                "flatpak",
                "remote-add",
                "--if-not-exists",
                "flathub",
                "https://flathub.org/repo/flathub.flatpakrepo",
            ]
        )
        ok("Flathub enabled.")
    except (subprocess.CalledProcessError, FileNotFoundError) as ex:
        failures.append("Flathub")
        err(f"Flathub failed: {str(ex)[:240]}")

    base_packages = ["git", "curl", "wget", "vim", "htop", "tmux"]
    info(f"Installing baseline packages: {', '.join(base_packages)} ...")
    try:
        run_command(with_privileges([dnf_cmd, "install", "-y", *base_packages]))
        ok("Baseline packages installed.")
    except (subprocess.CalledProcessError, FileNotFoundError) as ex:
        failures.append("baseline packages")
        err(f"Package install failed: {str(ex)[:240]}")

    if failures:
        warn(f"Setup completed with issues in: {', '.join(failures)}")
        return 1

    ok("Setup completed successfully.")
    return 0


def check_binary(name: str) -> tuple[bool, str]:
    path = shutil.which(name)
    if path:
        return True, f"{name} found at {path}"
    return False, f"{name} not found"


def check_service(name: str) -> tuple[bool, str]:
    try:
        result = run_command(["systemctl", "is-active", name], check=False)
        active = result.stdout.strip() == "active"
        if active:
            return True, f"Service {name} is active"
        return False, f"Service {name} is {result.stdout.strip() or 'inactive'}"
    except FileNotFoundError:
        return False, "systemctl not available"


def check_user_service(name: str) -> tuple[bool, str]:
    try:
        result = run_command(["systemctl", "--user", "is-active", name], check=False)
        active = result.stdout.strip() == "active"
        if active:
            return True, f"User service {name} is active"
        return False, f"User service {name} is {result.stdout.strip() or 'inactive'}"
    except FileNotFoundError:
        return False, "systemctl not available"


def check_disk() -> tuple[bool, str]:
    usage = shutil.disk_usage("/")
    percent_used = int((usage.used / usage.total) * 100)
    if percent_used >= 90:
        return False, f"Root filesystem almost full ({percent_used}% used)"
    if percent_used >= 80:
        return True, f"Root filesystem getting full ({percent_used}% used)"
    return True, f"Root filesystem OK ({percent_used}% used)"


def run_doctor() -> int:
    require_fedora()
    info("Running diagnostics ...")

    checks: list[tuple[str, tuple[bool, str]]] = [
        ("dnf", check_binary(pkg_manager_cmd())),
        ("flatpak", check_binary("flatpak")),
        ("NetworkManager", check_service("NetworkManager")),
        ("pipewire", check_user_service("pipewire")),
        ("wireplumber", check_user_service("wireplumber")),
        ("disk", check_disk()),
    ]

    failures = 0
    for name, (status, message) in checks:
        _ = name
        if status:
            ok(message)
        else:
            failures += 1
            err(message)

    if failures:
        warn(f"Diagnostics completed: {failures} problem(s) found.")
        return 1

    ok("Diagnostics completed: no critical issues found.")
    return 0


def resolve_items(items: Iterable[str]) -> list[Path]:
    resolved = []
    for item in items:
        p = Path(os.path.expanduser(item)).resolve()
        if p.exists():
            resolved.append(p)
        else:
            warn(f"Path not found, skipped: {p}")
    return resolved


def run_backup(destination: str, include_config: bool) -> int:
    target_dir = Path(destination).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    items = DEFAULT_BACKUP_ITEMS.copy()
    if include_config:
        items.append("~/.config")

    sources = resolve_items(items)
    if not sources:
        err("No valid backup source paths found.")
        return 1

    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    backup_file = target_dir / f"carekit-backup-{timestamp}.tar.gz"

    info(f"Creating backup: {backup_file}")
    with tarfile.open(backup_file, mode="w:gz") as tar:
        for source in sources:
            arcname = source.name
            tar.add(source, arcname=arcname)
            ok(f"Added: {source}")

    ok(f"Backup created: {backup_file}")
    return 0


def run_restore(archive_path: str, destination: str) -> int:
    archive = Path(archive_path).expanduser().resolve()
    if not archive.exists():
        err(f"Archive not found: {archive}")
        return 1

    target = Path(destination).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    def _is_safe_member(member_name: str) -> bool:
        member_path = (target / member_name).resolve()
        return str(member_path).startswith(str(target))

    info(f"Extracting {archive} to {target}")
    with tarfile.open(archive, mode="r:gz") as tar:
        members = tar.getmembers()
        unsafe = [m.name for m in members if not _is_safe_member(m.name)]
        if unsafe:
            err(f"Unsafe archive paths detected, restore aborted: {unsafe[:3]}")
            return 1
        tar.extractall(path=target)

    ok("Restore completed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="carekit", description=APP_NAME)
    sub = parser.add_subparsers(dest="command", required=True)

    setup = sub.add_parser("setup", help="Run baseline Fedora setup")
    setup.add_argument("-y", "--yes", action="store_true", help="run without prompt")

    sub.add_parser("doctor", help="Run basic diagnostics")

    backup = sub.add_parser("backup", help="Create a backup archive")
    backup.add_argument("--dest", required=True, help="backup destination directory")
    backup.add_argument("--include-config", action="store_true", help="include ~/.config")

    restore = sub.add_parser("restore", help="Restore a backup archive")
    restore.add_argument("--archive", required=True, help="path to .tar.gz backup")
    restore.add_argument("--dest", required=True, help="restore destination directory")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "setup":
        return run_setup(assume_yes=args.yes)
    if args.command == "doctor":
        return run_doctor()
    if args.command == "backup":
        return run_backup(destination=args.dest, include_config=args.include_config)
    if args.command == "restore":
        return run_restore(archive_path=args.archive, destination=args.dest)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
