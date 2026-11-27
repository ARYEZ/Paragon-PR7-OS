"""The Paragon apps in PR7-OS: each app's code, a launcher, a menu entry and its icon, and the file types it opens.

    python -m pr7os.apps FAMILY_DIR ROOT     FAMILY_DIR holds the app repositories (paragon-pr7-e, ...)

Layout in the image:
    /opt/paragon/apps/paragon-pr7-<x>/pr7<x>/    the app's package (no tests, no Windows installer)
    /opt/paragon/requirements.txt                 every app's Python packages, merged (a hook builds the venv)
    /opt/paragon/venv/                            one Python environment for all of them (built in the image)
    /usr/bin/pr7-<x>                              the launcher
    /usr/share/applications/pr7-<x>.desktop       the menu entry
    /usr/share/icons/hicolor/256x256/apps/paragon-pr7-<x>.png
    /etc/xdg/mimeapps.list                        folders, images, PDFs, media, text, archives: the family's apps
    /usr/share/kglobalaccel/pr7-<x>.desktop       apps with Plasma shortcuts (Plasma registers the X-KDE-Shortcuts of
                                                  menu entries found here: Spectacle's way to own Print)
    /etc/xdg/autostart/paragon-pr7-<x>.desktop    apps that start at sign-in (PR7-Q, as Greenshot does)

Every family app is here but PR7-U (it installs Windows setups; PR7-OS Update does that job here).
"""
from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class App:
    letter: str
    name: str                      # in the menu: "Paragon PR7-E Files"
    generic: str                   # what it is
    categories: str
    files: bool = False            # takes files / folders on its command line (%F)
    mime: tuple[str, ...] = field(default_factory=tuple)
    default_for: tuple[str, ...] = field(default_factory=tuple)   # the system opens these with it
    actions: tuple[tuple[str, str, str, str], ...] = field(default_factory=tuple)  # (id, name, arguments, shortcut)
    autostart: str = ""            # arguments it starts with at sign-in ("" = it doesn't)

    @property
    def key(self) -> str:
        return self.letter.lower()

    @property
    def package(self) -> str:
        return f"pr7{self.key}"

    @property
    def repo(self) -> str:
        return f"paragon-pr7-{self.key}"

    @property
    def command(self) -> str:
        return f"pr7-{self.key}"


IMAGES = ("image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp", "image/tiff", "image/avif", "image/heic")
VIDEO = ("video/mp4", "video/x-matroska", "video/webm", "video/x-msvideo", "video/quicktime", "video/mpeg")
AUDIO = ("audio/mpeg", "audio/flac", "audio/ogg", "audio/x-wav", "audio/mp4", "audio/aac", "audio/x-opus+ogg")
TEXT = ("text/plain", "text/markdown", "text/x-python", "application/x-shellscript", "text/x-csrc", "text/x-c++src",
        "application/json", "application/xml", "text/css", "text/html", "application/x-yaml")
ARCHIVES = ("application/zip", "application/x-7z-compressed", "application/x-rar", "application/vnd.rar",
            "application/x-tar", "application/x-compressed-tar", "application/x-xz-compressed-tar",
            "application/x-bzip-compressed-tar", "application/gzip", "application/x-xz", "application/zstd")

