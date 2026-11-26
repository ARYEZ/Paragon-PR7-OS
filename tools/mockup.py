"""Mock-ups of Paragon PR7-OS (Debian 13 + KDE Plasma in the family look), for approval before anything is built.

    python tools/mockup.py OUT_DIR [SHOTS_DIR]

Draws the desktop in both finishes (Plasma's floating panel, the launcher, windows in Paragon title bars), the login
screen (SDDM), the boot menu (GRUB) and the boot splash (Plymouth). SHOTS_DIR holds real app screenshots from each
app's tools/screenshots.py (e/grid.png, e/grid_aurora.png, m/main_window.png, p/main_window_aurora.png); the app icons
come from the family's repositories next to this one. The panel and the launcher stay dark in both finishes, as
menus and keys do in every family app.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen,  # noqa: E402
                           QRadialGradient)
from PySide6.QtWidgets import QApplication  # noqa: E402

from pr7os import theme, widgets  # noqa: E402

W, H = 1920, 1080
FAMILY = ROOT.parent                     # the other family repositories, checked out next to this one
APPS = [  # (letter, name in the launcher, what it is)
    ("E", "Files", "File manager"), ("W", "Text", "Text editor"), ("TM", "Terminal", "Terminal"),
    ("M", "Media", "Media player"), ("P", "Images", "Image viewer"), ("R", "PDF", "PDF reader"),
    ("Z", "Archives", "Archive manager"), ("F", "Transfers", "File transfer"), ("PM", "Passwords", "Passwords"),
    ("HB", "Video", "Video converter"), ("L", "Tags", "Tag editor"), ("Q", "Screenshot", "Screenshots"),
    ("BK", "Backups", "Backups"), ("FS", "Sync", "Folder sync"), ("DU", "Disk usage", "Disk usage"),
    ("HW", "Hardware", "Hardware information"),
]


# ------------------------------------------------------------------ basics
def font(px: float, bold: bool = False, spacing: float = 0.0) -> QFont:
    f = QFont("Inter")
    f.setPixelSize(round(px))
    f.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
    if spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return f


def colour(hex_: str, alpha: float = 1.0) -> QColor:
    c = QColor(hex_)
    c.setAlphaF(alpha)
    return c


def text(p: QPainter, rect: QRectF, s: str, px: float, c, bold=False, align=Qt.AlignmentFlag.AlignLeft
         | Qt.AlignmentFlag.AlignVCenter, spacing=0.0):
    p.setFont(font(px, bold, spacing))
    p.setPen(colour(c) if isinstance(c, str) else c)
    p.drawText(rect, int(align), s)


def rounded(p: QPainter, rect: QRectF, r: float, fill, edge=None, width=1.0):
    p.setPen(QPen(colour(edge) if isinstance(edge, str) else edge, width) if edge else Qt.PenStyle.NoPen)
    p.setBrush(fill)
    p.drawRoundedRect(rect, r, r)


def shadow(p: QPainter, rect: QRectF, r: float, depth: int = 22, strength: float = 0.5):
    p.setPen(Qt.PenStyle.NoPen)
    for i in range(depth, 0, -2):
        p.setBrush(QColor(0, 0, 0, round(255 * strength * (1 - i / depth) ** 2 / 6)))
        p.drawRoundedRect(rect.adjusted(-i, -i + 6, i, i + 6), r + i, r + i)


def icon(letter: str) -> QImage | None:
    for path in sorted(FAMILY.glob(f"paragon-pr7-{letter.lower()}/pr7*/icons/app.png")):
        img = QImage(str(path))
        if not img.isNull():
            return img
    return None


def draw_icon(p: QPainter, letter: str, rect: QRectF):
    img = icon(letter)
    if img is not None:
        p.drawImage(rect, img)
    else:
        rounded(p, rect, rect.width() * 0.22, theme.family_gradient(rect.left(), 0, rect.right(), 0))


def seven(p: QPainter, rect: QRectF, glow: bool = True):
    """The family's 7 on its own (the launcher button, the splash): PR7's geometry, the family gradient."""
    h = rect.height()
    path = QPainterPath()
    pts = [(0, 0), (.8, 0), (.8, .2), (.44, 1), (.18, 1), (.5, .2), (0, .2)]
    slant = widgets.SLANT
    x0 = rect.center().x() - (0.8 + slant) * h / 2
    path.moveTo(x0 + (pts[0][0] + slant * (1 - pts[0][1])) * h, rect.top() + pts[0][1] * h)
    for x, y in pts[1:]:
        path.lineTo(x0 + (x + slant * (1 - y)) * h, rect.top() + y * h)
    path.closeSubpath()
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if glow:
        for ring in (3, 2, 1):
            p.setPen(QPen(colour(theme.GLOW, 0.1 * (4 - ring)), h * 0.07 * ring, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
    p.fillPath(path, theme.family_gradient(x0, 0, x0 + h, 0))
    p.restore()


def line_icon(p: QPainter, name: str, c: QPointF, s: float, col: str, width: float = 1.8):
    """The tray's and the launcher's line glyphs, drawn in the family's pearl."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(colour(col), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    x, y = c.x(), c.y()
    if name == "wifi":
        for r in (s * .2, s * .38, s * .56):
            p.drawArc(QRectF(x - r, y + s * .3 - r, 2 * r, 2 * r), 45 * 16, 90 * 16)
        p.setBrush(colour(col)); p.drawEllipse(QPointF(x, y + s * .28), 1.6, 1.6)
    elif name == "volume":
        path = QPainterPath(QPointF(x - s * .45, y - s * .15))
        for px, py in ((-.25, -.15), (0, -.4), (0, .4), (-.25, .15), (-.45, .15)):
            path.lineTo(x + px * s, y + py * s)
        path.closeSubpath(); p.drawPath(path)
        p.drawArc(QRectF(x - s * .15, y - s * .25, s * .4, s * .5), -50 * 16, 100 * 16)
        p.drawArc(QRectF(x - s * .3, y - s * .45, s * .75, s * .9), -50 * 16, 100 * 16)
    elif name == "battery":
        p.drawRoundedRect(QRectF(x - s * .45, y - s * .22, s * .8, s * .44), 2, 2)
        p.drawLine(QPointF(x + s * .42, y - s * .08), QPointF(x + s * .42, y + s * .08))
        p.fillRect(QRectF(x - s * .36, y - s * .13, s * .48, s * .26), colour(col))
    elif name == "bell":
        path = QPainterPath(QPointF(x - s * .35, y + s * .22))
        path.cubicTo(x - s * .3, y - s * .1, x - s * .3, y - s * .4, x, y - s * .4)
        path.cubicTo(x + s * .3, y - s * .4, x + s * .3, y - s * .1, x + s * .35, y + s * .22)
        path.closeSubpath(); p.drawPath(path)
        p.drawLine(QPointF(x - s * .08, y + s * .36), QPointF(x + s * .08, y + s * .36))
    elif name == "clipboard":
        p.drawRoundedRect(QRectF(x - s * .3, y - s * .36, s * .6, s * .74), 2, 2)
        p.drawRoundedRect(QRectF(x - s * .14, y - s * .44, s * .28, s * .14), 1.5, 1.5)
        p.drawLine(QPointF(x - s * .16, y), QPointF(x + s * .16, y))
        p.drawLine(QPointF(x - s * .16, y + s * .16), QPointF(x + s * .08, y + s * .16))
    elif name == "search":
        p.drawEllipse(QPointF(x - s * .08, y - s * .08), s * .28, s * .28)
        p.drawLine(QPointF(x + s * .13, y + s * .13), QPointF(x + s * .38, y + s * .38))
    elif name == "power":
        p.drawArc(QRectF(x - s * .36, y - s * .32, s * .72, s * .72), 120 * 16, 300 * 16)
        p.drawLine(QPointF(x, y - s * .44), QPointF(x, y - s * .02))
    elif name == "restart":
        p.drawArc(QRectF(x - s * .36, y - s * .36, s * .72, s * .72), 60 * 16, 290 * 16)
        p.drawLine(QPointF(x + s * .18, y - s * .31), QPointF(x + s * .36, y - s * .38))
        p.drawLine(QPointF(x + s * .18, y - s * .31), QPointF(x + s * .2, y - s * .12))
    elif name == "sleep":
        path = QPainterPath(QPointF(x + s * .05, y - s * .4))
        path.arcTo(QRectF(x - s * .4, y - s * .4, s * .8, s * .8), 100, 250)
        path.cubicTo(x + s * .1, y + s * .3, x - s * .25, y - s * .1, x + s * .05, y - s * .4)
        p.drawPath(path)
    elif name == "leave":
        p.drawLine(QPointF(x - s * .05, y), QPointF(x + s * .4, y))
        p.drawLine(QPointF(x + s * .25, y - s * .15), QPointF(x + s * .4, y))
        p.drawLine(QPointF(x + s * .25, y + s * .15), QPointF(x + s * .4, y))
        p.drawPolyline([QPointF(x + s * .1, y - s * .25), QPointF(x + s * .1, y - s * .4),
                        QPointF(x - s * .4, y - s * .4), QPointF(x - s * .4, y + s * .4),
                        QPointF(x + s * .1, y + s * .4), QPointF(x + s * .1, y + s * .25)])
    elif name == "settings":
        p.drawEllipse(c, s * .16, s * .16)
        for i in range(8):
            a = i * math.pi / 4
            p.drawLine(QPointF(x + math.cos(a) * s * .28, y + math.sin(a) * s * .28),
                       QPointF(x + math.cos(a) * s * .42, y + math.sin(a) * s * .42))
        p.drawEllipse(c, s * .3, s * .3)
    elif name == "grid":
        for i in range(3):
            for j in range(3):
                p.drawRect(QRectF(x - s * .38 + i * s * .28, y - s * .38 + j * s * .28, s * .18, s * .18))
    elif name == "star":
        pts = [QPointF(x + math.cos(math.pi / 2 + i * math.pi / 5) * (s * .42 if i % 2 == 0 else s * .18),
                       y - math.sin(math.pi / 2 + i * math.pi / 5) * (s * .42 if i % 2 == 0 else s * .18))
               for i in range(10)]
        p.drawPolygon(pts)
    elif name == "folder":
        p.drawPolyline([QPointF(x - s * .42, y + s * .3), QPointF(x - s * .42, y - s * .3),
                        QPointF(x - s * .1, y - s * .3), QPointF(x, y - s * .18), QPointF(x + s * .42, y - s * .18),
                        QPointF(x + s * .42, y + s * .3), QPointF(x - s * .42, y + s * .3)])
    elif name in ("minimise", "maximise", "close"):
        if name == "minimise":
            p.drawLine(QPointF(x - s * .3, y + s * .1), QPointF(x + s * .3, y + s * .1))
        elif name == "maximise":
            p.drawRect(QRectF(x - s * .28, y - s * .28, s * .56, s * .56))
        else:
            p.drawLine(QPointF(x - s * .25, y - s * .25), QPointF(x + s * .25, y + s * .25))
            p.drawLine(QPointF(x + s * .25, y - s * .25), QPointF(x - s * .25, y + s * .25))
    p.restore()


