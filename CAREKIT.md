# carekit

A small Fedora-first toolkit for day-to-day workstation tasks.

`carekit` currently ships four commands:

- `setup` — enable RPM Fusion + Flathub and install baseline packages
- `doctor` — run quick local checks (package tools, services, disk usage)
- `backup` — create a timestamped `.tar.gz` from common user folders
- `restore` — restore a backup archive into a target directory

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/blamevlan/blamevlan/main/install.sh | bash
```

If your repo path is different, set it explicitly:

```bash
curl -fsSL https://raw.githubusercontent.com/<user>/<repo>/main/install.sh | \
REPO_RAW_BASE="https://raw.githubusercontent.com/<user>/<repo>/main" bash
```

## Usage

```bash
carekit --help
carekit setup
carekit setup --yes
carekit doctor
carekit backup --dest ~/Backups --include-config
carekit restore --archive ~/Backups/carekit-backup-YYYYMMDD-HHMMSSZ.tar.gz --dest ~/RestoreTest
```

## Notes

- Fedora is the main target (`dnf`/`dnf5`, RPM Fusion, Flathub).
- `setup` usually needs root privileges (`sudo`).
- `backup` and `restore` are local-only; nothing is uploaded.