APPS = [
    App("E", "Files", "File Manager", "System;FileTools;FileManager;", True, ("inode/directory",),
        ("inode/directory",)),
    App("W", "Text", "Text Editor", "Utility;TextEditor;", True, TEXT, TEXT),
    App("TM", "Terminal", "Terminal", "System;TerminalEmulator;"),
    App("M", "Media", "Media Player", "AudioVideo;Player;Video;Audio;", True, VIDEO + AUDIO, VIDEO + AUDIO),
    App("P", "Images", "Image Viewer", "Graphics;Viewer;", True, IMAGES, IMAGES),
    App("R", "PDF", "PDF Reader", "Office;Viewer;", True, ("application/pdf",), ("application/pdf",)),
    App("Z", "Archives", "Archive Manager", "Utility;Archiving;Compression;", True, ARCHIVES, ARCHIVES),
    App("F", "Transfers", "File Transfer", "Network;FileTransfer;"),
    App("PM", "Passwords", "Password Manager", "Utility;Security;", True, ("application/x-keepass2",),
        ("application/x-keepass2",)),
    App("HB", "Video", "Video Converter", "AudioVideo;Video;AudioVideoEditing;", True, VIDEO),
    App("L", "Tags", "Tag Editor", "AudioVideo;Audio;", True, AUDIO),
    App("BK", "Backups", "Backups", "Utility;Archiving;"),
    App("FS", "Sync", "Folder Sync", "Utility;", True),
    App("DU", "Disk usage", "Disk Usage", "System;Utility;Filesystem;", True),
    App("HW", "Hardware", "Hardware Information", "System;Monitor;"),
    App("SM", "System", "System Monitor", "System;Monitor;"),
    App("DB", "Database", "SQLite Browser", "Development;Database;", True,
        ("application/vnd.sqlite3", "application/x-sqlite3")),
    App("HX", "Hex", "Hex Editor", "Development;Utility;", True),
    App("WM", "Compare", "File Compare", "Development;Utility;", True),
    App("Q", "Screenshots", "Screenshot Tool", "Graphics;Utility;",
        actions=(("region", "Capture region", "--region", "Print"),
                 ("lastregion", "Capture last region", "--last-region", "Shift+Print"),
                 ("window", "Capture window", "--window", "Alt+Print"),
                 ("full", "Capture full screen", "--full", "Ctrl+Print")),
        autostart="--tray"),
    App("IS", "Search", "File Search", "System;Utility;Filesystem;",
        actions=(("search", "Search files", "", "Ctrl+Alt+Space"),), autostart="--index-service"),
    App("LN", "Launcher", "Launcher", "Utility;",
        actions=(("show", "Open the launcher", "", "Alt+Space"),), autostart="--tray"),
    App("CB", "Clipboard", "Clipboard History", "Utility;",
        actions=(("show", "Show clips", "", "Ctrl+`"),), autostart="--tray"),
    App("AR", "Startup", "Startup Manager", "System;Settings;"),
    App("UN", "Uninstaller", "Uninstaller", "System;Settings;PackageManager;"),
]

# Plasma's own defaults that PR7-OS changes for its apps (/etc/xdg/kglobalshortcutsrc: what a new account starts with):
# KRunner keeps Alt+F2 and the Search key, and Alt+Space goes to PR7-LN (Flow Launcher's key); Spectacle gives the
# Print keys to PR7-Q (setup_look.py also diverts Spectacle's kglobalaccel entry, for accounts made before).
SHORTCUT_DEFAULTS = """[services][org.kde.krunner.desktop]
_launch=Alt+F2\tSearch

[services][org.kde.spectacle.desktop]
_launch=none
FullScreenScreenShot=none
RectangularRegionScreenShot=none
ActiveWindowScreenShot=none
WindowUnderCursorScreenShot=none
CurrentMonitorScreenShot=none
OpenWithoutScreenshot=none
RecordRegion=none
RecordScreen=none
RecordWindow=none
"""

LEFT_OUT = {"U": "family installer: Windows setups (PR7-OS Update does its job here)"}


# The apps' text in Bebas Neue on PR7-OS (the owner's choice) without touching their code: their own Inter isn't
# packaged here, and their launcher gives them this font configuration, where Inter is hidden and a request for it
# answers with Bebas Neue (Qt asks fontconfig for a family it can't find). Monospaced fonts are left as they are.
FONTS_APPS = """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<!-- Paragon PR7-OS: the Paragon apps' fonts (their launchers set FONTCONFIG_FILE to this file) -->
<fontconfig>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
  <selectfont><rejectfont><pattern><patelt name="family"><string>Inter</string></patelt></pattern></rejectfont></selectfont>
  <match target="pattern">
    <test qual="any" name="family"><string>Inter</string></test>
    <edit name="family" mode="assign" binding="strong"><string>Bebas Neue</string></edit>
  </match>
</fontconfig>
"""


def launcher(app: App) -> str:
    return (f"#!/bin/sh\n# Paragon PR7-{app.letter} ({app.generic}) on PR7-OS\n"
            f"export PYTHONPATH=/opt/paragon/apps/{app.repo}\n"
            "# their text in Bebas Neue, unless you chose Inter (Paragon Welcome > FONT)\n"
            '[ "$(cat "${XDG_CONFIG_HOME:-$HOME/.config}/paragon/font" 2>/dev/null)" = inter ] || '
            "export FONTCONFIG_FILE=/etc/paragon/fonts-apps.conf\n"
            f'exec /opt/paragon/venv/bin/python -m {app.package} "$@"\n')


def desktop_entry(app: App) -> str:
    lines = ["[Desktop Entry]", "Type=Application", f"Name=PR7-{app.letter} {app.name}",
             f"GenericName={app.generic}", f"Comment=Paragon PR7-{app.letter}: {app.generic.lower()}",
             f"Exec={app.command}" + (" %F" if app.files else ""), f"Icon=paragon-pr7-{app.key}",
             f"Categories={app.categories}", "Terminal=false", f"StartupWMClass={app.package}",
             "X-KDE-Paragon=true"]
    if app.mime:
        lines.append("MimeType=" + ";".join(app.mime) + ";")
    if app.actions:
        lines.append("Actions=" + ";".join(a[0] for a in app.actions) + ";")
        for ident, name, args, shortcut in app.actions:
            lines += ["", f"[Desktop Action {ident}]", f"Name={name}", f"Exec={app.command} {args}".rstrip()]
            if shortcut:
                lines.append(f"X-KDE-Shortcuts={shortcut}")
    return "\n".join(lines) + "\n"


