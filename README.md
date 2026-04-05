# carekit

I built this because I kept repeating the same steps every time I set up a fresh Fedora machine — enabling RPM Fusion, adding Flathub, installing the same handful of packages. carekit wraps all of that into one tool, plus a couple of extras I wanted anyway (quick health check, local backups).

Just run `carekit` and pick what you want from the menu.

```
carekit
```

## What it does

**setup** — enables RPM Fusion (free + nonfree) and Flathub, then installs a base set of packages: git, curl, wget, vim, htop, tmux. Asks before doing anything unless you pass `--yes`.

**doctor** — runs a quick local health check. Looks at dnf, flatpak, NetworkManager, PipeWire, wireplumber and disk usage. No network calls, nothing gets changed.

**backup** — packs up Documents, Pictures and Desktop into a timestamped `.tar.gz`. Add `--include-config` to also grab `~/.config`.

**restore** — unpacks a carekit backup into whatever directory you point it at.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/blamevlan/carekit/main/install.sh | bash
```

Needs Python 3 and [rich](https://github.com/Textualize/rich) — the install script handles rich automatically.

## Usage

```bash
carekit                    # interactive menu
carekit doctor             # run directly
carekit setup --yes        # skip the confirmation
carekit backup --dest ~/Backups
carekit backup --dest ~/Backups --include-config
carekit restore --archive ~/Backups/carekit-backup-20260405-120000Z.tar.gz --dest ~/Restored
```

## Notes

- Built for Fedora. Should work on RHEL and similar but I only test on Fedora.
- `setup` needs sudo for dnf and flatpak.
- `backup` and `restore` are purely local, nothing gets uploaded anywhere.
