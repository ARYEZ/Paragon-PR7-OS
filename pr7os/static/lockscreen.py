#!/usr/bin/env python3
"""Plasma's lock screen in the login screen's look, changing only how it looks (runs in the image's build).

    python3 lockscreen.py [ROOT]          ROOT: the system's root (tests use a copy of Plasma's files)

The lock screen is Plasma's shell package (org.kde.plasma.desktop/contents/lockscreen), not the global theme, and
its QML also unlocks the session; so its logic stays Plasma's. Exact edits, each anchored to text that must appear
once: LockScreenUi.qml shows ParagonClock (put beside it) instead of Breeze's Clock; MainBlock.qml gives the password
field and the unlock button the family's backgrounds; UserDelegate.qml draws the gradient ring behind the picture.
All edits are checked first: if any anchor is missing (Plasma changed), nothing is written and the build stops. The
edited files are diverted (dpkg-divert), so a Plasma update can't put back a version these edits don't match.
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


def plan(root: Path) -> list[tuple[Path, str]]:
    out = []
    for rel, edits in EDITS:
        path = locate(root, rel)
        text = path.read_text(encoding="utf-8")
        for old, new in edits:
            n = text.count(old)
            if n != 1:
                raise SystemExit(f"lockscreen: {path} has {n} of the text this edit expects; nothing changed")
            text = text.replace(old, new)
        out.append((path, text))
    return out


def main(argv: list[str]) -> int:
    root = Path(argv[0]) if argv else Path("/")
    edits = plan(root)                       # every edit checked before anything is written
    here = Path(__file__).resolve().parent
    for path, text in edits:
        if root == Path("/"):
            subprocess.run(["dpkg-divert", "--package", "paragon", "--divert", f"{path}.paragon-orig", "--rename",
                            "--add", str(path)], check=True)
        path.write_text(text, encoding="utf-8")
        print(f"lockscreen: {path}")
    shutil.copy2(here / "lockscreen" / "ParagonClock.qml", root / SHELL / "ParagonClock.qml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
