# carekit

I built carekit because I kept doing the same jobs after a fresh Fedora install: enable the usual repositories, install a basic toolset, check the machine and make a quick local backup.

Run `carekit` without arguments for the menu, or call a command directly.

```bash
carekit
```

## Commands

### setup

Enables RPM Fusion and Flathub, then installs a small base set of packages such as git, curl, wget, vim, htop and tmux.

It asks before making changes unless `--yes` is used.

### doctor

Shows a quick local system check including kernel version, uptime, RAM and disk usage, pending DNF updates, failed systemd services, NetworkManager, PipeWire, WirePlumber and installed Flatpak apps.

### backup

Creates a timestamped `.tar.gz` from Documents, Pictures and Desktop. Add `--include-config` to include `~/.config`.

### restore

Extracts a carekit backup into a directory you choose.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/blamevlan/carekit/main/install.sh | bash
```

Python 3 is required. The installer handles the `rich` dependency.

## Examples

```bash
carekit doctor
carekit setup --yes
carekit backup --dest ~/Backups
carekit backup --dest ~/Backups --include-config
carekit restore --archive ~/Backups/carekit-backup-20260405-120000Z.tar.gz --dest ~/Restored
```

## Notes

Fedora is the platform I actually test on. RPM Fusion and DNF make the setup command Fedora-focused.

Backups stay local. carekit does not upload them anywhere.

## License

MIT. See [LICENSE](LICENSE).
