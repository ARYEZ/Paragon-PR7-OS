#!/usr/bin/env python3
"""One finish for the whole desktop: the Paragon apps' OBSIDIAN / AURORA and Plasma's global theme kept together.

Started with Plasma (/etc/xdg/autostart/pr7os-finish-sync.desktop), it looks every two seconds at both:
- the family's choice, ~/.config/paragon/family-finish (any Paragon app's View > Finish writes it, and every open app
  follows it), and
- Plasma's, LookAndFeelPackage in ~/.config/kdeglobals (System Settings > Global Theme writes it).
When an app switched the finish, Plasma gets the matching Paragon global theme (plasma-apply-lookandfeel, its own tool:
colours, window decoration, the wallpaper's light or dark picture; the panel layout is left alone). When you picked a
Paragon global theme in System Settings, the family file follows, and so do the apps. Picking another global theme
(Breeze ...) leaves the apps as they are. Standard library only (Debian's python3).

    python3 finish_sync.py            keep them together until the session ends
    python3 finish_sync.py --once     one look (tests)
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

THEMES = {"obsidian": "org.paragon.pr7os.obsidian", "aurora": "org.paragon.pr7os.aurora"}


def config_home() -> str:
    return os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")


def family_file() -> str:
    return os.environ.get("PARAGON_FAMILY_FILE") or os.path.join(config_home(), "paragon", "family-finish")


def family() -> str | None:
    try:
        with open(family_file(), encoding="utf-8") as fh:
            v = fh.read().strip().lower()
    except OSError:
        return None
    return v if v in THEMES else None


def set_family(name: str) -> None:
    path = family_file()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path + ".part", "w", encoding="utf-8") as fh:
        fh.write(name)
    os.replace(path + ".part", path)


def plasma() -> str | None:
    """Plasma's global theme as a finish name, or None when it isn't one of Paragon's (or isn't set yet)."""
    try:
        with open(os.path.join(config_home(), "kdeglobals"), encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    group = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("["):
            group = line
        elif group == "[KDE]" and line.startswith("LookAndFeelPackage="):
            pkg = line.split("=", 1)[1].strip()
            return next((name for name, p in THEMES.items() if p == pkg), None)
    return None


def apply_plasma(name: str) -> bool:
    command = os.environ.get("PR7OS_APPLY_LOOKANDFEEL", "plasma-apply-lookandfeel")
    try:
        return subprocess.run([command, "-a", THEMES[name]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


class Sync:
    def __init__(self):
        self.last_family = family()
        self.last_plasma = plasma()
        # at sign-in Plasma's own choice wins: you may have changed it in System Settings while nothing was watching
        if self.last_plasma and self.last_plasma != self.last_family:
            set_family(self.last_plasma)
            self.last_family = self.last_plasma

    def step(self) -> str:
        """One look; what was done ("plasma", "family" or "")."""
        f, p = family(), plasma()
        done = ""
        if f and f != self.last_family and f != p:       # an app switched: Plasma follows
            if apply_plasma(f):
                p = plasma() or f
                done = "plasma"
        elif p and p != self.last_plasma and p != f:     # System Settings switched to a Paragon theme: the apps follow
            set_family(p)
            f = p
            done = "family"
        self.last_family, self.last_plasma = f, p
        return done


def main(argv: list[str]) -> int:
    sync = Sync()
    if "--once" in argv:
        print(sync.step())
        return 0
    while True:
        time.sleep(2)
        try:
            sync.step()
        except Exception:  # noqa: BLE001 - a bad moment (a file half-written) is tried again in two seconds
            pass


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
