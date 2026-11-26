"""Render the real login screen (pr7os/static/sddm/Main.qml) with stand-ins for SDDM's objects.

    python tools/login_preview.py ROOT OUT.png      ROOT: the generated files (python -m pr7os.assets ROOT)

Tests use `render` to check the screen and that logging in calls SDDM with the account, password and session.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import (QAbstractListModel, QByteArray, QModelIndex, QObject, QUrl, Property, Qt,  # noqa: E402
                            Signal, Slot)


class Model(QAbstractListModel):
    """SDDM's userModel / sessionModel: rows of roles, and lastIndex."""

    def __init__(self, rows: list[dict], last: int = 0):
        super().__init__()
        self.rows, self._last = rows, last
        self.keys = list(rows[0]) if rows else []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def roleNames(self):
        return {Qt.ItemDataRole.UserRole + 1 + i: QByteArray(k.encode()) for i, k in enumerate(self.keys)}

    def data(self, index, role):
        k = role - Qt.ItemDataRole.UserRole - 1
        if 0 <= k < len(self.keys):
            return self.rows[index.row()][self.keys[k]]
        return None

    def _get_last(self):
        return self._last

    lastIndex = Property(int, _get_last, constant=True)


class Sddm(QObject):
    """SDDM's `sddm` object: what the theme may do, and what it did (`calls`)."""
    loginFailed = Signal()
    loginSucceeded = Signal()

    def __init__(self):
        super().__init__()
        self.calls: list[tuple] = []

    def _yes(self):
        return True

    canSuspend = Property(bool, _yes, constant=True)
    canReboot = Property(bool, _yes, constant=True)
    canPowerOff = Property(bool, _yes, constant=True)

    @Slot(str, str, int)
    def login(self, user, password, session):
        self.calls.append(("login", user, password, session))

    @Slot()
    def suspend(self):
        self.calls.append(("suspend",))

    @Slot()
    def reboot(self):
        self.calls.append(("reboot",))

    @Slot()
    def powerOff(self):
        self.calls.append(("powerOff",))


def view(root: Path):
    """(QQuickView showing the theme, Sddm stand-in). The caller keeps both alive."""
    from PySide6.QtQuick import QQuickView, QQuickWindow, QSGRendererInterface
    from PySide6.QtGui import QFontDatabase
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)
    for ttf in (root / "usr/share/fonts/truetype/paragon-inter").glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(ttf))
    theme_dir = root / "usr/share/sddm/themes/paragon"
    sddm = Sddm()
    users = Model([{"name": "ari", "realName": "", "icon": "", "homeDir": "/home/ari", "needsPassword": True}])
    sessions = Model([{"name": "Plasma (Wayland)", "file": "plasma.desktop"},
                      {"name": "Plasma (X11)", "file": "plasmax11.desktop"}])
    v = QQuickView()
    ctx = v.rootContext()
    v._keep = (sddm, users, sessions)
    ctx.setContextProperty("sddm", sddm)
    ctx.setContextProperty("userModel", users)
    ctx.setContextProperty("sessionModel", sessions)
    ctx.setContextProperty("config", {"background": "background.png"})
    ctx.setContextProperty("keyboard", None)
    v.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    v.resize(1920, 1080)
    v.setSource(QUrl.fromLocalFile(str(theme_dir / "Main.qml")))
    errors = [e.toString() for e in v.errors()]
    if errors:
        raise RuntimeError("\n".join(errors))
    v.show()
    return v, sddm


def render(root: Path, out: Path | None = None):
    from PySide6.QtWidgets import QApplication
    v, sddm = view(root)
    for _ in range(20):
        QApplication.processEvents()
    img = v.grabWindow()
    if out is not None:
        img.save(str(out))
    return v, sddm, img


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    render(Path(sys.argv[1]), Path(sys.argv[2]))
    print(sys.argv[2])
