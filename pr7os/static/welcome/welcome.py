"""Paragon Welcome: what a new PR7-OS desktop needs, in one window (PySide6 from the apps' environment).

    FINISH      OBSIDIAN or AURORA: the family's choice (~/.config/paragon/family-finish); every Paragon app follows,
                and finish_sync.py takes Plasma's global theme along
    KEYS        Print (PR7-Q), Alt+Space (PR7-LN), Ctrl+Alt+Space (PR7-IS)
    SSH         on / off through pr7os-ssh-helper (pkexec: your password once); shows how to reach this PC
    PRINTERS    Plasma's printer settings
    STEAM       pr7os-steam (Discover on Steam's Flathub page, or Steam itself)
    UPDATES     PR7-OS Update

`pr7os-welcome --first-run` (the autostart entry) opens it only while "Show at sign-in" is on
(~/.config/paragon/welcome.json). Tests replace `Window.start` (what would be started) and set PR7OS_SSH_HELPER.
"""
from __future__ import annotations

import json
import os
import shlex
import socket
import subprocess
import sys

from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

GRADIENT = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF0743, stop:0.5 #FA3632, stop:1 #F2781E)"
STYLE = f"""
QWidget {{ background: #0C0A0D; color: #E8E8EA; font-family: "Bebas Neue"; font-size: 16px; letter-spacing: 0.5px; }}
QLabel#title {{ font-size: 15px; font-weight: 600; letter-spacing: 2px; color: #8A8A92; }}
QLabel#heading {{ font-size: 25px; font-weight: 600; }}
QLabel#label {{ font-size: 15px; font-weight: 600; letter-spacing: 2px; color: #B9B5B8; }}
QLabel#dim {{ color: #8A8A92; }}
QFrame#card {{ background: #141116; border: 1px solid #27222A; border-radius: 10px; }}
QFrame#card QLabel, QFrame#card QCheckBox {{ background: transparent; }}
QPushButton {{ background: #1C1C20; border: 1px solid #3A3238; border-radius: 8px; padding: 8px 16px;
              font-weight: 600; letter-spacing: 1px; }}
QPushButton:hover {{ background: #303034; }}
QPushButton:checked, QPushButton#primary {{ background: {GRADIENT}; border: none; color: #FFFFFF; }}
QPushButton:disabled {{ color: #5E5A60; }}
"""
KEYS = [("PRINT", "Screenshot of a region (PR7-Q); Shift / Alt / Ctrl+Print: last region, window, full screen"),
        ("ALT+SPACE", "The launcher (PR7-LN): programs, files, sums, web searches"),
        ("CTRL+ALT+SPACE", "Search every file (PR7-IS)"),
        ("META+L", "Lock the screen")]


def config_home() -> str:
    return os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")


def family_file() -> str:
    return os.environ.get("PARAGON_FAMILY_FILE") or os.path.join(config_home(), "paragon", "family-finish")


def settings_file() -> str:
    return os.path.join(config_home(), "paragon", "welcome.json")


def show_at_sign_in() -> bool:
    try:
        with open(settings_file(), encoding="utf-8") as fh:
            return bool(json.load(fh).get("show_at_sign_in", True))
    except (OSError, ValueError):
        return True


def set_show_at_sign_in(on: bool) -> None:
    os.makedirs(os.path.dirname(settings_file()), exist_ok=True)
    with open(settings_file(), "w", encoding="utf-8") as fh:
        json.dump({"show_at_sign_in": on}, fh)


def finish() -> str:
    try:
        with open(family_file(), encoding="utf-8") as fh:
            v = fh.read().strip().lower()
    except OSError:
        v = ""
    return v if v in ("obsidian", "aurora") else "obsidian"


def set_finish(name: str) -> None:
    path = family_file()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(name)


def helper() -> list[str]:
    if os.environ.get("PR7OS_SSH_HELPER"):
        return shlex.split(os.environ["PR7OS_SSH_HELPER"])
    return ["/usr/libexec/paragon/pr7os-ssh-helper"]


def ssh_state() -> str:
    try:
        return subprocess.run(helper() + ["state"], capture_output=True, text=True, timeout=10).stdout.strip() or "off"
    except (OSError, subprocess.SubprocessError):
        return "off"


def card(label: str, text: str) -> tuple[QFrame, QHBoxLayout, QLabel]:
    box = QFrame()
    box.setObjectName("card")
    row = QHBoxLayout(box)
    row.setContentsMargins(16, 12, 16, 12)
    words = QVBoxLayout()
    title = QLabel(label)
    title.setObjectName("label")
    body = QLabel(text)
    body.setObjectName("dim")
    body.setWordWrap(True)
    words.addWidget(title)
    words.addWidget(body)
    row.addLayout(words, 1)
    return box, row, body


