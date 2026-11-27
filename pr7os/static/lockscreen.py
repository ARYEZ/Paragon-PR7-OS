#!/usr/bin/env python3
"""Plasma's lock screen in the login screen's look, changing only how it looks (runs in the image's build).

    python3 lockscreen.py [ROOT]          ROOT: the system's root (tests use a copy of Plasma's files)

The lock screen is Plasma's shell package (org.kde.plasma.desktop/contents/lockscreen), not the global theme, and
its QML also unlocks the session; so its logic stays Plasma's. Exact edits, each anchored to text that must appear
once: LockScreenUi.qml shows ParagonClock (put beside it) instead of Breeze's Clock; MainBlock.qml gives the password
field and the unlock button the family's backgrounds; UserDelegate.qml draws the gradient ring behind the picture.
All edits are checked first. The edited files are diverted (dpkg-divert): Plasma's own versions are kept beside them as
<file>.paragon-orig, and every run (an update, or a Plasma update through the package's dpkg triggers) starts again
from those, so it can run any number of times. When Plasma's files no longer have the anchors (a newer Plasma), the
lock screen goes back to Plasma's own design (diversions removed) instead of half-changed; with --strict (the ISO's
build) it stops instead. --restore puts Plasma's design back (the package's removal).
"""
import shutil
import subprocess
import sys
from pathlib import Path

GRADIENT = ('gradient: Gradient { orientation: Gradient.Horizontal; '
            'GradientStop { position: 0.0; color: "#FF0743" } GradientStop { position: 0.5; color: "#FA3632" } '
            'GradientStop { position: 1.0; color: "#F2781E" } }')

SHELL = "usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen"
EDITS = [
    (f"{SHELL}/LockScreenUi.qml", [
        ("        Clock {\n            id: clock\n", "        ParagonClock {\n            id: clock\n"),
    ]),
    (f"{SHELL}/MainBlock.qml", [
        ("            id: passwordBox\n",
         "            id: passwordBox\n"
         "            // Paragon: the login screen's field (dark, rounded, the family gradient under it)\n"
         "            color: \"#E8E8EA\"\n"
         "            leftPadding: 18\n"
         "            background: Rectangle {\n"
         "                implicitHeight: 48\n"
         "                radius: 12\n"
         "                color: \"#E60C0A0D\"\n"
         "                border.color: passwordBox.activeFocus ? \"#5A4048\" : \"#3A3238\"\n"
         "                border.width: 1\n"
         "                Rectangle {\n"
         "                    anchors.bottom: parent.bottom\n"
         "                    anchors.horizontalCenter: parent.horizontalCenter\n"
         "                    width: parent.width - 24\n"
         "                    height: 2\n"
         f"                    {GRADIENT}\n"
         "                }\n"
         "            }\n"),
        ("            id: loginButton\n",
         "            id: loginButton\n"
         "            // Paragon: the family gradient key\n"
         "            icon.color: \"#FFFFFF\"\n"
         "            background: Rectangle {\n"
         "                radius: 9\n"
         "                opacity: loginButton.down ? 0.8 : 1\n"
         f"                {GRADIENT}\n"
         "            }\n"),
    ]),
    ("*/org/kde/breeze/components/UserDelegate.qml", [
        ("    // Draw a translucent background circle under the user picture\n",
         "    // Paragon: the family gradient ring around the picture, over a dark disk (as on the login screen)\n"
         "    Rectangle {\n"
         "        anchors.centerIn: imageSource\n"
         "        width: imageSource.width + 8\n"
         "        height: width\n"
         "        radius: width / 2\n"
         f"        {GRADIENT}\n"
         "        Rectangle {\n"
         "            anchors.centerIn: parent\n"
         "            width: parent.width - 8\n"
         "            height: width\n"
         "            radius: width / 2\n"
         "            color: \"#1C1C20\"\n"
         "        }\n"
         "    }\n\n"
         "    // Draw a translucent background circle under the user picture\n"),
    ]),
]


def locate(root: Path, rel: str) -> Path:
    if not rel.startswith("*/"):
        return root / rel
    found = sorted(p for p in (root / "usr").glob("**/" + rel[2:]) if p.is_file())
    if not found:
        raise SystemExit(f"lockscreen: {rel} not found")
    return found[0]


def original(path: Path) -> Path:
    """Plasma's own version of a file: beside it once diverted, the file itself before."""
    kept = path.with_name(path.name + ".paragon-orig")
    return kept if kept.exists() else path


def plan(root: Path) -> list[tuple[Path, str]]:
    out = []
    for rel, edits in EDITS:
        path = locate(root, rel)
        text = original(path).read_text(encoding="utf-8")
        for old, new in edits:
            n = text.count(old)
            if n != 1:
                raise ValueError(f"{path}: {n} of the text an edit expects")
            text = text.replace(old, new)
        out.append((path, text))
    return out


def divert(root: Path, path: Path, add: bool) -> None:
    """Keep Plasma's file beside ours (add) or put it back (remove); a test root has no dpkg: plain renames."""
    kept = path.with_name(path.name + ".paragon-orig")
    if root == Path("/"):
        listed = subprocess.run(["dpkg-divert", "--list", str(path)], capture_output=True, text=True).stdout
        if add and "paragon" not in listed:
            subprocess.run(["dpkg-divert", "--package", "paragon", "--divert", str(kept), "--rename", "--add",
                            str(path)], check=True)
        elif not add and "paragon" in listed:
            path.unlink(missing_ok=True)
            subprocess.run(["dpkg-divert", "--package", "paragon", "--rename", "--remove", str(path)], check=True)
    elif add and not kept.exists():
        path.rename(kept)
    elif not add and kept.exists():
        kept.replace(path)


def restore(root: Path) -> None:
    for rel, _edits in EDITS:
        try:
            divert(root, locate(root, rel), add=False)
        except SystemExit:
            continue
    (root / SHELL / "ParagonClock.qml").unlink(missing_ok=True)


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    args = [a for a in argv if not a.startswith("--")]
    root = Path(args[0]) if args else Path("/")
    if "--restore" in argv:
        restore(root)
        print("lockscreen: Plasma's own design")
        return 0
    try:
        edits = plan(root)                       # every edit checked before anything is written
    except ValueError as e:
        if strict:
            raise SystemExit(f"lockscreen: {e}; nothing changed")
        restore(root)
        print(f"lockscreen: {e}: this Plasma's lock screen is newer than these edits; Plasma's own design is kept")
        return 0
    here = Path(__file__).resolve().parent
    for path, text in edits:
        divert(root, path, add=True)
        path.write_text(text, encoding="utf-8")
        print(f"lockscreen: {path}")
    shutil.copy2(here / "lockscreen" / "ParagonClock.qml", root / SHELL / "ParagonClock.qml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
