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
- the system's name: Debian's os-release diverted, NAME / PRETTY_NAME / LOGO Paragon's, ID still "debian";
- the account picture: accounts with no picture, or still Debian's (byte for byte a file Debian ships), get Paragon's
  (AccountsService's icon, which the login and lock screens read, and ~/.face.icon); a picture you chose is never
  touched. New accounts get it from /etc/skel: Debian's /etc/skel/.face(.icon) (desktop-base's swirl) is diverted to
  /etc/paragon/skel-orig (outside skel, or every new account would get copies) and replaced by a link to Paragon's.
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


# --------------------------------------------------------------------------- Print belongs to PR7-Q
SPECTACLE_KEYS = Path("/usr/share/kglobalaccel/org.kde.spectacle.desktop")
SPECTACLE_OFF = Path("/usr/share/kglobalaccel/org.kde.spectacle.desktop.paragon-off")


def spectacle_keys_off() -> None:
    """Plasma gives an app the shortcuts of its entry in /usr/share/kglobalaccel: Spectacle's claims Print (and Shift /
    Meta+Print), which are PR7-Q's on PR7-OS. Its entry is diverted aside (kglobalaccel only reads *.desktop there);
    Spectacle itself stays installed and in the menu."""
    listed = subprocess.run(["dpkg-divert", "--list", str(SPECTACLE_KEYS)], capture_output=True, text=True).stdout \
        if shutil.which("dpkg-divert") else ""
    if "paragon" in listed or not (SPECTACLE_KEYS.exists() or SPECTACLE_KEYS.is_symlink()):
        return
    subprocess.run(["dpkg-divert", "--package", "paragon", "--divert", str(SPECTACLE_OFF), "--rename", "--add",
                    str(SPECTACLE_KEYS)], check=True)


def spectacle_keys_on() -> None:
    if not shutil.which("dpkg-divert"):
        return
    listed = subprocess.run(["dpkg-divert", "--list", str(SPECTACLE_KEYS)], capture_output=True, text=True).stdout
    if "paragon" in listed:
        subprocess.run(["dpkg-divert", "--package", "paragon", "--rename", "--remove", str(SPECTACLE_KEYS)], check=True)


KRUNNER_KEYS = Path("/usr/share/kglobalaccel/org.kde.krunner.desktop")
KRUNNER_ORIG = Path("/usr/share/kglobalaccel/org.kde.krunner.desktop.paragon-orig")


def krunner_keys() -> None:
    """Alt+Space is PR7-LN's on PR7-OS (Flow Launcher's key); KRunner keeps Alt+F2 and the Search key. Its kglobalaccel
    entry (the 0.4.0 boot test: an /etc/xdg default didn't move it) is diverted, and a copy whose X-KDE-Shortcuts
    leave Alt+Space out takes its place; Plasma's own updates re-run this through the look's dpkg trigger."""
    if not shutil.which("dpkg-divert"):
        return
    listed = subprocess.run(["dpkg-divert", "--list", str(KRUNNER_KEYS)], capture_output=True, text=True).stdout
    if "paragon" not in listed:
        if not (KRUNNER_KEYS.exists() or KRUNNER_KEYS.is_symlink()):
            return
        subprocess.run(["dpkg-divert", "--package", "paragon", "--divert", str(KRUNNER_ORIG), "--rename", "--add",
                        str(KRUNNER_KEYS)], check=True)
    if not KRUNNER_ORIG.exists():
        return
    lines = KRUNNER_ORIG.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        if line.startswith("X-KDE-Shortcuts="):
            keys = [k for k in line.split("=", 1)[1].split(",") if k.strip() and k.strip().lower() != "alt+space"]
            line = "X-KDE-Shortcuts=" + ",".join(keys or ["Alt+F2"])
        out.append(line)
    if KRUNNER_KEYS.is_symlink():
        KRUNNER_KEYS.unlink()
    KRUNNER_KEYS.write_text("\n".join(out) + "\n", encoding="utf-8")


def krunner_keys_back() -> None:
    if not shutil.which("dpkg-divert"):
        return
    listed = subprocess.run(["dpkg-divert", "--list", str(KRUNNER_KEYS)], capture_output=True, text=True).stdout
    if "paragon" in listed:
        KRUNNER_KEYS.unlink(missing_ok=True)
        subprocess.run(["dpkg-divert", "--package", "paragon", "--rename", "--remove", str(KRUNNER_KEYS)], check=True)


# --------------------------------------------------------------------------- LibreOffice's splash
LO_PROGRAM = Path(os.environ.get("PR7OS_LO_PROGRAM", "/usr/lib/libreoffice/program"))
LO_RC = Path(os.environ.get("PR7OS_LO_RC", "/etc/libreoffice/sofficerc"))
LO_ART = Path(os.environ.get("PR7OS_LO_ART", "/usr/share/paragon/libreoffice"))
LO_PICTURES = ("intro.png", "intro-highres.png")
# the progress bar under the splash (assets.LO_SPLASH: 640 x 300 at 1x): the family's orange on onyx, pearl text
LO_PROGRESS = {"Logo": "1", "NativeProgress": "false", "ProgressBarColor": "242,120,30",
               "ProgressFrameColor": "28,28,32", "ProgressTextColor": "232,232,234", "ProgressPosition": "40,262",
               "ProgressSize": "560,4", "ProgressTextBaseline": "250"}


