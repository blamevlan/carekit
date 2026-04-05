# carekit

A small toolkit for Fedora workstations. It handles the things you do once when setting up a new machine, and occasionally afterwards — enabling repos, running a quick health check, taking a backup.

```
carekit setup
carekit doctor
carekit backup --dest ~/Backups
```

## Commands

**`setup`** — enables RPM Fusion and Flathub, then installs a baseline set of packages (`git`, `curl`, `wget`, `vim`, `htop`, `tmux`). Asks for confirmation unless you pass `--yes`.

**`doctor`** — runs a quick local health check: package manager, Flatpak, NetworkManager, PipeWire, disk usage. No network calls, no changes.

**`backup`** — creates a timestamped `.tar.gz` from `~/Documents`, `~/Pictures` and `~/Desktop`. Add `--include-config` to also include `~/.config`.

**`restore`** — extracts a carekit backup archive into a directory of your choice.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/blamevlan/carekit/main/install.sh | bash
```

Requires Python 3. Installs to `/usr/local/bin/carekit` by default (needs sudo).

## Usage

```bash
carekit --help
carekit setup
carekit setup --yes
carekit doctor
carekit backup --dest ~/Backups --include-config
carekit restore --archive ~/Backups/carekit-backup-20260405-120000Z.tar.gz --dest ~/Restored
```

## Notes

- Fedora is the primary target. Most things will work on RHEL and similar, but it's not tested there.
- `setup` needs root for dnf and flatpak remote-add.
- `backup` and `restore` are entirely local — nothing leaves your machine.