# ------------------------------------------------------------------ the pieces
def wallpaper(p: QPainter, rect: QRectF, finish: str, mark: QRectF | None = None):
    """Onyx (OBSIDIAN) or pearl (AURORA) with the family's glow and the PR7 lean in light streaks."""
    dark = finish == "obsidian"
    p.fillRect(rect, colour("#060407" if dark else "#DCD3D7"))
    for cx, cy, r, hue, a in ((0.18, 1.05, 0.75, "#DE0639", .55 if dark else .32),
                              (0.92, 0.85, 0.6, "#CD6619", .42 if dark else .28),
                              (0.55, -0.1, 0.5, "#D42E2A", .18 if dark else .12)):
        g = QRadialGradient(QPointF(rect.width() * cx, rect.height() * cy), rect.width() * r)
        g.setColorAt(0, colour(hue, a))
        g.setColorAt(1, colour(hue, 0))
        p.fillRect(rect, g)
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    for i, (x, w, a) in enumerate(((0.30, 0.10, .07), (0.43, 0.03, .10), (0.49, 0.015, .14), (0.70, 0.06, .05))):
        band = QPainterPath()
        top, bottom = rect.top(), rect.bottom()
        lean = rect.height() * widgets.SLANT
        x0 = rect.width() * x
        band.moveTo(x0 + lean, top); band.lineTo(x0 + lean + rect.width() * w, top)
        band.lineTo(x0 + rect.width() * w, bottom); band.lineTo(x0, bottom); band.closeSubpath()
        g = QLinearGradient(0, top, 0, bottom)
        g.setColorAt(0, colour("#FFFFFF", 0))
        g.setColorAt(0.6, colour("#FF6A3A" if dark else "#FFFFFF", a))
        g.setColorAt(1, colour("#FFFFFF", 0))
        p.fillPath(band, g)
    p.restore()
    if mark is not None:   # the PR7-OS mark, faint, where the windows leave it showing
        p.save()
        p.setOpacity(0.12 if dark else 0.16)
        theme.set_finish(finish)
        widgets.draw_mark(p, mark, glow=False)
        theme.set_finish("obsidian")
        p.restore()


