# Paragon PR7-OS

The Paragon family's own desktop: **Debian 13 with KDE Plasma**, in the family look (OBSIDIAN and AURORA, the
family's colours only, Bebas Neue, the PR7 mark), with the Paragon apps.

**Status: 0.1.0, the first release.** The approved mock-up is in `docs/mockup/`:

| | |
|---|---|
| `desktop_obsidian.png` | The desktop in OBSIDIAN: Plasma's floating panel, the launcher open, PR7-E in a Paragon window |
| `desktop_aurora.png` | The desktop in AURORA: PR7-E and PR7-P, a PR7-BK notification |
| `login.png` | The login screen (SDDM) |
| `boot_menu.png` | The boot menu (GRUB) |
| `boot_splash.png` | The boot splash (Plymouth) |

Redraw them with `python tools/mockup.py docs/mockup SHOTS_DIR` (SHOTS_DIR: the apps' own `tools/screenshots.py`
output; the icons come from the family's repositories checked out next to this one).

Based on Debian. Not affiliated with or endorsed by the Debian project.

## How it's made

- `pr7os/assets.py` generates every theme file from the family theme; `pr7os/apps.py` puts the apps in.
- `live/` is a Debian live-build configuration; CI builds the ISO in Debian 13, boots it in QEMU and takes
  screenshots (branch `ci-boot-screens`).
- Tests: `python -m pytest` (the theme files' colours, the login screen logging in, every app starting on Linux).
