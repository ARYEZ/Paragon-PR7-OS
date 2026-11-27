"""PR7-OS Update: the window (PySide6, from the apps' environment). What's newer, its notes, UPDATE.

UPDATE runs the root helper through pkexec (your password, once per session) and follows its lines: STEP (what it's
doing), PROGRESS i n file, LOG (apt's output, under DETAILS), DONE logout|installed|up-to-date, ERROR text.
Tests replace `Window.provider` (what GitHub and dpkg say) and `Window.helper` (the command it starts).
"""
from __future__ import annotations

import os
import shlex
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pr7os_update as u  # noqa: E402

from PySide6.QtCore import QObject, QProcess, Qt, Signal  # noqa: E402
from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPlainTextEdit, QProgressBar,  # noqa: E402
                               QPushButton, QTextBrowser, QVBoxLayout, QWidget)

GRADIENT = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF0743, stop:0.5 #FA3632, stop:1 #F2781E)"
STYLE = f"""
QWidget {{ background: #0C0A0D; color: #E8E8EA; font-family: "Bebas Neue"; font-size: 16px; letter-spacing: 0.5px; }}
QLabel#title {{ font-size: 15px; font-weight: 600; letter-spacing: 2px; color: #8A8A92; }}
QLabel#heading {{ font-size: 23px; font-weight: 600; }}
QLabel#status {{ color: #B9B5B8; }}
QTextBrowser, QPlainTextEdit {{ background: #060407; border: 1px solid #27222A; border-radius: 8px; padding: 8px; }}
QPushButton {{ background: #1C1C20; border: 1px solid #3A3238; border-radius: 8px; padding: 9px 18px;
              font-weight: 600; letter-spacing: 1px; }}
QPushButton:hover {{ background: #303034; }}
QPushButton#primary {{ background: {GRADIENT}; border: none; color: #FFFFFF; }}
QPushButton#primary:disabled {{ background: #303034; color: #8A8A92; }}
QProgressBar {{ background: #1C1C20; border: none; border-radius: 3px; height: 6px; }}
QProgressBar::chunk {{ background: {GRADIENT}; border-radius: 3px; }}
"""
HELPER = ["pkexec", "/usr/libexec/paragon/pr7os-update-helper"]


def default_provider():
    info = u.latest()
    return info, u.installed()


class Bridge(QObject):
    found = Signal(object, object)       # info, installed
    failed = Signal(str)