def panel(p: QPainter, active: str, running: set[str], launcher_open: bool = False, finish: str = "obsidian"):
    """Plasma's floating panel: the launcher's 7, pinned and running apps, the tray and the clock. Dark in both."""
    r = QRectF(8, H - 8 - 52, W - 16, 52)
    shadow(p, r, 14, 18, 0.7)
    rounded(p, r, 14, colour("#0C0A0D", 0.94), colour("#27222A"))
    btn = QRectF(r.left() + 6, r.top() + 6, 40, 40)
    if launcher_open:
        rounded(p, btn, 10, theme.family_gradient(btn.left(), 0, btn.right(), 0, theme.DIM))
    seven(p, btn.adjusted(9, 9, -9, -9))
    x = btn.right() + 14
    p.setPen(QPen(colour("#27222A"), 1)); p.drawLine(QPointF(x - 7, r.top() + 12), QPointF(x - 7, r.bottom() - 12))
    for letter in ("E", "TM", "W", "M", "P", "Z", "PM"):
        cell = QRectF(x, r.top() + 6, 40, 40)
        if letter == active:
            rounded(p, cell, 10, colour("#FFFFFF", 0.07))
        draw_icon(p, letter, cell.adjusted(6, 5, -6, -7))
        if letter in running:
            bar = QRectF(cell.center().x() - (12 if letter == active else 3), cell.bottom() - 1,
                         24 if letter == active else 6, 3)
            rounded(p, bar, 1.5, theme.family_gradient(bar.left(), 0, bar.right(), 0))
        x += 46
    # tray and clock
    clock = QRectF(r.right() - 118, r.top(), 100, r.height())
    text(p, clock.adjusted(0, 7, 0, -26), "13:42", 15, theme.ON_DARK, True, Qt.AlignmentFlag.AlignCenter)
    text(p, clock.adjusted(0, 26, 0, -7), "Thu 26 Nov", 11.5, "#8A8A92", False, Qt.AlignmentFlag.AlignCenter)
    tx = clock.left() - 22
    for name in ("bell", "battery", "volume", "wifi", "clipboard"):
        line_icon(p, name, QPointF(tx, r.center().y()), 20, "#C9C5C8", 1.6)
        tx -= 34
    p.setPen(QPen(colour("#27222A"), 1)); p.drawLine(QPointF(tx + 10, r.top() + 12), QPointF(tx + 10, r.bottom() - 12))