class Window(QWidget):
    def __init__(self, sync: bool = False):
        super().__init__()
        self.sync = sync
        self.started: list[list[str]] = []
        self.proc: QProcess | None = None
        self.setWindowTitle("Welcome to PR7-OS")
        self.setStyleSheet(STYLE)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)        # PR7-OS's updater window's lesson
        self.resize(720, 640)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(12)
        title = QLabel("PARAGON PR7-OS  ·  WELCOME")
        title.setObjectName("title")
        heading = QLabel("Welcome to Paragon PR7-OS")
        heading.setObjectName("heading")
        lay.addWidget(title)
        lay.addWidget(heading)

        box, row, _ = card("FINISH", "Every Paragon app and the desktop itself, dark or light.")
        self.finish_keys = {}
        for name in ("obsidian", "aurora"):
            b = QPushButton(name.upper())
            b.setCheckable(True)
            b.setChecked(finish() == name)
            b.clicked.connect(lambda _=False, n=name: self.choose_finish(n))
            row.addWidget(b)
            self.finish_keys[name] = b
        lay.addWidget(box)

        keys = QFrame()
        keys.setObjectName("card")
        grid = QGridLayout(keys)
        grid.setContentsMargins(16, 12, 16, 12)
        head = QLabel("KEYS")
        head.setObjectName("label")
        grid.addWidget(head, 0, 0, 1, 2)
        for r, (key, what) in enumerate(KEYS, 1):
            k, w = QLabel(key), QLabel(what)
            k.setObjectName("label")
            w.setObjectName("dim")
            grid.addWidget(k, r, 0)
            grid.addWidget(w, r, 1)
        lay.addWidget(keys)

        box, row, self.ssh_text = card("SSH", "")
        self.ssh_key = QPushButton("")
        self.ssh_key.clicked.connect(self.toggle_ssh)
        row.addWidget(self.ssh_key)
        lay.addWidget(box)
        self.ssh = ssh_state()
        self.show_ssh()

        for label, text, key, command in (
                ("PRINTERS", "Network printers are found by themselves; add one here.", "ADD A PRINTER",
                 ["systemsettings", "kcm_printer_manager"]),
                ("STEAM", "Steam from Flathub, with its own libraries.", "GET STEAM", ["pr7os-steam"]),
                ("UPDATES", "PR7-OS checks once a day; look now.", "CHECK FOR UPDATES", ["pr7os-update"])):
            box, row, _ = card(label, text)
            b = QPushButton(key)
            b.clicked.connect(lambda _=False, c=command: self.start(c))
            row.addWidget(b)
            lay.addWidget(box)

        lay.addStretch(1)
        bottom = QHBoxLayout()
        self.at_sign_in = QCheckBox("Show at sign-in")
        self.at_sign_in.setChecked(show_at_sign_in())
        self.at_sign_in.toggled.connect(set_show_at_sign_in)
        close = QPushButton("CLOSE")
        close.setObjectName("primary")
        close.clicked.connect(self.close)
        bottom.addWidget(self.at_sign_in)
        bottom.addStretch(1)
        bottom.addWidget(close)
        lay.addLayout(bottom)

    # ---------------------------------------------------------------- what the keys do
    def start(self, command: list[str]) -> None:
        self.started.append(command)
        QProcess.startDetached(command[0], command[1:])

    def choose_finish(self, name: str) -> None:
        set_finish(name)
        for n, b in self.finish_keys.items():
            b.setChecked(n == name)

    def show_ssh(self, note: str = "") -> None:
        host = socket.gethostname()
        user = os.environ.get("USER") or "you"
        if self.ssh == "on":
            self.ssh_text.setText(note or f"On: from another computer, ssh {user}@{host}.local")
            self.ssh_key.setText("TURN OFF")
        else:
            self.ssh_text.setText(note or "Off: other computers can't log in to this one.")
            self.ssh_key.setText("TURN ON")
        self.ssh_key.setEnabled(True)

    def toggle_ssh(self) -> None:
        word = "off" if self.ssh == "on" else "on"
        self.ssh_key.setEnabled(False)
        self.ssh_text.setText("Your password lets PR7-OS change this.")
        cmd = helper() if os.environ.get("PR7OS_SSH_HELPER") else ["pkexec"] + helper()
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(lambda code, _s=None: self._ssh_done(code))
        self.proc.start(cmd[0], cmd[1:] + [word])
        if self.sync:
            self.proc.waitForFinished(120000)

    def _read(self) -> None:
        if self.proc is None:
            return
        for line in bytes(self.proc.readAllStandardOutput()).decode(errors="replace").splitlines():
            word, _, rest = line.partition(" ")
            if word in ("STEP", "ERROR"):
                self.ssh_text.setText(rest)
            self.last_line = line

    def _ssh_done(self, code: int) -> None:
        self._read()
        if code in (126, 127):                     # the password dialog was cancelled
            self.show_ssh("Nothing was changed (no password given).")
            return
        self.ssh = ssh_state()
        self.show_ssh("" if code == 0 else getattr(self, "last_line", "").partition(" ")[2])


def main(argv: list[str]) -> int:
    if "--first-run" in argv and not show_at_sign_in():
        return 0
    app = QApplication.instance() or QApplication(sys.argv[:1])
    w = Window()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