def _orig(path: Path) -> Path:
    return path.with_name(path.name + ".paragon-orig")


def _divert(path: Path) -> bool:
    """LibreOffice's own file set aside (its updates go there too); False when there's nothing to set aside."""
    listed = subprocess.run(["dpkg-divert", "--list", str(path)], capture_output=True, text=True).stdout
    if "paragon" in listed:
        return True
    if not (path.exists() or path.is_symlink()):
        return False
    subprocess.run(["dpkg-divert", "--package", "paragon", "--divert", str(_orig(path)), "--rename", "--add",
                    str(path)], check=True)
    return True


def _undivert(path: Path) -> None:
    listed = subprocess.run(["dpkg-divert", "--list", str(path)], capture_output=True, text=True).stdout
    if "paragon" in listed:
        path.unlink(missing_ok=True)
        subprocess.run(["dpkg-divert", "--package", "paragon", "--rename", "--remove", str(path)], check=True)


def sofficerc(original: str) -> str:
    """LibreOffice's sofficerc with the splash's progress bar in the family's colours, everything else as it was."""
    out, seen = [], set()
    for line in original.splitlines():
        key = line.split("=", 1)[0].strip()
        if key in LO_PROGRESS:
            out.append(f"{key}={LO_PROGRESS[key]}")
            seen.add(key)
        else:
            out.append(line)
    missing = [f"{k}={v}" for k, v in LO_PROGRESS.items() if k not in seen]
    if missing:
        at = next((i + 1 for i, line in enumerate(out) if line.strip() == "[Bootstrap]"), None)
        if at is None:
            out = ["[Bootstrap]"] + missing + out
        else:
            out[at:at] = missing
    return "\n".join(out) + "\n"


def libreoffice_look() -> None:
    """LibreOffice's splash in the family look: its pictures and its sofficerc (the progress bar's colours: Debian's
    frame is green) set aside, ours in their place; its updates land on the set-aside copies and the look's dpkg
    trigger runs this again."""
    if not LO_PROGRAM.is_dir() or not shutil.which("dpkg-divert"):
        return
    for name in LO_PICTURES:
        target, ours = LO_PROGRAM / name, LO_ART / name
        if ours.exists() and _divert(target):
            if target.is_symlink():
                target.unlink()
            shutil.copyfile(ours, target)
    if _divert(LO_RC) and _orig(LO_RC).exists():
        if LO_RC.is_symlink():
            LO_RC.unlink()
        LO_RC.write_text(sofficerc(_orig(LO_RC).read_text(encoding="utf-8")), encoding="utf-8")


def libreoffice_back() -> None:
    if not shutil.which("dpkg-divert"):
        return
    for name in LO_PICTURES:
        _undivert(LO_PROGRAM / name)
    _undivert(LO_RC)


# --------------------------------------------------------------------------- the account picture
FACE = "usr/share/paragon/face.png"
DEBIAN_PICTURES = ("usr/share/desktop-base", "usr/share/pixmaps", "usr/share/images/desktop-base")


def accounts(root: Path) -> list[tuple[str, int, int, Path]]:
    """People's accounts (uid 1000-59999 with a home folder): name, uid, gid, home."""
    out = []
    try:
        lines = (root / "etc/passwd").read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        f = line.split(":")
        if len(f) >= 7 and f[2].isdigit() and 1000 <= int(f[2]) < 60000:
            home = root / f[5].lstrip("/")
            if home.is_dir():
                out.append((f[0], int(f[2]), int(f[3]), home))
    return out


SKEL_FACES = ("etc/skel/.face.icon", "etc/skel/.face")
SKEL_ORIG = "etc/paragon/skel-orig"          # same filesystem as /etc/skel (dpkg-divert --rename renames)


def skel_orig(root: Path, rel: str) -> Path:
    return root / SKEL_ORIG / Path(rel).name


def skel_faces(root: Path = Path("/")) -> None:
    """New accounts copy /etc/skel: Debian's pictures there (owned by desktop-base, which dpkg won't let another
    package overwrite) are diverted to .paragon-orig, and a link to Paragon's takes their place."""
    for rel in SKEL_FACES:
        path = root / rel
        if path.is_symlink() and os.readlink(path) == "/" + FACE:
            continue                                     # already Paragon's (every update runs this again)
        listed = subprocess.run(["dpkg-divert", "--list", "/" + rel], capture_output=True, text=True).stdout \
            if root == Path("/") and shutil.which("dpkg-divert") else ""
        if "paragon" not in listed and (path.exists() or path.is_symlink()):
            orig = skel_orig(root, rel)
            orig.parent.mkdir(parents=True, exist_ok=True)
            if root == Path("/") and shutil.which("dpkg-divert"):
                subprocess.run(["dpkg-divert", "--package", "paragon", "--divert", "/" + str(orig.relative_to(root)),
                                "--rename", "--add", "/" + rel], check=True)
            else:                                        # tests: a stand-in root, the same outcome
                path.rename(orig)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink() or path.exists():
            path.unlink()
        path.symlink_to("/" + FACE)