def titled_window(p: QPainter, rect: QRectF, title: str, letter: str, shot: QImage, finish: str, focused=True):
    """A window in the Paragon decoration: the finish's surface, the title centred, a gradient close key."""
    dark = finish == "obsidian"
    bar_h = 36
    whole = QRectF(rect.left(), rect.top() - bar_h, rect.width(), rect.height() + bar_h)
    shadow(p, whole, 10, 34 if focused else 20, 0.9 if focused else 0.6)
    path = QPainterPath(); path.addRoundedRect(whole, 10, 10)
    p.save()
    p.setClipPath(path)
    bar = QRectF(whole.left(), whole.top(), whole.width(), bar_h)
    p.fillRect(bar, colour("#0E0B0F" if dark else "#E0DBDD"))
    if focused:  # a thread of the family gradient along the top edge
        p.fillRect(QRectF(bar.left(), bar.top(), bar.width(), 2), theme.family_gradient(bar.left(), 0, bar.right(), 0))
    draw_icon(p, letter, QRectF(bar.left() + 12, bar.top() + 9, 18, 18))
    text(p, bar, title, 13, ("#E8E8EA" if focused else "#8A8A92") if dark else ("#26252A" if focused else "#6B6569"),
         focused, Qt.AlignmentFlag.AlignCenter)
    keys_x = bar.right() - 108
    ink = "#C9C5C8" if dark else "#4A4549"
    for i, name in enumerate(("minimise", "maximise")):
        line_icon(p, name, QPointF(keys_x + 18 + i * 34, bar.center().y()), 16, ink, 1.5)
    close = QRectF(bar.right() - 38, bar.top() + 7, 26, 22)
    if focused:
        rounded(p, close, 6, theme.family_gradient(close.left(), 0, close.right(), 0))
        line_icon(p, "close", close.center(), 16, "#FFFFFF", 1.6)
    else:
        line_icon(p, "close", close.center(), 16, ink, 1.5)
    p.drawImage(rect, shot)
    p.restore()
    rounded(p, whole, 10, Qt.BrushStyle.NoBrush, colour("#27222A" if dark else "#A8999F"))