def autostart_entry(app: App) -> str:
    return ("[Desktop Entry]\nType=Application\n"
            f"Name=PR7-{app.letter} {app.name}\nComment=Paragon PR7-{app.letter} at sign-in (switch it off in its "
            f"Preferences)\nExec={app.command} {app.autostart}\nIcon=paragon-pr7-{app.key}\nTerminal=false\n"
            "X-KDE-autostart-phase=2\n")


def mimeapps() -> str:
    out = ["[Default Applications]"]
    for app in APPS:
        out += [f"{m}={app.command}.desktop" for m in app.default_for]
    out += ["", "[Added Associations]"]
    for app in APPS:
        out += [f"{m}={app.command}.desktop;" for m in app.mime]
    return "\n".join(out) + "\n"


def requirements(family: Path) -> list[str]:
    """Every app's requirements, merged: the strictest lower bound of each package, Windows-only ones left out."""
    best: dict[str, tuple[tuple[int, ...], str]] = {}
    for app in APPS:
        for line in (family / app.repo / "requirements.txt").read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if not line or "win32" in line:
                continue
            m = re.match(r"([A-Za-z0-9_.\-]+)\s*(?:>=\s*([\d.]+))?", line)
            name, ver = m.group(1), m.group(2) or "0"
            key = name.lower()
            v = tuple(int(x) for x in ver.split("."))
            if key not in best or v > best[key][0]:
                best[key] = (v, f"{name}>={ver}" if ver != "0" else name)
    return sorted(spec for _v, spec in best.values())


def stage(family: Path, root: Path) -> list[Path]:
    """Copy every app into `root` (the image's filesystem) with its launcher, menu entry and icon."""
    out: list[Path] = []
    for app in APPS:
        src = family / app.repo / app.package
        if not (src / "__main__.py").exists():
            raise FileNotFoundError(f"{src}/__main__.py: is {app.repo} checked out?")
        dest = root / "opt/paragon/apps" / app.repo / app.package
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "Inter-*.ttf"))
        for extra in ("LICENSE", "NOTICE.md", "README.md"):
            if (family / app.repo / extra).exists():
                shutil.copy2(family / app.repo / extra, dest.parent / extra)
        exe = root / "usr/bin" / app.command
        exe.parent.mkdir(parents=True, exist_ok=True)
        exe.write_text(launcher(app), encoding="utf-8")
        exe.chmod(0o755)
        entry = root / "usr/share/applications" / f"{app.command}.desktop"
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text(desktop_entry(app), encoding="utf-8")
        icon = root / "usr/share/icons/hicolor/256x256/apps" / f"paragon-pr7-{app.key}.png"
        icon.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / "icons" / "app.png", icon)
        out += [dest, exe, entry, icon]
        if any(a[3] for a in app.actions):          # Plasma takes the shortcuts of entries it finds here
            keys = root / "usr/share/kglobalaccel" / f"{app.command}.desktop"
            keys.parent.mkdir(parents=True, exist_ok=True)
            keys.write_text(desktop_entry(app), encoding="utf-8")
            out.append(keys)
        if app.autostart:
            auto = root / "etc/xdg/autostart" / f"paragon-pr7-{app.key}.desktop"
            auto.parent.mkdir(parents=True, exist_ok=True)
            auto.write_text(autostart_entry(app), encoding="utf-8")
            out.append(auto)
    req = root / "opt/paragon/requirements.txt"
    req.parent.mkdir(parents=True, exist_ok=True)
    req.write_text("\n".join(requirements(family)) + "\n", encoding="utf-8")
    fonts = root / "etc/paragon/fonts-apps.conf"
    fonts.parent.mkdir(parents=True, exist_ok=True)
    fonts.write_text(FONTS_APPS, encoding="utf-8")
    keys = root / "etc/xdg/kglobalshortcutsrc"
    keys.write_text(SHORTCUT_DEFAULTS, encoding="utf-8")
    mime = root / "etc/xdg/mimeapps.list"
    mime.parent.mkdir(parents=True, exist_ok=True)
    mime.write_text(mimeapps(), encoding="utf-8")
    return out + [req, fonts, keys, mime]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    family, root = Path(argv[0]), Path(argv[1])
    files = stage(family, root)
    print(f"{len(APPS)} apps staged under {root} ({len(files)} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
