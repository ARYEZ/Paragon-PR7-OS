# Paragon PR7-OS

The Paragon family's own desktop: **Debian 13 with KDE Plasma**, in the family look (OBSIDIAN and AURORA, the
family's colours only, Inter, the PR7 mark), with the Paragon apps.

**Status: mock-up, waiting for approval.** Nothing is built yet. See `docs/mockup/`:

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
