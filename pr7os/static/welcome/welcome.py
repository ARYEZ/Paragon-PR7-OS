"""Paragon Welcome: what a new PR7-OS desktop needs, in one window (PySide6 from the apps' environment).

    FONT        Bebas Neue (PR7-OS's) or Inter, for your account: Plasma's fonts (kwriteconfig6) and the Paragon apps
                (their launcher reads ~/.config/paragon/font); the login screen and boot stay Bebas Neue (everyone's)
    FINISH      OBSIDIAN or AURORA: the family's choice (~/.config/paragon/family-finish); every Paragon app follows,
                and finish_sync.py takes Plasma's global theme along
    KEYS        Print (PR7-Q), Alt+Space (PR7-LN), Ctrl+Alt+Space (PR7-IS)
    SSH         on / off through pr7os-ssh-helper (pkexec: your password once); shows how to reach this PC
    DRIVERS     pr7os-drivers-helper: firmware for any PC, the NVIDIA driver for an NVIDIA card (and Secure Boot's key)
    PRINTERS    Plasma's printer settings
    STEAM       pr7os-steam (Discover on Steam's Flathub page, or Steam itself)
    BACKUPS     PR7-BK's ready-made home backup (`pr7-bk --new-home-backup`: home, daily 03:00, caches out)
    UPDATES     PR7-OS Update

`pr7os-welcome --first-run` (the autostart entry) opens it only while "Show at sign-in" is on
(~/.config/paragon/welcome.json). Tests replace `Window.start` (what would be started) and set PR7OS_SSH_HELPER /
PR7OS_DRIVERS_HELPER.
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
QWidget {{ background: #0C0A0D; color: #E8E8EA; font-family: "@FONT@"; font-size: @SIZE@px; letter-spacing: 0.5px; }}
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


FONTS = {   # Plasma's font settings for each choice (Bebas Neue a size up: a tall, condensed face)
    "bebas": {"font": "Bebas Neue,12,-1,5,400,0,0,0,0,0,0,0,0,0,0,1",
              "small": "Bebas Neue,10,-1,5,400,0,0,0,0,0,0,0,0,0,0,1",
              "title": "Bebas Neue,12,-1,5,400,0,0,0,0,0,0,0,0,0,0,1"},
    "inter": {"font": "Inter,10,-1,5,400,0,0,0,0,0,0,0,0,0,0,1",
              "small": "Inter,8,-1,5,400,0,0,0,0,0,0,0,0,0,0,1",
              "title": "Inter,10,-1,5,600,0,0,0,0,0,0,0,0,0,0,1"},
}


def font_file() -> str:
    return os.path.join(config_home(), "paragon", "font")


def font() -> str:
    try:
        with open(font_file(), encoding="utf-8") as fh:
            v = fh.read().strip().lower()
    except OSError:
        v = ""
    return v if v in FONTS else "bebas"


def font_commands(name: str) -> list[list[str]]:
    """Plasma's own way to change your fonts (System Settings > Fonts writes the same keys)."""
    f = FONTS[name]
    out = []
    for key, value in (("font", f["font"]), ("menuFont", f["font"]), ("toolBarFont", f["font"]),
                       ("smallestReadableFont", f["small"])):
        out.append(["kwriteconfig6", "--file", "kdeglobals", "--group", "General", "--key", key, value])
    out.append(["kwriteconfig6", "--file", "kdeglobals", "--group", "WM", "--key", "activeFont", f["title"]])
    return out


def style() -> str:
    return STYLE.replace("@FONT@", "Bebas Neue" if font() == "bebas" else "Inter").replace(
        "@SIZE@", "16" if font() == "bebas" else "13")


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


def drivers_helper() -> list[str]:
    if os.environ.get("PR7OS_DRIVERS_HELPER"):
        return shlex.split(os.environ["PR7OS_DRIVERS_HELPER"])
    return ["/usr/libexec/paragon/pr7os-drivers-helper"]


def drivers_state() -> dict:
    try:
        text = subprocess.run(drivers_helper() + ["state"], capture_output=True, text=True, timeout=20).stdout
        return json.loads(text)
    except (OSError, subprocess.SubprocessError, ValueError):
        return {}


