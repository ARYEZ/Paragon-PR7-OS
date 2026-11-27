#!/usr/bin/env python3
"""What the paragon-pr7os-look package does once its files are in place (its postinst), and undoes on removal.

    python3 setup_look.py configure [--strict]     after installing or updating (and on Plasma's own updates)
    python3 setup_look.py remove                   the package's removal: Plasma's, GRUB's and Debian's own back

Every step can run any number of times (each update runs it again):
- the "paragon" Plasma style: Breeze Dark's art (copied from the installed Plasma, so it always matches it) with the
  family's colours (/usr/share/paragon/plasma-colors): the panel and launcher stay dark in both finishes;
- font and icon caches, the menu's desktop entries;
- the boot menu's fonts (grub-fonts.py), and on an installed system update-grub;
- the boot splash (Plymouth) and the initramfs that shows it (installed systems only: the ISO's build makes its own);
- the lock screen's look (lockscreen.py; --strict stops on a Plasma it doesn't recognise, as the ISO's build wants);
- the system's name: Debian's os-release diverted, NAME / PRETTY_NAME / LOGO Paragon's, ID still "debian".
Standard library only: it runs with Debian's python3, before or without the apps' environment.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SHARE = Path("/usr/share/paragon")
STYLE = Path("/usr/share/plasma/desktoptheme/paragon")
BREEZE_DARK = Path("/usr/share/plasma/desktoptheme/breeze-dark")
GRUB_THEME = Path("/usr/share/grub/themes/paragon")
OS_RELEASE = Path("/usr/lib/os-release")
OS_RELEASE_DEBIAN = Path("/usr/lib/os-release.debian")
NAMES = {"NAME": '"Paragon PR7-OS"', "PRETTY_NAME": '"Paragon PR7-OS (based on Debian 13)"', "LOGO": "pr7os",
         "HOME_URL": '"https://github.com/ARYEZ/Paragon-PR7-OS"',
         "SUPPORT_URL": '"https://github.com/ARYEZ/Paragon-PR7-OS/issues"',
         "BUG_REPORT_URL": '"https://github.com/ARYEZ/Paragon-PR7-OS/issues"'}


def run(*cmd: str, check: bool = False) -> int:
    """A step's command; a missing tool (a minimal system) is skipped, not fatal, unless check."""
    if not shutil.which(cmd[0]):
        print(f"setup: {cmd[0]} isn't installed, skipped")
        return 0
    done = subprocess.run(list(cmd))
    if check and done.returncode:
        raise SystemExit(f"setup: {' '.join(cmd)} failed")
    return done.returncode


def installed_system() -> bool:
    """A real installed system (GRUB set up on a disk), not the ISO's build or a container."""
    return Path("/boot/grub/grub.cfg").exists() and not Path("/run/live").exists()


def plasma_style() -> None:
    src = BREEZE_DARK if BREEZE_DARK.is_dir() else Path("/usr/share/plasma/desktoptheme/default")
    if not src.is_dir():
        print("setup: no Plasma style to start from, skipped")
        return
    if STYLE.exists():
        shutil.rmtree(STYLE)
    shutil.copytree(src, STYLE, symlinks=True)
    shutil.copy2(SHARE / "plasma-colors", STYLE / "colors")
    meta = STYLE / "metadata.json"
    if meta.exists():
        m = json.loads(meta.read_text(encoding="utf-8"))
        kp = m.setdefault("KPlugin", {})
        kp.update({"Id": "paragon", "Name": "Paragon", "Description": "Breeze's art in the Paragon family's colours"})
        for k in [k for k in kp if k.startswith(("Name[", "Description["))]:
            del kp[k]
        meta.write_text(json.dumps(m, indent=2), encoding="utf-8")
    desk = STYLE / "metadata.desktop"
    if desk.exists():
        t = desk.read_text(encoding="utf-8")
        t = re.sub(r"^Name(\[.*\])?=.*$", "", t, flags=re.M)
        t = re.sub(r"^X-KDE-PluginInfo-Name=.*$", "X-KDE-PluginInfo-Name=paragon", t, flags=re.M)
        desk.write_text(t.replace("[Desktop Entry]", "[Desktop Entry]\nName=Paragon", 1), encoding="utf-8")


def os_release() -> None:
    listed = subprocess.run(["dpkg-divert", "--list", str(OS_RELEASE)], capture_output=True, text=True).stdout
    if "paragon" not in listed:
        subprocess.run(["dpkg-divert", "--package", "paragon", "--divert", str(OS_RELEASE_DEBIAN), "--rename",
                        "--add", str(OS_RELEASE)], check=True)
    keep = dict(re.findall(r"^(\w+)=(.*)$", OS_RELEASE_DEBIAN.read_text(encoding="utf-8"), re.M))
    keep.update(NAMES)
    OS_RELEASE.write_text("".join(f"{k}={v}\n" for k, v in keep.items()), encoding="utf-8")


def configure(strict: bool) -> None:
    plasma_style()
    run("fc-cache", "-f")
    run("gtk-update-icon-cache", "-f", "-q", "/usr/share/icons/hicolor")
    run("update-desktop-database", "-q", "/usr/share/applications")
    if shutil.which("grub-mkfont"):
        subprocess.run([sys.executable, str(SHARE / "grub-fonts.py"), str(GRUB_THEME),
                        "/usr/share/fonts/truetype/paragon-inter"], check=True)
    lock = [sys.executable, str(SHARE / "lockscreen.py")] + (["--strict"] if strict else [])
    subprocess.run(lock, check=True)
    os_release()
    if shutil.which("plymouth-set-default-theme"):
        run("plymouth-set-default-theme", "paragon")
    if installed_system():
        run("update-initramfs", "-u")
        run("update-grub")


def remove() -> None:
    subprocess.run([sys.executable, str(SHARE / "lockscreen.py"), "--restore"], check=False)
    if STYLE.exists():
        shutil.rmtree(STYLE)
    for pf2 in GRUB_THEME.glob("*.pf2"):
        pf2.unlink()
    listed = subprocess.run(["dpkg-divert", "--list", str(OS_RELEASE)], capture_output=True, text=True).stdout
    if "paragon" in listed:
        OS_RELEASE.unlink(missing_ok=True)
        subprocess.run(["dpkg-divert", "--package", "paragon", "--rename", "--remove", str(OS_RELEASE)], check=True)
    if shutil.which("plymouth-set-default-theme"):
        run("plymouth-set-default-theme", "--reset")
    if installed_system():
        run("update-initramfs", "-u")
        run("update-grub")


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("configure", "remove"):
        print(__doc__)
        return 2
    os.umask(0o022)
    if argv[0] == "configure":
        configure("--strict" in argv)
    else:
        remove()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
