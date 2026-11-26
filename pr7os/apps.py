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

Only apps that work on Linux are here. Left out (Windows-only for now): PR7-AR (Autoruns), PR7-UN (uninstaller),
PR7-U (Windows installers), PR7-CB / PR7-LN / PR7-Q / PR7-IS (global keys, Wayland screenshots, the NTFS index).
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
]

LEFT_OUT = {"AR": "Autoruns: Windows' startup places", "UN": "uninstaller: Windows programs",
            "U": "family installer: Windows setups", "CB": "clipboard history: global keys, Wayland's clipboard",
            "LN": "launcher: global keys (Plasma has KRunner)", "Q": "screenshots: Wayland's screenshot portal",
            "IS": "file search: the NTFS index"}


def launcher(app: App) -> str:
    return (f"#!/bin/sh\n# Paragon PR7-{app.letter} ({app.generic}) on PR7-OS\n"
            f"export PYTHONPATH=/opt/paragon/apps/{app.repo}\n"
            f'exec /opt/paragon/venv/bin/python -m {app.package} "$@"\n')


def desktop_entry(app: App) -> str:
    lines = ["[Desktop Entry]", "Type=Application", f"Name=PR7-{app.letter} {app.name}",
             f"GenericName={app.generic}", f"Comment=Paragon PR7-{app.letter}: {app.generic.lower()}",
             f"Exec={app.command}" + (" %F" if app.files else ""), f"Icon=paragon-pr7-{app.key}",
             f"Categories={app.categories}", "Terminal=false", f"StartupWMClass={app.package}",
             "X-KDE-Paragon=true"]
    if app.mime:
        lines.append("MimeType=" + ";".join(app.mime) + ";")
    return "\n".join(lines) + "\n"


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
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
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
    req = root / "opt/paragon/requirements.txt"
    req.parent.mkdir(parents=True, exist_ok=True)
    req.write_text("\n".join(requirements(family)) + "\n", encoding="utf-8")
    mime = root / "etc/xdg/mimeapps.list"
    mime.parent.mkdir(parents=True, exist_ok=True)
    mime.write_text(mimeapps(), encoding="utf-8")
    return out + [req, mime]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    family, root = Path(argv[0]), Path(argv[1])
    files = stage(family, root)
    print(f"{len(APPS)} apps staged under {root} ({len(files)} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
