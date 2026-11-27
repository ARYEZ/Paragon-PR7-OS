"""PR7-OS as Debian packages: what the ISO installs and what the update channel delivers (the same files).

    python3 -m pr7os.packages --root ROOT --out DIR [--venv /opt/paragon/venv] [--version X.Y.Z]

ROOT is the generated tree (pr7os.assets + pr7os.apps); --venv the apps' Python environment, built at its final path
(/opt/paragon/venv) with Debian 13's python3. Writes paragon-pr7os-{look,apps,updates}_<version>_all.deb,
paragon-pr7os-python_<version>_amd64.deb and pr7os-update.json (each package's version, file, SHA-256 and size), which
the updater reads from the release. Standard library and dpkg-deb only (it runs in the Debian build container).

    look      every theme file (colour schemes, decoration, wallpaper, global themes, SDDM, Plymouth, GRUB, lock screen,
              /etc/xdg defaults) and setup_look.py, run by its postinst (and by dpkg triggers on Plasma's updates)
    apps      the Paragon apps, their launchers, menu entries, icons, file associations
    python    the apps' environment; its version is a hash of what it holds, so an update only downloads it when the
              apps' requirements change
    updates   the updater: the daily check, the notification, the update window, the root helper, polkit, systemd
    system    what a desktop needs beyond Plasma, as the Debian packages it depends on (names on the network, printing,
              security updates, command-line basics, the firewall, Flatpak with Flathub, Vulkan for games), and
              setup_system.py, run by its postinst (the firewall once, Flathub)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import __version__

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
MAINTAINER = "Paragon PR7-OS <pr7os@users.noreply.github.com>"
HOMEPAGE = "https://github.com/ARYEZ/Paragon-PR7-OS"
MANIFEST = "pr7os-update.json"
UPDATER_FILES = {   # the updater's files: path in the image -> source in pr7os/static/updater
    "usr/bin/pr7os-update": "pr7os-update",
    "usr/libexec/paragon/pr7os-update-helper": "pr7os-update-helper",
    "usr/share/paragon/update/pr7os_update.py": "pr7os_update.py",
    "usr/share/paragon/update/window.py": "window.py",
    "usr/share/polkit-1/actions/org.paragon.pr7os.update.policy": "org.paragon.pr7os.update.policy",
    "usr/lib/systemd/user/pr7os-update-check.service": "pr7os-update-check.service",
    "usr/lib/systemd/user/pr7os-update-check.timer": "pr7os-update-check.timer",
    "usr/share/applications/pr7os-update.desktop": "pr7os-update.desktop",
}
SYSTEM_FILES = {    # the system package's own files -> source in pr7os/static/system
    "usr/share/paragon/setup_system.py": "setup_system.py",
    "usr/bin/pr7os-steam": "pr7os-steam",
    "usr/share/applications/pr7os-steam.desktop": "pr7os-steam.desktop",
    "etc/apt/apt.conf.d/52paragon-auto-upgrades": "52paragon-auto-upgrades",
}
EXECUTABLE = {"usr/bin/pr7os-update", "usr/libexec/paragon/pr7os-update-helper", "usr/bin/pr7os-steam"}


def is_app_file(rel: str) -> bool:
    return (rel.startswith(("opt/paragon/apps/", "usr/bin/pr7-")) or rel == "opt/paragon/requirements.txt"
            or rel in ("etc/xdg/mimeapps.list", "etc/xdg/kglobalshortcutsrc")
            or (rel.startswith("usr/share/applications/pr7-") and rel.endswith(".desktop"))
            or rel.startswith("usr/share/icons/hicolor/256x256/apps/paragon-pr7-")
            or rel.startswith(("usr/share/kglobalaccel/pr7-", "etc/xdg/autostart/paragon-pr7-")))


def split(root: Path) -> dict[str, list[str]]:
    """The generated tree's files by package (the venv and the updater come from elsewhere)."""
    out: dict[str, list[str]] = {"paragon-pr7os-look": [], "paragon-pr7os-apps": []}
    for f in sorted(p for p in root.rglob("*") if p.is_file() or p.is_symlink()):
        rel = f.relative_to(root).as_posix()
        if rel.startswith("opt/paragon/venv/") or rel in UPDATER_FILES or rel in SYSTEM_FILES:
            continue
        out["paragon-pr7os-apps" if is_app_file(rel) else "paragon-pr7os-look"].append(rel)
    return out