def drivers_view(s: dict) -> tuple[str, str]:
    """The DRIVERS card's words and key for what the helper found."""
    nvidia = next((g for g in s.get("gpus", []) if g.get("vendor") == "10de"), None)
    if not nvidia:
        return "Firmware for Wi-Fi, Bluetooth, sound and graphics, and your processor's security fixes.", \
            "INSTALL FIRMWARE"
    name = nvidia.get("name", "NVIDIA")
    if s.get("in_use"):
        return f"{name}: the NVIDIA driver is in use.", "INSTALL AGAIN"
    if s.get("installed"):
        if s.get("key_waiting"):
            return (f"{name}: installed. Restart; on the blue screen choose Enroll MOK, Continue, Yes, type the "
                    "password Welcome showed, then Reboot."), "INSTALL AGAIN"
        return f"{name}: the NVIDIA driver is installed: restart the PC to use it.", "INSTALL AGAIN"
    return (f"{name}: the open-source driver is in use (games run slowly). Debian's NVIDIA driver, with firmware "
            "for the rest of the PC."), "INSTALL NVIDIA DRIVER"


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
        self.setStyleSheet(style())
        self.configure = lambda args: subprocess.run(args, capture_output=True)   # tests record instead
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

        box, row, self.font_text = card("FONT", "Bebas Neue (capitals only) or Inter, for your account and the Paragon "
                                                "apps. Sign out and back in to see it everywhere.")
        self.font_keys = {}
        for name, label in (("bebas", "BEBAS NEUE"), ("inter", "INTER")):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(font() == name)
            b.clicked.connect(lambda _=False, n=name: self.choose_font(n))
            row.addWidget(b)
            self.font_keys[name] = b
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

        box, row, self.drivers_text = card("DRIVERS", "")
        self.drivers_key = QPushButton("")
        self.drivers_key.clicked.connect(self.install_drivers)
        row.addWidget(self.drivers_key)
        lay.addWidget(box)
        self.mok = ""
        self.show_drivers()

        for label, text, key, command in (
                ("PRINTERS", "Network printers are found by themselves; add one here.", "ADD A PRINTER",
                 ["systemsettings", "kcm_printer_manager"]),
                ("STEAM", "Steam from Flathub, with its own libraries.", "GET STEAM", ["pr7os-steam"]),
                ("BACKUPS", "Your home folder every night at 03:00, to a drive you choose (PR7-BK).",
                 "BACK UP TO A DRIVE", ["pr7-bk", "--new-home-backup"]),
                ("UPDATES", "PR7-OS checks once a day; look now, or go back to the release before.", "CHECK FOR UPDATES",
                 ["pr7os-update"])):
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

    def choose_font(self, name: str) -> None:
        path = font_file()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(name)
        for args in font_commands(name):
            self.configure(args)
        for n, b in self.font_keys.items():
            b.setChecked(n == name)
        self.font_text.setText("Saved: sign out and back in to see it everywhere.")
        self.setStyleSheet(style())

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
        self._run(helper(), "PR7OS_SSH_HELPER", word, self.ssh_text, self._ssh_done)

    def _run(self, cmd: list[str], test_var: str, word: str, text: QLabel, done) -> None:
        """A root helper through pkexec (straight in tests); its STEP / ERROR lines go to the card's text."""
        cmd = cmd if os.environ.get(test_var) else ["pkexec"] + cmd
        self.proc_text = text
        self.last_line = ""
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(lambda code, _s=None: done(code))
        self.proc.start(cmd[0], cmd[1:] + [word])
        if self.sync:
            self.proc.waitForFinished(1800000)

    def _read(self) -> None:
        if self.proc is None:
            return
        for line in bytes(self.proc.readAllStandardOutput()).decode(errors="replace").splitlines():
            word, _, rest = line.partition(" ")
            if word in ("STEP", "ERROR"):
                self.proc_text.setText(rest)
            if word == "MOK":
                self.mok = rest.strip()
            if word != "MOK":                        # the password is shown once, on the card; never kept elsewhere
                self.last_line = line

    def show_drivers(self, note: str = "") -> None:
        text, key = drivers_view(drivers_state())
        self.drivers_text.setText(note or text)
        self.drivers_key.setText(key)
        self.drivers_key.setEnabled(True)

    def install_drivers(self) -> None:
        self.drivers_key.setEnabled(False)
        self.mok = ""
        self.drivers_text.setText("Your password lets PR7-OS install them.")
        self._run(drivers_helper(), "PR7OS_DRIVERS_HELPER", "install", self.drivers_text, self._drivers_done)

    def _drivers_done(self, code: int) -> None:
        self._read()
        if code in (126, 127):
            self.show_drivers("Nothing was installed (no password given).")
            return
        if code:
            self.show_drivers(self.last_line.partition(" ")[2] or "The install stopped.")
            return
        note = "Installed: restart the PC to use them."
        if self.mok:
            spaced = f"{self.mok[:4]} {self.mok[4:]}"
            note = (f"Installed. Secure Boot must trust the driver once: restart, and on the blue screen choose "
                    f"Enroll MOK, Continue, Yes, type {spaced}, then Reboot.")
        self.show_drivers(note)

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