def launcher(p: QPainter):
    """Plasma's launcher (Kickoff) in the family look: account, search, categories, favourites, power keys."""
    r = QRectF(8, H - 8 - 52 - 10 - 660, 700, 660)
    shadow(p, r, 14, 30, 0.9)
    rounded(p, r, 14, colour("#0C0A0D", 0.97), colour("#27222A"))
    # header: account and search
    av = QRectF(r.left() + 22, r.top() + 20, 44, 44)
    p.save(); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(theme.family_gradient(av.left(), 0, av.right(), 0), 2.5)); p.setBrush(colour("#1C1C20"))
    p.drawEllipse(av.adjusted(2, 2, -2, -2)); p.restore()
    text(p, av, "A", 18, theme.ON_DARK, True, Qt.AlignmentFlag.AlignCenter)
    text(p, QRectF(av.right() + 12, av.top(), 200, 24), "ari", 15, theme.ON_DARK, True)
    text(p, QRectF(av.right() + 12, av.top() + 22, 220, 22), "PARAGON PR7-OS", 11, "#8A8A92", True, spacing=1.2)
    search = QRectF(r.left() + 300, r.top() + 22, r.width() - 322, 40)
    rounded(p, search, 10, colour("#151217"), colour("#3A3238"))
    p.fillRect(QRectF(search.left() + 10, search.bottom() - 2, search.width() - 20, 2),
               theme.family_gradient(search.left(), 0, search.right(), 0))
    line_icon(p, "search", QPointF(search.left() + 22, search.center().y()), 18, "#8A8A92")
    text(p, search.adjusted(42, 0, 0, 0), "Type to search…", 14, "#6E6A70")
    p.setPen(QPen(colour("#27222A"), 1)); p.drawLine(QPointF(r.left() + 16, r.top() + 82), QPointF(r.right() - 16, r.top() + 82))
    # categories
    cats = [("star", "FAVOURITES"), ("grid", "ALL APPLICATIONS"), ("folder", "PARAGON"), ("folder", "INTERNET"),
            ("folder", "MULTIMEDIA"), ("folder", "OFFICE"), ("folder", "SYSTEM"), ("folder", "UTILITIES"),
            ("settings", "SETTINGS")]
    y = r.top() + 96
    for i, (g, name) in enumerate(cats):
        row = QRectF(r.left() + 12, y, 212, 38)
        if i == 0:
            rounded(p, row, 8, theme.family_gradient(row.left(), 0, row.right(), 0, theme.LIT, 0.9))
        line_icon(p, g, QPointF(row.left() + 22, row.center().y()), 18, "#FFFFFF" if i == 0 else "#C9C5C8", 1.5)
        text(p, row.adjusted(44, 0, 0, 0), name, 12, "#FFFFFF" if i == 0 else "#C9C5C8", True, spacing=1.0)
        y += 42
    p.setPen(QPen(colour("#27222A"), 1)); p.drawLine(QPointF(r.left() + 236, r.top() + 96), QPointF(r.left() + 236, r.bottom() - 74))
    # favourites grid
    gx, gy = r.left() + 252, r.top() + 98
    for i, (letter, name, _what) in enumerate(APPS[:16]):
        cell = QRectF(gx + (i % 4) * 108, gy + (i // 4) * 120, 100, 116)
        if i == 0:
            rounded(p, cell, 10, colour("#FFFFFF", 0.06), colour("#3A3238"))
        draw_icon(p, letter, QRectF(cell.center().x() - 26, cell.top() + 10, 52, 52))
        text(p, QRectF(cell.left(), cell.top() + 70, cell.width(), 20), name, 13, theme.ON_DARK, True,
             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        text(p, QRectF(cell.left(), cell.top() + 90, cell.width(), 18), f"PR7-{letter}", 10.5, "#8A8A92", False,
             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, 0.8)
    # footer
    p.setPen(QPen(colour("#27222A"), 1)); p.drawLine(QPointF(r.left() + 16, r.bottom() - 62), QPointF(r.right() - 16, r.bottom() - 62))
    fx = r.left() + 16
    for g, name in (("leave", "LOG OUT"), ("sleep", "SLEEP"), ("restart", "RESTART"), ("power", "SHUT DOWN")):
        key = QRectF(fx, r.bottom() - 50, 160, 38)
        rounded(p, key, 8, colour("#1C1C20"), colour("#3A3238"))
        line_icon(p, g, QPointF(key.left() + 22, key.center().y()), 17, "#C9C5C8", 1.5)
        text(p, key.adjusted(42, 0, 0, 0), name, 11.5, theme.ON_DARK, True, spacing=1.0)
        fx += 170


def notification(p: QPainter):
    r = QRectF(W - 8 - 400, H - 8 - 52 - 12 - 108, 400, 108)
    shadow(p, r, 12, 22, 0.8)
    rounded(p, r, 12, colour("#0C0A0D", 0.96), colour("#27222A"))
    p.fillRect(QRectF(r.left() + 1, r.top() + 14, 3, r.height() - 28), theme.family_gradient(0, r.top(), 0, r.bottom()))
    draw_icon(p, "BK", QRectF(r.left() + 18, r.top() + 18, 36, 36))
    text(p, QRectF(r.left() + 66, r.top() + 14, 300, 22), "PR7-BK", 11, "#8A8A92", True, spacing=1.2)
    text(p, QRectF(r.right() - 90, r.top() + 14, 74, 22), "now", 11, "#8A8A92", False,
         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    text(p, QRectF(r.left() + 66, r.top() + 36, 320, 24), "Backup finished", 15, theme.ON_DARK, True)
    text(p, QRectF(r.left() + 66, r.top() + 60, 320, 40), "Documents and Pictures: 4,812 files,\n2.1 GB, no warnings",
         12.5, "#B9B5B8", False, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)


def shot(shots: Path, rel: str, size=(1280, 800)) -> QImage:
    img = QImage(str(shots / rel))
    if img.isNull():  # no screenshot: a plain stand-in, so the layout still shows
        img = QImage(*size, QImage.Format.Format_RGB32)
        img.fill(colour("#151217"))
    return img


# ------------------------------------------------------------------ the screens
def desktop_obsidian(shots: Path) -> QImage:
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    wallpaper(p, QRectF(0, 0, W, H), "obsidian", QRectF(1180, 860, 620, 110))
    e = shot(shots, "e/grid.png").scaled(1120, 700, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
    titled_window(p, QRectF(560, 120, e.width(), e.height()), "Elseworld shoot — Files", "E", e, "obsidian")
    launcher(p)
    panel(p, "E", {"E", "M", "TM"}, launcher_open=True)
    p.end()
    return img


def desktop_aurora(shots: Path) -> QImage:
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    wallpaper(p, QRectF(0, 0, W, H), "aurora", QRectF(110, 800, 560, 100))
    e = shot(shots, "e/grid_aurora.png").scaled(980, 612, Qt.AspectRatioMode.KeepAspectRatio,
                                                 Qt.TransformationMode.SmoothTransformation)
    titled_window(p, QRectF(90, 110, e.width(), e.height()), "Pictures — Files", "E", e, "aurora", focused=False)
    pv = shot(shots, "p/main_window_aurora.png").scaled(1060, 680, Qt.AspectRatioMode.KeepAspectRatio,
                                                         Qt.TransformationMode.SmoothTransformation)
    titled_window(p, QRectF(760, 250, pv.width(), pv.height()), "IMG_2041.jpg — Images", "P", pv, "aurora")
    notification(p)
    panel(p, "P", {"E", "P", "W"}, finish="aurora")
    p.end()
    return img


def login() -> QImage:
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    wallpaper(p, QRectF(0, 0, W, H), "obsidian")
    p.fillRect(QRectF(0, 0, W, H), colour("#060407", 0.45))
    text(p, QRectF(48, 40, 160, 34), "PARAGON", 22, theme.ON_DARK)
    widgets.draw_mark(p, QRectF(176, 40, 300, 34), glow=True)
    text(p, QRectF(0, 170, W, 120), "13:42", 112, theme.ON_DARK, False, Qt.AlignmentFlag.AlignCenter)
    text(p, QRectF(0, 290, W, 34), "THURSDAY 26 NOVEMBER", 15, "#B9B5B8", True, Qt.AlignmentFlag.AlignCenter, 2.5)
    av = QRectF(W / 2 - 62, 400, 124, 124)
    p.setPen(QPen(theme.family_gradient(av.left(), 0, av.right(), 0), 4)); p.setBrush(colour("#1C1C20"))
    p.drawEllipse(av.adjusted(3, 3, -3, -3))
    text(p, av, "A", 46, theme.ON_DARK, True, Qt.AlignmentFlag.AlignCenter)
    text(p, QRectF(0, 540, W, 34), "ari", 22, theme.ON_DARK, True, Qt.AlignmentFlag.AlignCenter)
    field = QRectF(W / 2 - 190, 600, 380, 48)
    rounded(p, field, 12, colour("#0C0A0D", 0.9), colour("#3A3238"))
    p.fillRect(QRectF(field.left() + 12, field.bottom() - 2, field.width() - 24, 2),
               theme.family_gradient(field.left(), 0, field.right(), 0))
    text(p, field.adjusted(18, 0, -60, 0), "• • • • • • •", 15, "#E8E8EA")
    go = QRectF(field.right() - 44, field.top() + 6, 36, 36)
    rounded(p, go, 9, theme.family_gradient(go.left(), 0, go.right(), 0))
    p.setPen(QPen(colour("#FFFFFF"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    c = go.center()
    p.drawLine(QPointF(c.x() - 8, c.y()), QPointF(c.x() + 8, c.y()))
    p.drawLine(QPointF(c.x() + 2, c.y() - 6), QPointF(c.x() + 8, c.y()))
    p.drawLine(QPointF(c.x() + 2, c.y() + 6), QPointF(c.x() + 8, c.y()))
    text(p, QRectF(0, 662, W, 24), "CAPS LOCK IS OFF  ·  EN", 11.5, "#8A8A92", True, Qt.AlignmentFlag.AlignCenter, 1.5)
    # bottom bar: session, keyboard, power
    text(p, QRectF(48, H - 76, 400, 40), "SESSION   PLASMA (WAYLAND)", 12, "#B9B5B8", True, spacing=1.5)
    x = W - 48
    for g, name in (("power", "SHUT DOWN"), ("restart", "RESTART"), ("sleep", "SLEEP")):
        key = QRectF(x - 150, H - 80, 150, 44)
        rounded(p, key, 10, colour("#0C0A0D", 0.85), colour("#3A3238"))
        line_icon(p, g, QPointF(key.left() + 24, key.center().y()), 18, "#C9C5C8", 1.6)
        text(p, key.adjusted(46, 0, 0, 0), name, 11.5, theme.ON_DARK, True, spacing=1.2)
        x -= 162
    p.end()
    return img


def grub() -> QImage:
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(QRectF(0, 0, W, H), colour("#060407"))
    g = QRadialGradient(QPointF(W / 2, H * 1.1), W * 0.6)
    g.setColorAt(0, colour("#DE0639", 0.25)); g.setColorAt(1, colour("#DE0639", 0))
    p.fillRect(QRectF(0, 0, W, H), g)
    widgets.draw_mark(p, QRectF(W / 2 - 230, 170, 460, 80), glow=True)
    text(p, QRectF(0, 262, W, 30), "BASED ON DEBIAN 13", 13, "#8A8A92", True, Qt.AlignmentFlag.AlignCenter, 3)
    box = QRectF(W / 2 - 420, 360, 840, 300)
    rounded(p, box, 12, colour("#0C0A0D"), colour("#27222A"))
    entries = ["Paragon PR7-OS", "Advanced options for Paragon PR7-OS", "Memory test", "UEFI firmware settings"]
    y = box.top() + 24
    for i, e in enumerate(entries):
        row = QRectF(box.left() + 18, y, box.width() - 36, 52)
        if i == 0:
            rounded(p, row, 8, theme.family_gradient(row.left(), 0, row.right(), 0))
        text(p, row.adjusted(22, 0, 0, 0), e, 18, "#FFFFFF" if i == 0 else "#C9C5C8", i == 0)
        y += 64
    text(p, QRectF(0, 700, W, 26), "↑ ↓  CHOOSE    ENTER  START    E  EDIT    C  COMMAND LINE", 12.5, "#8A8A92",
         True, Qt.AlignmentFlag.AlignCenter, 2)
    text(p, QRectF(0, 736, W, 26), "Starting Paragon PR7-OS in 4 s", 14, "#B9B5B8", False, Qt.AlignmentFlag.AlignCenter)
    p.end()
    return img


def splash() -> QImage:
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(QRectF(0, 0, W, H), colour("#060407"))
    widgets.draw_mark(p, QRectF(W / 2 - 260, H / 2 - 90, 520, 96), glow=True)
    text(p, QRectF(0, H / 2 - 150, W, 30), "PARAGON", 22, theme.ON_DARK, False, Qt.AlignmentFlag.AlignCenter, 8)
    track = QRectF(W / 2 - 160, H / 2 + 60, 320, 4)
    rounded(p, track, 2, colour("#1C1C20"))
    fill = QRectF(track.left(), track.top(), track.width() * 0.62, track.height())
    rounded(p, fill, 2, theme.family_gradient(fill.left(), 0, fill.right(), 0))
    gl = QRadialGradient(fill.topRight(), 18)
    gl.setColorAt(0, colour("#FF7A1A", 0.7)); gl.setColorAt(1, colour("#FF7A1A", 0))
    p.fillRect(QRectF(fill.right() - 18, fill.top() - 18, 36, 40), gl)
    text(p, QRectF(0, H - 80, W, 24), "BASED ON DEBIAN 13", 11.5, "#5E5A60", True, Qt.AlignmentFlag.AlignCenter, 3)
    p.end()
    return img


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/mockup")
    shots = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "docs" / "shots"
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])  # noqa: F841 - fonts and painting need it
    theme.load_fonts()
    theme.set_finish("obsidian")
    for name, make in (("desktop_obsidian", lambda: desktop_obsidian(shots)),
                       ("desktop_aurora", lambda: desktop_aurora(shots)),
                       ("login", login), ("boot_menu", grub), ("boot_splash", splash)):
        make().save(str(out / f"{name}.png"))
        print(out / f"{name}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