def python_version(venv: Path) -> str:
    """The environment's version: what it holds (every installed distribution and its version), hashed."""
    dists = sorted(p.name for p in venv.glob("lib/python3*/site-packages/*.dist-info"))
    digest = hashlib.sha256("\n".join(dists).encode()).hexdigest()[:12]
    return f"1+{digest}"


SCRIPTS = {
    "paragon-pr7os-look": {
        "postinst": """#!/bin/sh
set -e
case "$1" in
    configure|triggered) python3 /usr/share/paragon/setup_look.py configure ;;
esac
""",
        "prerm": """#!/bin/sh
set -e
case "$1" in
    remove|deconfigure) python3 /usr/share/paragon/setup_look.py remove ;;
esac
""",
        # Plasma's own updates (its lock screen, the components it uses, Breeze Dark) re-apply the look to them
        "triggers": """interest-noawait /usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen
interest-noawait /usr/share/plasma/desktoptheme/breeze-dark
interest-noawait /usr/lib/x86_64-linux-gnu/qt6/qml/org/kde/breeze/components
""",
    },
    "paragon-pr7os-apps": {
        "postinst": """#!/bin/sh
set -e
case "$1" in
    configure)
        update-desktop-database -q /usr/share/applications || true
        gtk-update-icon-cache -f -q /usr/share/icons/hicolor || true
        ;;
esac
""",
    },
    "paragon-pr7os-system": {
        "postinst": """#!/bin/sh
set -e
case "$1" in
    configure) python3 /usr/share/paragon/setup_system.py configure || true ;;
esac
""",
    },
    "paragon-pr7os-updates": {
        "postinst": """#!/bin/sh
set -e
case "$1" in
    configure) systemctl --global enable pr7os-update-check.timer || true ;;
esac
""",
        "prerm": """#!/bin/sh
set -e
case "$1" in
    remove|deconfigure) systemctl --global disable pr7os-update-check.timer || true ;;
esac
""",
    },
}

CONTROL = {
    "paragon-pr7os-look": ("all", "python3, plasma-workspace, sddm, plymouth, grub-common, dpkg",
                           "Paragon PR7-OS's look",
                           "The family look for Debian's KDE Plasma: colour schemes, window decoration, wallpaper,\n"
                           " global themes, login screen, lock screen, boot splash and boot menu."),
    "paragon-pr7os-apps": ("all", "paragon-pr7os-python, python3, 7zip, restic, handbrake-cli, libxcb-cursor0, "
                                  "libpulse0, libegl1, libgl1, libxkbcommon-x11-0, libfontconfig1",
                           "The Paragon apps",
                           "Files, Text, Terminal, Media, Images, PDF, Archives and the rest of the Paragon family,\n"
                           " in the menu, with the family's file associations."),
    "paragon-pr7os-python": ("amd64", "python3 (>= 3.13), python3 (<< 3.14)",
                             "The Paragon apps' Python environment",
                             "Qt (PySide6, PyQt6) and the other Python packages the Paragon apps use."),
    "paragon-pr7os-system": ("all", "python3, avahi-daemon, libnss-mdns, cups, print-manager, unattended-upgrades, "
                                    "curl, wget, git, unzip, htop, ufw, plasma-firewall, flatpak, "
                                    "plasma-discover-backend-flatpak, mesa-vulkan-drivers, gamemode, xdg-utils",
                             "Paragon PR7-OS system",
                             "What PR7-OS adds to Debian's Plasma: names on the network (name.local), printing, Debian's\n"
                             " security fixes by themselves, command-line basics, the firewall, Flatpak with Flathub\n"
                             " in Discover, and Vulkan for games (Steam from Flathub)."),
    "paragon-pr7os-updates": ("all", "python3, pkexec, libnotify-bin, systemd",
                              "Paragon PR7-OS updates",
                              "Checks GitHub for new PR7-OS releases once a day, says so, and installs them."),
}