def unskel_faces(root: Path = Path("/")) -> None:
    for rel in SKEL_FACES:
        path = root / rel
        if path.is_symlink() and os.readlink(path) == "/" + FACE:
            path.unlink()
        if root == Path("/") and shutil.which("dpkg-divert"):
            listed = subprocess.run(["dpkg-divert", "--list", "/" + rel], capture_output=True, text=True).stdout
            if "paragon" in listed:
                subprocess.run(["dpkg-divert", "--package", "paragon", "--rename", "--remove", "/" + rel], check=True)
        else:
            orig = skel_orig(root, rel)
            if orig.exists() or orig.is_symlink():
                orig.rename(path)


def debian_pictures(root: Path) -> set[bytes]:
    found = set()
    for rel in SKEL_FACES:                               # what accounts made before PR7-OS's look copied from skel
        orig = skel_orig(root, rel)
        if orig.is_file():
            found.add(orig.read_bytes())
    for d in DEBIAN_PICTURES:
        for f in (root / d).rglob("*") if (root / d).is_dir() else []:
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg") and f.stat().st_size < 4_000_000:
                found.add(f.read_bytes())
    return found


def replaceable(path: Path, ours: bytes, debian: set[bytes]) -> bool:
    """No picture, a broken link, ours (refreshed), or byte for byte one of Debian's: not something you chose."""
    if not path.exists():
        return True
    try:
        data = path.read_bytes()
    except OSError:
        return False
    return data == ours or data in debian


def set_icon_line(user_file: Path, icon: str | None) -> None:
    """AccountsService's [User] Icon= line set (or removed), the rest of the file kept."""
    lines = user_file.read_text(encoding="utf-8").splitlines() if user_file.exists() else ["[User]"]
    lines = [l for l in lines if not l.startswith("Icon=")]
    if icon is not None:
        if "[User]" not in lines:
            lines.insert(0, "[User]")
        lines.insert(lines.index("[User]") + 1, f"Icon={icon}")
    user_file.parent.mkdir(parents=True, exist_ok=True)
    user_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def faces(root: Path = Path("/")) -> list[str]:
    face = root / FACE
    if not face.exists():
        return []
    ours, debian = face.read_bytes(), debian_pictures(root)
    given = []
    for name, uid, gid, home in accounts(root):
        acc = root / "var/lib/AccountsService"
        icon = acc / "icons" / name
        user_file = acc / "users" / name
        listed = ""
        if user_file.exists():
            m = re.search(r"^Icon=(.*)$", user_file.read_text(encoding="utf-8"), re.M)
            listed = m.group(1).strip() if m else ""
        listed_path = root / listed.lstrip("/") if listed else icon
        if not (replaceable(icon, ours, debian) and replaceable(listed_path, ours, debian)):
            continue                                     # a picture of your own
        icon.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(face, icon)
        set_icon_line(user_file, "/var/lib/AccountsService/icons/" + name)
        dot = home / ".face.icon"
        if dot.is_symlink() or replaceable(dot, ours, debian):
            dot.unlink(missing_ok=True)
            dot.symlink_to("/" + FACE)
            try:
                os.lchown(dot, uid, gid)
            except OSError:
                pass
        given.append(name)
    if given:
        run("systemctl", "try-restart", "accounts-daemon.service")      # it caches pictures
    return given


def unfaces(root: Path = Path("/")) -> None:
    face = root / FACE
    if not face.exists():
        return
    ours = face.read_bytes()
    for name, _uid, _gid, home in accounts(root):
        icon = root / "var/lib/AccountsService/icons" / name
        if icon.exists() and icon.read_bytes() == ours:
            icon.unlink()
            set_icon_line(root / "var/lib/AccountsService/users" / name, None)
        dot = home / ".face.icon"
        if dot.is_symlink() and os.readlink(dot) == "/" + FACE:
            dot.unlink()


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
    spectacle_keys_off()
    krunner_keys()
    libreoffice_look()
    skel_faces()
    faces()
    if shutil.which("plymouth-set-default-theme"):
        run("plymouth-set-default-theme", "paragon")
    if installed_system():
        run("update-initramfs", "-u")
        run("update-grub")


def remove() -> None:
    subprocess.run([sys.executable, str(SHARE / "lockscreen.py"), "--restore"], check=False)
    unfaces()
    unskel_faces()
    spectacle_keys_on()
    krunner_keys_back()
    libreoffice_back()
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