class Window(QWidget):
    provider = staticmethod(default_provider)
    helper = HELPER

    def __init__(self, sync: bool = False):
        super().__init__()
        self.setWindowTitle("PR7-OS Update")
        # Qt deletes the window when it closes, at a safe point in its event loop. Left to Python's garbage collector
        # (the window is in reference cycles with its slots), it was deleted at a random moment: a crash at exit.
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(640, 520)
        self.setStyleSheet(STYLE)
        self.sync = sync
        self.info = None
        self.pkgs: list[dict] = []
        self.state = "looking"
        self.result = ""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(12)
        title = QLabel("PARAGON PR7-OS  ·  UPDATE")
        title.setObjectName("title")
        self.heading = QLabel("Looking for updates…")
        self.heading.setObjectName("heading")
        self.heading.setWordWrap(True)
        self.status = QLabel("")
        self.status.setObjectName("status")
        self.status.setWordWrap(True)
        self.notes = QTextBrowser()
        self.notes.setOpenExternalLinks(True)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.hide()
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setFont(QFont("DejaVu Sans Mono", 9))
        self.details.hide()
        keys = QHBoxLayout()
        self.more = QPushButton("DETAILS")
        self.more.clicked.connect(self.toggle_details)
        self.later = QPushButton("LATER")
        self.later.clicked.connect(self.close)
        self.update_key = QPushButton("UPDATE")
        self.update_key.setObjectName("primary")
        self.update_key.setEnabled(False)
        self.update_key.clicked.connect(self.start)
        keys.addWidget(self.more)
        keys.addStretch(1)
        keys.addWidget(self.later)
        keys.addWidget(self.update_key)
        for w in (title, self.heading, self.status, self.notes, self.progress, self.details):
            lay.addWidget(w)
        lay.addLayout(keys)
        self.bridge = Bridge()
        self.bridge.found.connect(self.show_found, Qt.ConnectionType.QueuedConnection)
        self.bridge.failed.connect(self.show_failed, Qt.ConnectionType.QueuedConnection)
        self.proc: QProcess | None = None
        self._buffer = ""
        self.look()

    def toggle_details(self):
        self.details.setVisible(not self.details.isVisible())

    # ---------------------------------------------------------------- what's there
    def look(self):
        def work():
            try:
                info, have = type(self).provider()
                self.bridge.found.emit(info, have)
            except u.UpdateError as e:
                self.bridge.failed.emit(str(e))
        if self.sync:
            try:
                info, have = type(self).provider()
                self.show_found(info, have)
            except u.UpdateError as e:
                self.show_failed(str(e))
        else:
            threading.Thread(target=work, daemon=True).start()

    def show_found(self, info, have):
        self.info = info
        self.pkgs = u.pending(info["manifest"], have)
        self.notes.setMarkdown(info.get("notes") or "")
        if not self.pkgs:
            self.state = "current"
            self.heading.setText(f"Paragon PR7-OS {info['version']} is the newest")
            self.status.setText("Nothing to install.")
            self.later.setText("CLOSE")
            return
        self.state = "available"
        size = sum(int(p["size"]) for p in self.pkgs) / 1e6
        current = have.get("paragon-pr7os-look")
        self.heading.setText(f"Paragon PR7-OS {info['version']} is ready")
        self.status.setText((f"You have {current}. " if current else "")
                            + f"{len(self.pkgs)} package{'s' if len(self.pkgs) != 1 else ''} to download "
                            f"({size:.0f} MB).")
        self.update_key.setEnabled(True)

    def show_failed(self, text):
        self.state = "error"
        self.heading.setText("Updates can't be checked right now")
        self.status.setText(text)
        self.later.setText("CLOSE")

    # ---------------------------------------------------------------- installing
    def start(self):
        self.state = "installing"
        self.update_key.setEnabled(False)
        self.later.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.show()
        self.status.setText("Your password lets PR7-OS install the update.")
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(self._finished)
        cmd = type(self).helper
        if os.environ.get("PR7OS_UPDATE_HELPER"):
            cmd = shlex.split(os.environ["PR7OS_UPDATE_HELPER"])
        self.proc.start(cmd[0], cmd[1:])
        if self.sync:
            self.proc.waitForFinished(120000)
            self._read()

    def _read(self):
        if self.proc is None:
            return
        self._buffer += bytes(self.proc.readAllStandardOutput()).decode(errors="replace")
        *lines, self._buffer = self._buffer.split("\n")
        for line in lines:
            self.handle(line)

    def handle(self, line: str):
        word, _, rest = line.partition(" ")
        if word == "STEP":
            self.status.setText(rest)
        elif word == "PROGRESS":
            i, n, name = (rest.split(" ", 2) + ["", ""])[:3]
            self.progress.setRange(0, int(n))
            self.progress.setValue(int(i))
            self.status.setText(f"Downloading {name}")
        elif word == "LOG":
            self.details.appendPlainText(rest)
        elif word == "DONE":
            self.result = rest.split(" ")[0]
        elif word == "ERROR":
            self.result = "error"
            self.status.setText(rest)
            self.details.appendPlainText(line)
        elif line:
            self.details.appendPlainText(line)

    def _finished(self, code, _status=None):
        self._read()
        self.progress.hide()
        self.later.setEnabled(True)
        self.later.setText("CLOSE")
        if code in (126, 127) and not self.result:      # pkexec: the password dialog was cancelled
            self.state = "available"
            self.status.setText("Nothing was changed (no password given).")
            self.update_key.setEnabled(True)
            return
        if self.result == "error" or code:
            self.state = "error"
            self.heading.setText("The update didn't finish")
            if not self.status.text():
                self.status.setText(f"The helper stopped with code {code}.")
            self.details.show()
            return
        self.state = "done"
        version = self.info["version"] if self.info else ""
        self.heading.setText(f"Paragon PR7-OS {version} is installed")
        if self.result == "logout":
            self.status.setText("Log out and back in to see the new look everywhere.")
            self.update_key.setText("LOG OUT NOW")
            self.update_key.setEnabled(True)
            self.update_key.clicked.disconnect()
            self.update_key.clicked.connect(self.logout)
        else:
            self.status.setText("Open apps get the update when they're started again.")

    def logout(self):
        QProcess.startDetached("qdbus6", ["org.kde.Shutdown", "/Shutdown", "logout"])
        self.close()


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    w = Window()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