def build_deb(name: str, version: str, files: dict[str, Path], out: Path) -> Path:
    """One package: `files` maps the path in the system to its source (symlinks kept)."""
    arch, depends, short, long = CONTROL[name]
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "pkg"
        for rel, src in files.items():
            dest = tree / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if src.is_symlink():
                dest.symlink_to(src.readlink())
            else:
                shutil.copy2(src, dest)
                dest.chmod(0o755 if (rel in EXECUTABLE or rel.startswith(("usr/bin/", "opt/paragon/venv/bin/"))
                                     or src.stat().st_mode & 0o111) else 0o644)
        debian = tree / "DEBIAN"
        debian.mkdir(parents=True)
        size_kb = sum(f.stat().st_size for f in tree.rglob("*") if f.is_file() and not f.is_symlink()) // 1024 + 1
        (debian / "control").write_text(
            f"Package: {name}\nVersion: {version}\nArchitecture: {arch}\nMaintainer: {MAINTAINER}\n"
            f"Installed-Size: {size_kb}\nDepends: {depends}\nSection: misc\nPriority: optional\n"
            f"Homepage: {HOMEPAGE}\nDescription: {short}\n {long}\n", encoding="utf-8")
        conffiles = sorted("/" + rel for rel in files if rel.startswith("etc/"))
        if conffiles:                           # changes made there survive updates (dpkg asks, or keeps them)
            (debian / "conffiles").write_text("\n".join(conffiles) + "\n", encoding="utf-8")
        for script, body in SCRIPTS.get(name, {}).items():
            (debian / script).write_text(body, encoding="utf-8")
            (debian / script).chmod(0o644 if script == "triggers" else 0o755)
        deb = out / f"{name}_{version}_{arch}.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(tree), str(deb)], check=True,
                       stdout=subprocess.DEVNULL)
    return deb


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(root: Path, out: Path, version: str = __version__, venv: Path | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    parts = split(root)
    debs = [build_deb(name, version, {rel: root / rel for rel in rels}, out) for name, rels in parts.items()]
    debs.append(build_deb("paragon-pr7os-updates", version,
                          {rel: STATIC / "updater" / src for rel, src in UPDATER_FILES.items()}, out))
    debs.append(build_deb("paragon-pr7os-system", version,
                          {rel: STATIC / "system" / src for rel, src in SYSTEM_FILES.items()}, out))
    if venv is not None:
        files = {}
        for f in sorted(p for p in venv.rglob("*") if p.is_file() or p.is_symlink()):
            if "__pycache__" in f.parts and f.suffix != ".pyc":
                continue
            files[(Path("opt/paragon/venv") / f.relative_to(venv)).as_posix()] = f
        debs.append(build_deb("paragon-pr7os-python", python_version(venv), files, out))
    manifest = {"version": version, "packages": []}
    for deb in debs:
        name, pkg_version, _arch = deb.stem.split("_")
        manifest["packages"].append({"name": name, "version": pkg_version, "file": deb.name,
                                     "sha256": sha256(deb), "size": deb.stat().st_size})
    (out / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--venv", type=Path)
    ap.add_argument("--version", default=__version__)
    a = ap.parse_args(argv)
    manifest = build(a.root, a.out, a.version, a.venv)
    for p in manifest["packages"]:
        print(f"{p['file']}  {p['size'] // 1024} kB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
