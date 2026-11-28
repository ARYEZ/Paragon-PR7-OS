"""Every PR7-OS theme file, generated from the family theme (no hand-edited art, so nothing drifts from it).

    python -m pr7os.assets ROOT        writes the files into ROOT, laid out like the installed system

What goes where (all read by Plasma, SDDM, Plymouth, GRUB and Calamares as their own formats):
    usr/share/color-schemes/ParagonObsidian.colors, ParagonAurora.colors    Plasma colour schemes
    usr/share/aurorae/themes/Paragon-{Obsidian,Aurora}/                     the window decoration (Aurorae SVG)
    usr/share/wallpapers/Paragon/                                           wallpaper (AURORA light, OBSIDIAN dark)
    usr/share/plasma/look-and-feel/org.paragon.pr7os.{obsidian,aurora}/     global themes: defaults, panel, splash
    usr/share/paragon/plasma-colors                                         the panel / launcher colours (a hook
                                                                            puts them into a copy of Breeze Dark)
    usr/share/sddm/themes/paragon/                                          the login screen (static QML + art)
    usr/share/plymouth/themes/paragon/                                      the boot splash
    usr/share/grub/themes/paragon/                                          the boot menu
    etc/xdg/...                                                             system defaults (OBSIDIAN)
The family rule holds everywhere: hues ~318 -> 0 -> 42 deg, pearl and onyx greys, nothing blue or green.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient

from . import theme, widgets

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"                 # QML, scripts and templates written by hand (no colours of their own)
VERSION_NAME = "Paragon PR7-OS"
DEBIAN = "Debian 13"

# --------------------------------------------------------------------------- the two finishes, as Plasma colours
# Plasma's colour roles. Each finish fills every role (KDE's own blues / greens never show through).
FINISH_COLOURS = {
    "obsidian": {
        "Window": ("#0C0A0D", "#151217"), "View": ("#060407", "#09070A"), "Button": ("#1C1C20", "#303034"),
        "Header": ("#0E0B0F", "#151217"), "Tooltip": ("#050405", "#0C0A0D"), "Complementary": ("#0C0A0D", "#151217"),
        "Selection": ("#E8303A", "#C42633"),
        "text": "#E8E8EA", "dim": "#8A8A92", "link": "#FF7A1A", "visited": "#E0457A", "negative": "#FF3B2F",
        "neutral": "#FF9A3C", "positive": "#F2B48C", "focus": "#F4353A", "hover": "#FF7A1A",
        "wm_active": "#0E0B0F", "wm_inactive": "#0C0A0D",
    },
    "aurora": {
        "Window": ("#D9D0D4", "#E0DBDD"), "View": ("#E6E4E5", "#DFDBDD"), "Button": ("#1C1C20", "#303034"),
        "Header": ("#E0DBDD", "#D9D0D4"), "Tooltip": ("#050405", "#0C0A0D"), "Complementary": ("#0C0A0D", "#151217"),
        "Selection": ("#E8303A", "#C42633"),
        "text": "#26252A", "dim": "#6B6569", "link": "#C24A12", "visited": "#B0285A", "negative": "#C81E2A",
        "neutral": "#B85A10", "positive": "#9C5A3C", "focus": "#E8303A", "hover": "#C24A12",
        "wm_active": "#E0DBDD", "wm_inactive": "#D9D0D4",
    },
}
DARK_ROLES = {"Button", "Tooltip", "Complementary", "Selection"}   # keys, tooltips, panels stay dark in both


def rgb(hex_: str) -> str:
    c = QColor(hex_)
    return f"{c.red()},{c.green()},{c.blue()}"


def colour_groups(finish: str) -> dict[str, dict[str, str]]:
    """The [Colors:*] groups of a KDE colour scheme (and kdeglobals) for a finish."""
    f = FINISH_COLOURS[finish]
    groups = {}
    for role in ("Window", "View", "Button", "Header", "Tooltip", "Complementary", "Selection"):
        normal, alternate = f[role]
        dark_text = role in DARK_ROLES
        text_c = "#FFFFFF" if role == "Selection" else ("#E8E8EA" if dark_text else f["text"])
        dim = "#F0C8C0" if role == "Selection" else ("#8A8A92" if dark_text else f["dim"])
        on_dark = dark_text or finish == "obsidian"
        groups[f"Colors:{role}"] = {
            "BackgroundNormal": rgb(normal), "BackgroundAlternate": rgb(alternate),
            "ForegroundNormal": rgb(text_c), "ForegroundInactive": rgb(dim),
            "ForegroundActive": rgb("#FFB070" if role == "Selection" else (FINISH_COLOURS["obsidian"]["hover"] if on_dark else f["hover"])),
            "ForegroundLink": rgb("#FFD0A0" if role == "Selection" else (FINISH_COLOURS["obsidian"]["link"] if on_dark else f["link"])),
            "ForegroundVisited": rgb("#FFC0D0" if role == "Selection" else (FINISH_COLOURS["obsidian"]["visited"] if on_dark else f["visited"])),
            "ForegroundNegative": rgb(FINISH_COLOURS["obsidian"]["negative"] if on_dark else f["negative"]),
            "ForegroundNeutral": rgb(FINISH_COLOURS["obsidian"]["neutral"] if on_dark else f["neutral"]),
            "ForegroundPositive": rgb(FINISH_COLOURS["obsidian"]["positive"] if on_dark else f["positive"]),
            "DecorationFocus": rgb(f["focus"]), "DecorationHover": rgb(f["hover"]),
        }
    groups["Colors:Header][Inactive"] = dict(groups["Colors:Header"])
    groups["WM"] = {
        "activeBackground": rgb(f["wm_active"]), "activeBlend": rgb(f["wm_active"]),
        "activeForeground": rgb(f["text"]), "inactiveBackground": rgb(f["wm_inactive"]),
        "inactiveBlend": rgb(f["wm_inactive"]), "inactiveForeground": rgb(f["dim"]),
    }
    groups["ColorEffects:Disabled"] = {"Color": rgb("#38323A" if finish == "obsidian" else "#B8AFB3"),
                                       "ColorAmount": "0", "ColorEffect": "0", "ContrastAmount": "0.65",
                                       "ContrastEffect": "1", "IntensityAmount": "0.1", "IntensityEffect": "2"}
    groups["ColorEffects:Inactive"] = {"ChangeSelectionColor": "true", "Color": rgb("#0C0A0D"),
                                       "ColorAmount": "0.025", "ColorEffect": "2", "ContrastAmount": "0.1",
                                       "ContrastEffect": "2", "Enable": "false", "IntensityAmount": "0",
                                       "IntensityEffect": "0"}
    return groups


def ini(groups: dict[str, dict[str, str]]) -> str:
    out = []
    for name, keys in groups.items():
        out.append(f"[{name}]")
        out += [f"{k}={v}" for k, v in keys.items()]
        out.append("")
    return "\n".join(out)


def colour_scheme(finish: str) -> str:
    name = "ParagonObsidian" if finish == "obsidian" else "ParagonAurora"
    groups = colour_groups(finish)
    groups["General"] = {"ColorScheme": name, "Name": f"Paragon {finish.title()}", "shadeSortColumn": "true"}
    groups["KDE"] = {"contrast": "4"}
    return ini(groups)


# --------------------------------------------------------------------------- painting helpers
def colour(hex_: str, alpha: float = 1.0) -> QColor:
    c = QColor(hex_)
    c.setAlphaF(alpha)
    return c


def new_image(w: int, h: int) -> tuple[QImage, QPainter]:
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    return img, p


def wallpaper(w: int, h: int, finish: str, mark: bool = True) -> QImage:
    """The mock-up's wallpaper: onyx or pearl, the family glow, the PR7 lean in light, the mark faint."""
    img, p = new_image(w, h)
    rect = QRectF(0, 0, w, h)
    dark = finish == "obsidian"
    p.fillRect(rect, colour("#060407" if dark else "#DCD3D7"))
    for cx, cy, r, hue, a in ((0.18, 1.05, 0.75, "#DE0639", .55 if dark else .32),
                              (0.92, 0.85, 0.6, "#CD6619", .42 if dark else .28),
                              (0.55, -0.1, 0.5, "#D42E2A", .18 if dark else .12)):
        g = QRadialGradient(QPointF(w * cx, h * cy), w * r)
        g.setColorAt(0, colour(hue, a))
        g.setColorAt(1, colour(hue, 0))
        p.fillRect(rect, g)
    for x, bw, a in ((0.30, 0.10, .07), (0.43, 0.03, .10), (0.49, 0.015, .14), (0.70, 0.06, .05)):
        band = QPainterPath()
        lean = h * widgets.SLANT
        x0 = w * x
        band.moveTo(x0 + lean, 0); band.lineTo(x0 + lean + w * bw, 0)
        band.lineTo(x0 + w * bw, h); band.lineTo(x0, h); band.closeSubpath()
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, colour("#FFFFFF", 0))
        g.setColorAt(0.6, colour("#FF6A3A" if dark else "#FFFFFF", a))
        g.setColorAt(1, colour("#FFFFFF", 0))
        p.fillPath(band, g)
    if mark:
        p.setOpacity(0.12 if dark else 0.16)
        theme.set_finish(finish)
        widgets.draw_mark(p, QRectF(w * 0.615, h * 0.80, w * 0.32, h * 0.10), glow=False)
        theme.set_finish("obsidian")
        p.setOpacity(1)
    p.end()
    return img


def seven_path(rect: QRectF) -> QPainterPath:
    h = rect.height()
    pts = [(0, 0), (.8, 0), (.8, .2), (.44, 1), (.18, 1), (.5, .2), (0, .2)]
    x0 = rect.center().x() - (0.8 + widgets.SLANT) * h / 2
    path = QPainterPath()
    for i, (x, y) in enumerate(pts):
        pt = QPointF(x0 + (x + widgets.SLANT * (1 - y)) * h, rect.top() + y * h)
        path.moveTo(pt) if i == 0 else path.lineTo(pt)
    path.closeSubpath()
    return path


def mark_image(w: int, h: int, glow: bool = True, text_colour: str | None = None) -> QImage:
    img, p = new_image(w, h)
    if text_colour:
        theme.TEXT = text_colour
    widgets.draw_mark(p, QRectF(h * 0.1, h * 0.1, w - h * 0.2, h * 0.8), glow=glow)
    theme.set_finish("obsidian")
    p.end()
    return img


def face_image(size: int = 256) -> QImage:
    """The account picture until you choose your own: onyx with a soft family glow and the gradient 7 (the login and
    lock screens crop it to a circle)."""
    from PySide6.QtGui import QRadialGradient
    img, p = new_image(size, size)
    p.fillRect(QRectF(0, 0, size, size), colour("#141116"))
    glow = QRadialGradient(size * 0.5, size * 0.62, size * 0.62)
    glow.setColorAt(0, colour("#DE0639", 0.30))
    glow.setColorAt(1, colour("#DE0639", 0.0))
    p.fillRect(QRectF(0, 0, size, size), glow)
    seven = QRectF(size * 0.22, size * 0.28, size * 0.56, size * 0.44)
    p.fillPath(seven_path(seven), theme.family_gradient(seven.left(), 0, seven.right(), 0))
    p.end()
    return img


def text_image(s: str, px: int, hex_: str, w: int, h: int, spacing: float = 0, bold: bool = False) -> QImage:
    from PySide6.QtGui import QFont
    img, p = new_image(w, h)
    f = QFont(UI_FONT)
    f.setPixelSize(px)
    f.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
    if spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    p.setFont(f)
    p.setPen(colour(hex_))
    p.drawText(QRectF(0, 0, w, h), int(Qt.AlignmentFlag.AlignCenter), s)
    p.end()
    return img


# --------------------------------------------------------------------------- SVG (the decoration, the start icon)
def _stops(alpha: float = 1.0) -> str:
    out = []
    for pos, hex_ in theme.FAMILY_STOPS:
        c = theme._scaled(hex_, theme.LIT)
        out.append(f'<stop offset="{pos}" stop-color="#{c.red():02X}{c.green():02X}{c.blue():02X}" '
                   f'stop-opacity="{alpha}"/>')
    return "".join(out)


def start_icon_svg() -> str:
    """The launcher's 7 (Plasma's start button): PR7's geometry, the family gradient."""
    path = seven_path(QRectF(0, 8, 64, 48))
    d = []
    for i in range(path.elementCount()):
        e = path.elementAt(i)
        d.append(("M" if e.isMoveTo() else "L") + f"{e.x:.2f},{e.y:.2f}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0">{_stops()}</linearGradient></defs>'
            f'<path d="{" ".join(d)} Z" fill="url(#g)"/></svg>\n')


def aurorae(finish: str) -> dict[str, str]:
    """An Aurorae window decoration: the finish's title bar, rounded top corners, a thread of the family gradient
    along the active window's top, a gradient close key. Returns {file name: content}."""
    dark = finish == "obsidian"
    name = "Paragon-Obsidian" if dark else "Paragon-Aurora"
    bar = FINISH_COLOURS[finish]["wm_active"]
    bar_in = FINISH_COLOURS[finish]["wm_inactive"]
    edge = "#27222A" if dark else "#A8999F"
    ink = "#C9C5C8" if dark else "#4A4549"
    ink_in = "#6E6A70" if dark else "#8A8086"
    title_h, r = 36, 10

    def frame(prefix: str, fill: str, thread: bool) -> str:
        g = f'<rect x="0" y="0" width="{{w}}" height="2" fill="url(#fam)"/>' if thread else ""
        parts = {
            "topleft": (r, title_h, f'<path d="M0,{title_h} V{r} A{r},{r} 0 0 1 {r},0 H{r} V{title_h} Z" fill="{fill}"/>'
                        + (f'<path d="M{r},0 A{r},{r} 0 0 0 0,{r} V{r + 2} A{r - 2},{r - 2} 0 0 1 {r},2 Z" fill="#DE0639"/>'
                           if thread else "")),
            "top": (8, title_h, f'<rect width="8" height="{title_h}" fill="{fill}"/>' + g.format(w=8)),
            "topright": (r, title_h, f'<path d="M0,0 A{r},{r} 0 0 1 {r},{r} V{title_h} H0 Z" fill="{fill}"/>'
                         + (f'<path d="M0,0 A{r},{r} 0 0 1 {r},{r} V{r + 2} A{r - 2},{r - 2} 0 0 0 0,2 Z" fill="#CD6619"/>'
                            if thread else "")),
            "left": (1, 8, f'<rect width="1" height="8" fill="{edge}"/>'),
            "center": (8, 8, f'<rect width="8" height="8" fill="{fill}"/>'),
            "right": (1, 8, f'<rect width="1" height="8" fill="{edge}"/>'),
            "bottomleft": (1, 1, f'<rect width="1" height="1" fill="{edge}"/>'),
            "bottom": (8, 1, f'<rect width="8" height="1" fill="{edge}"/>'),
            "bottomright": (1, 1, f'<rect width="1" height="1" fill="{edge}"/>'),
        }
        out, x = [], 0
        for piece, (w, h, body) in parts.items():
            out.append(f'<g id="{prefix}-{piece}" transform="translate({x},0)">{body}</g>')
            x += w + 4
        return "".join(out)

    defs = f'<defs><linearGradient id="fam" x1="0" y1="0" x2="1" y2="0">{_stops()}</linearGradient></defs>'
    deco = (f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="80">{defs}'
            + frame("decoration", bar, True) + frame("decoration-inactive", bar_in, False) + "</svg>\n")

    def button(glyph: str, close: bool = False) -> str:
        w, h = 26, 22

        def state(prefix: str, bg: str, fg: str) -> str:
            back = f'<rect width="{w}" height="{h}" rx="6" fill="{bg}"/>' if bg else \
                f'<rect width="{w}" height="{h}" fill="none"/>'
            return f'<g id="{prefix}-center">{back}<g stroke="{fg}" stroke-width="1.6" stroke-linecap="round" ' \
                   f'fill="none">{glyph}</g></g>'
        if close:
            return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">'
                    f'<defs><linearGradient id="fam" x1="0" y1="0" x2="1" y2="0">{_stops()}</linearGradient>'
                    f'<linearGradient id="lit" x1="0" y1="0" x2="1" y2="0">{_stops(0.8)}</linearGradient></defs>'
                    + state("active", "url(#fam)", "#FFFFFF") + state("hover", "url(#lit)", "#FFFFFF")
                    + state("pressed", "#9E1A26", "#FFFFFF") + state("inactive", "", ink_in)
                    + state("deactivated", "", ink_in) + "</svg>\n")
        hover = "#FFFFFF1F" if dark else "#0000001A"
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">'
                + state("active", "", ink) + state("hover", hover, ink) + state("pressed", hover, ink)
                + state("inactive", "", ink_in) + state("deactivated", "", ink_in) + "</svg>\n")

    x_glyph = '<path d="M9,7 L17,15 M17,7 L9,15"/>'
    files = {
        "decoration.svg": deco,
        "close.svg": button(x_glyph, close=True),
        "minimize.svg": button('<path d="M8,13 H18"/>'),
        "maximize.svg": button('<rect x="8.5" y="6.5" width="9" height="9"/>'),
        "restore.svg": button('<rect x="8.5" y="8.5" width="7" height="7"/><path d="M10.5,6.5 H17.5 V13.5"/>'),
        "metadata.desktop": (f"[Desktop Entry]\nName=Paragon {finish.title()}\nComment=Paragon PR7-OS window decoration\n"
                             f"X-KDE-PluginInfo-Name={name}\nX-KDE-PluginInfo-Author=Paragon\n"
                             f"X-KDE-PluginInfo-Version=1.0\nX-KDE-PluginInfo-License=GPL\n"),
        f"{name}rc": "\n".join([
            "[General]", f"ActiveTextColor={rgb('#E8E8EA' if dark else '#26252A')}",
            f"InactiveTextColor={rgb('#8A8A92' if dark else '#6B6569')}", "UseTextShadow=false",
            "TitleAlignment=Center", "TitleVerticalAlignment=Center", "Animation=120", "Shadow=true",
            "DecorationPosition=0", "ButtonHeight=22", "ButtonWidth=26", "ButtonSpacing=8", "ButtonMarginTop=0",
            "ExplicitButtonSpacer=10", "PaddingTop=0", "PaddingBottom=0", "PaddingLeft=0", "PaddingRight=0",
            "BorderLeft=1", "BorderRight=1", "BorderBottom=1", "TitleEdgeTop=7", "TitleEdgeBottom=7",
            "TitleEdgeLeft=12", "TitleEdgeRight=12", "TitleEdgeTopMaximized=7", "TitleEdgeBottomMaximized=7",
            "TitleEdgeLeftMaximized=12", "TitleEdgeRightMaximized=12", "TitleBorderLeft=10", "TitleBorderRight=10",
            "TitleHeight=22", ""]),
    }
    return files


# --------------------------------------------------------------------------- Plasma: global themes and defaults
# Bebas Neue everywhere (the owner's choice; capitals only, one weight): a size up from Inter's, it's a tall condensed face.
# Terminals keep the fixed-width font; the login screen's password field keeps Inter.
UI_FONT = "Bebas Neue"
FONT = "Bebas Neue,12,-1,5,400,0,0,0,0,0,0,0,0,0,0,1"
FONT_SMALL = "Bebas Neue,10,-1,5,400,0,0,0,0,0,0,0,0,0,0,1"
FONT_BOLD = "Bebas Neue,12,-1,5,400,0,0,0,0,0,0,0,0,0,0,1"
FONT_MONO = "DejaVu Sans Mono,10,-1,5,400,0,0,0,0,0,0,0,0,0,0,1"


def plasma_settings(finish: str) -> dict[str, dict[str, dict[str, str]]]:
    """{config file: {group: {key: value}}}: what a global theme sets (and the system defaults for OBSIDIAN)."""
    dark = finish == "obsidian"
    scheme = "ParagonObsidian" if dark else "ParagonAurora"
    lnf = f"org.paragon.pr7os.{finish}"
    return {
        "kdeglobals": {
            "General": {"ColorScheme": scheme, "font": FONT, "fixed": FONT_MONO, "smallestReadableFont": FONT_SMALL,
                        "toolBarFont": FONT, "menuFont": FONT, "AccentColor": rgb("#E8303A")},
            "KDE": {"widgetStyle": "Breeze", "LookAndFeelPackage": lnf},
            "Icons": {"Theme": "breeze-dark" if dark else "breeze"},
            "WM": {"activeFont": FONT_BOLD},
        },
        "plasmarc": {"Theme": {"name": "paragon"}},
        "kwinrc": {"org.kde.kdecoration2": {"library": "org.kde.kwin.aurorae",
                                            "theme": f"__aurorae__svg__Paragon-{finish.title()}",
                                            "ButtonsOnLeft": "", "ButtonsOnRight": "IAX"}},
        "kcminputrc": {"Mouse": {"cursorTheme": "breeze_cursors"}},
        "ksplashrc": {"KSplash": {"Engine": "KSplashQML", "Theme": lnf}},
        # the lock screen's wallpaper: the plugin named, and the wallpaper as the desktop gives it (a full path; the
        # bare name "Paragon" isn't found, and 0.1.1 locked on KDE's own purple picture)
        "kscreenlockerrc": {"Greeter": {"WallpaperPlugin": "org.kde.image"},
                            "Greeter][Wallpaper][org.kde.image][General": {
                                "Image": "file:///usr/share/wallpapers/Paragon/",
                                "PreviewImage": "file:///usr/share/wallpapers/Paragon/"}},
    }


LAYOUT_APPS = ["pr7-e", "pr7-tm", "pr7-w", "pr7-m", "pr7-p", "pr7-z", "pr7-pm"]


def layout_js() -> str:
    """Plasma's first-login layout: the mock-up's floating bottom panel and the Paragon wallpaper."""
    launchers = ", ".join(f'"applications:{a}.desktop"' for a in LAYOUT_APPS)
    return f"""// Paragon PR7-OS: the floating bottom panel of the mock-up (launcher, pinned apps, tray, clock).
var panel = new Panel;
panel.location = "bottom";
panel.height = 2 * Math.floor(gridUnit * 2.6 / 2);
panel.floating = true;

var kickoff = panel.addWidget("org.kde.plasma.kickoff");
kickoff.currentConfigGroup = ["General"];
kickoff.writeConfig("icon", "pr7os-start");
kickoff.writeConfig("favoritesPortedToKAstats", true);

var tasks = panel.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("launchers", [{launchers}]);   // a list: one string would be one (unknown) launcher

panel.addWidget("org.kde.plasma.marginsseparator");
panel.addWidget("org.kde.plasma.systemtray");
var clock = panel.addWidget("org.kde.plasma.digitalclock");
clock.currentConfigGroup = ["Appearance"];
clock.writeConfig("showDate", true);
clock.writeConfig("dateFormat", "custom");
clock.writeConfig("customDateFormat", "ddd d MMM");
panel.addWidget("org.kde.plasma.showdesktop");

var all = desktops();
for (var i = 0; i < all.length; ++i) {{
    var d = all[i];
    d.wallpaperPlugin = "org.kde.image";
    d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    d.writeConfig("Image", "file:///usr/share/wallpapers/Paragon/");
}}
"""


def look_and_feel(finish: str) -> dict[str, str | QImage]:
    lnf = f"org.paragon.pr7os.{finish}"
    title = f"Paragon {finish.title()}"
    defaults = []
    for cfg, groups in plasma_settings(finish).items():
        for group, keys in groups.items():
            defaults.append(f"[{cfg}][{group}]")
            defaults += [f"{k}={v}" for k, v in keys.items()]
            defaults.append("")
    defaults += ["[Wallpaper]", "Image=Paragon", ""]
    meta = ('{\n  "KPlugin": {\n    "Id": "%s",\n    "Name": "%s",\n    "Description": "Paragon PR7-OS in %s: the '
            'family\'s colours, Inter and the PR7 mark",\n    "Authors": [{"Name": "Paragon"}],\n    "Category": '
            '"",\n    "License": "GPL-2.0+",\n    "Version": "1.0",\n    "Website": ""\n  },\n  '
            '"KPackageStructure": "Plasma/LookAndFeel",\n  "X-Plasma-APIVersion": "2"\n}\n') % (lnf, title,
                                                                                               finish.upper())
    splash = (STATIC / "Splash.qml").read_text(encoding="utf-8")
    preview = wallpaper(1280, 720, finish).scaled(640, 360, Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)
    return {"metadata.json": meta, "contents/defaults": "\n".join(defaults),
            "contents/layouts/org.kde.plasma.desktop-layout.js": layout_js(),
            "contents/splash/Splash.qml": splash, "contents/splash/images/mark.png": mark_image(1040, 200),
            "contents/previews/preview.png": preview,
            "contents/previews/fullscreenpreview.jpg": wallpaper(1920, 1080, finish)}


# --------------------------------------------------------------------------- boot menu, splash, login screen
def grub_background(w: int = 1920, h: int = 1080) -> QImage:
    """The boot menu's picture: the mark, "based on Debian 13", the menu's box (GRUB draws the entries on it)."""
    img, p = new_image(w, h)
    p.fillRect(QRectF(0, 0, w, h), colour("#060407"))
    g = QRadialGradient(QPointF(w / 2, h * 1.1), w * 0.6)
    g.setColorAt(0, colour("#DE0639", 0.25)); g.setColorAt(1, colour("#DE0639", 0))
    p.fillRect(QRectF(0, 0, w, h), g)
    widgets.draw_mark(p, QRectF(w / 2 - 230, 170, 460, 80), glow=True)
    p.drawImage(QPointF(0, 262), text_image(f"BASED ON {DEBIAN.upper()}", 13, "#8A8A92", w, 30, 3, True))
    box = QRectF(w * 0.27, h * 0.33, w * 0.46, h * 0.36)     # three entries (live-build adds "Utilities...")
    p.setPen(QPen(colour("#27222A"), 1)); p.setBrush(colour("#0C0A0D"))
    p.drawRoundedRect(box, 12, 12)
    p.end()
    return img


def grub_select(piece: str) -> QImage:
    """The selected entry's band (GRUB's 9-slice "select_*.png"): rounded ends, the family gradient between."""
    h, r = 52, 8
    if piece == "c":
        img, p = new_image(400, h)
        p.fillRect(QRectF(0, 0, 400, h), theme.family_gradient(0, 0, 400, 0))
    else:
        img, p = new_image(r, h)
        col = "#DE0639" if piece == "w" else "#CD6619"
        c = theme._scaled(col, theme.LIT)
        path = QPainterPath()
        if piece == "w":
            path.addRoundedRect(QRectF(0, 0, 2 * r, h), r, r)
        else:
            path.addRoundedRect(QRectF(-r, 0, 2 * r, h), r, r)
        p.fillPath(path, c)
    p.end()
    return img


def grub_theme_txt() -> str:
    return """# Paragon PR7-OS boot menu (generated by pr7os.assets)
title-text: ""
desktop-image: "background.png"
desktop-color: "#060407"
terminal-font: "Inter Regular 16"
terminal-box: "terminal_*.png"

+ boot_menu {
    left = 29%
    top = 35%
    width = 42%
    height = 32%
    item_font = "Bebas Neue Regular 24"
    selected_item_font = "Bebas Neue Regular 24"
    item_color = "#C9C5C8"
    selected_item_color = "#FFFFFF"
    item_height = 44
    item_padding = 22
    item_spacing = 8
    icon_width = 0
    icon_height = 0
    item_icon_space = 0
    selected_item_pixmap_style = "select_*.png"
    scrollbar = false
}

+ label {
    left = 0
    top = 73%
    width = 100%
    align = "center"
    color = "#8A8A92"
    font = "Bebas Neue Regular 16"
    text = "UP / DOWN  CHOOSE     ENTER  START     E  EDIT     C  COMMAND LINE"
}

+ label {
    id = "__timeout__"
    left = 0
    top = 78%
    width = 100%
    align = "center"
    color = "#B9B5B8"
    font = "Bebas Neue Regular 18"
    text = "Starting Paragon PR7-OS in %d s"
}
"""


def write(root: Path, rel: str, content: str | bytes | QImage) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, QImage):
        fmt = None if path.suffix.lower() in (".png", ".jpg", ".jpeg") else "PNG"     # .face.icon is a PNG
        if not content.save(str(path), fmt):
            raise OSError(f"couldn't write {path}")
    elif isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def build(root: Path) -> list[Path]:
    """Every generated file into `root` (the image's filesystem). Returns what was written."""
    theme.load_fonts()
    theme.set_finish("obsidian")
    out: list[Path] = []
    share = "usr/share"
    for finish in ("obsidian", "aurora"):
        scheme = "ParagonObsidian" if finish == "obsidian" else "ParagonAurora"
        out.append(write(root, f"{share}/color-schemes/{scheme}.colors", colour_scheme(finish)))
        deco = f"{share}/aurorae/themes/Paragon-{finish.title()}"
        for name, content in aurorae(finish).items():
            out.append(write(root, f"{deco}/{name}", content))
        lnf = f"{share}/plasma/look-and-feel/org.paragon.pr7os.{finish}"
        for name, content in look_and_feel(finish).items():
            out.append(write(root, f"{lnf}/{name}", content))
    # the wallpaper: AURORA as the light picture, OBSIDIAN as the dark one (Plasma picks by the colour scheme)
    wp = f"{share}/wallpapers/Paragon"
    out.append(write(root, f"{wp}/metadata.json", '{\n  "KPlugin": {\n    "Id": "Paragon",\n    "Name": "Paragon",\n'
                     '    "Authors": [{"Name": "Paragon"}],\n    "License": "CC-BY-SA-4.0"\n  }\n}\n'))
    out.append(write(root, f"{wp}/contents/images/3840x2160.png", wallpaper(3840, 2160, "aurora")))
    out.append(write(root, f"{wp}/contents/images_dark/3840x2160.png", wallpaper(3840, 2160, "obsidian")))
    out.append(write(root, f"{wp}/contents/screenshot.png", wallpaper(800, 450, "obsidian")))
    # panel / launcher colours: dark in both finishes (the hook puts them into a copy of Breeze Dark)
    panel = colour_groups("obsidian")
    out.append(write(root, f"{share}/paragon/plasma-colors", ini(panel)))
    # the start button's 7, and the system's logo
    out.append(write(root, f"{share}/icons/hicolor/scalable/apps/pr7os-start.svg", start_icon_svg()))
    out.append(write(root, f"{share}/icons/hicolor/scalable/apps/pr7os.svg", start_icon_svg()))
    out.append(write(root, f"{share}/pixmaps/pr7os-mark.png", mark_image(1040, 200)))
    # the account picture (setup_look.py gives it to accounts that still have Debian's, and links /etc/skel's to it:
    # desktop-base owns /etc/skel/.face.icon, so the package can't ship that file itself)
    out.append(write(root, f"{share}/paragon/face.png", face_image(256)))
    # system defaults: OBSIDIAN (what a new account starts with)
    for cfg, groups in plasma_settings("obsidian").items():
        body = dict(groups)
        if cfg == "kdeglobals":
            body.update(colour_groups("obsidian"))
        out.append(write(root, f"etc/xdg/{cfg}", ini(body)))
    # login screen (SDDM): the QML is static, the art is drawn here
    sddm = f"{share}/sddm/themes/paragon"
    for f in ("Main.qml", "metadata.desktop", "theme.conf"):
        out.append(write(root, f"{sddm}/{f}", (STATIC / "sddm" / f).read_text(encoding="utf-8")))
    shot = wallpaper(1920, 1080, "obsidian", mark=False)
    out.append(write(root, f"{sddm}/background.png", shot))
    out.append(write(root, f"{sddm}/mark.png", mark_image(520, 100)))
    out.append(write(root, "etc/sddm.conf.d/10-paragon.conf",
                     "[General]\n# no on-screen keyboard over the password (Debian turns Qt's virtual keyboard on)\n"
                     "InputMethod=\n\n[Theme]\nCurrent=paragon\nCursorTheme=breeze_cursors\nFont=Bebas Neue\n"))
    # boot splash (Plymouth)
    ply = f"{share}/plymouth/themes/paragon"
    for f in ("paragon.plymouth", "paragon.script"):
        out.append(write(root, f"{ply}/{f}", (STATIC / "plymouth" / f).read_text(encoding="utf-8")))
    out.append(write(root, f"{ply}/mark.png", mark_image(520, 100)))
    out.append(write(root, f"{ply}/word.png", text_image("PARAGON", 22, "#E8E8EA", 320, 36, 8)))
    out.append(write(root, f"{ply}/footer.png", text_image(f"BASED ON {DEBIAN.upper()}", 12, "#5E5A60", 400, 24, 3,
                                                           True)))
    track, tp = new_image(320, 4); tp.setPen(Qt.PenStyle.NoPen); tp.setBrush(colour("#1C1C20"))
    tp.drawRoundedRect(QRectF(0, 0, 320, 4), 2, 2); tp.end()
    out.append(write(root, f"{ply}/track.png", track))
    fill, fp = new_image(320, 4); fp.fillRect(QRectF(0, 0, 320, 4), theme.family_gradient(0, 0, 320, 0)); fp.end()
    out.append(write(root, f"{ply}/fill.png", fill))
    # boot menu (GRUB): the installed system's, and the same art for the live ISO's menu
    grub = f"{share}/grub/themes/paragon"
    out.append(write(root, f"{grub}/theme.txt", grub_theme_txt()))
    out.append(write(root, f"{grub}/background.png", grub_background()))
    for piece in ("w", "c", "e"):
        out.append(write(root, f"{grub}/select_{piece}.png", grub_select(piece)))
    for piece in ("c", "n", "ne", "e", "se", "s", "sw", "w", "nw"):   # the command line's frame: onyx
        img, p = new_image(8, 8); p.fillRect(QRectF(0, 0, 8, 8), colour("#0C0A0D")); p.end()
        out.append(write(root, f"{grub}/terminal_{piece}.png", img))
    out.append(write(root, "etc/default/grub.d/paragon.cfg",
                     'GRUB_DISTRIBUTOR="Paragon PR7-OS"\nGRUB_THEME="/usr/share/grub/themes/paragon/theme.txt"\n'
                     'GRUB_GFXMODE="1920x1080,auto"\nGRUB_TIMEOUT=5\n'
                     'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash loglevel=3 plymouth.use-simpledrm"\n'))
    # what the look package does once installed (its postinst; dpkg triggers run it again on Plasma's updates)
    out.append(write(root, f"{share}/paragon/setup_look.py", (STATIC / "setup_look.py").read_text(encoding="utf-8")))
    # one finish for the whole desktop: the apps' OBSIDIAN / AURORA and Plasma's global theme kept together
    out.append(write(root, f"{share}/paragon/finish_sync.py", (STATIC / "finish_sync.py").read_text(encoding="utf-8")))
    out.append(write(root, "etc/xdg/autostart/pr7os-finish-sync.desktop",
                     "[Desktop Entry]\nType=Application\nName=Paragon finish\nComment=The Paragon apps' finish and "
                     "Plasma's global theme kept together\nExec=python3 /usr/share/paragon/finish_sync.py\n"
                     "NoDisplay=true\nOnlyShowIn=KDE;\nX-KDE-autostart-phase=2\n"))
    # the lock screen: Plasma's own (it also unlocks), restyled in the image by this script
    out.append(write(root, f"{share}/paragon/lockscreen.py", (STATIC / "lockscreen.py").read_text(encoding="utf-8")))
    out.append(write(root, f"{share}/paragon/lockscreen/ParagonClock.qml",
                     (STATIC / "lockscreen/ParagonClock.qml").read_text(encoding="utf-8")))
    # the boot menu's fonts are made in the image (grub-mkfont); this script names them in theme.txt
    out.append(write(root, f"{share}/paragon/grub-fonts.py", (STATIC / "grub-fonts.py").read_text(encoding="utf-8")))
    # the installer (Calamares): branding, slideshow, logo
    from . import __version__
    cal = "etc/calamares/branding/paragon"
    out.append(write(root, f"{cal}/branding.desc",
                     (STATIC / "calamares/branding.desc").read_text(encoding="utf-8").replace("@VERSION@", __version__)))
    out.append(write(root, f"{cal}/show.qml", (STATIC / "calamares/show.qml").read_text(encoding="utf-8")))
    # the installer's disk settings (an encrypted disk by default): applied to Debian's partition.conf by hook 0300
    out.append(write(root, "usr/share/paragon/calamares_partition.py",
                     (STATIC / "calamares/partition_settings.py").read_text(encoding="utf-8")))
    icon, ip = new_image(256, 256)
    ip.fillPath(seven_path(QRectF(40, 52, 176, 152)), theme.family_gradient(40, 0, 216, 0)); ip.end()
    out.append(write(root, f"{cal}/icon.png", icon))
    out.append(write(root, f"{cal}/logo.png", icon))
    out.append(write(root, f"{cal}/welcome.png", mark_image(1040, 200)))
    out.append(write(root, f"{share}/icons/hicolor/256x256/apps/pr7os.png", icon))
    # fonts, system-wide: Bebas Neue (everything) and Inter (the login password field, GRUB's command line); the
    # folder keeps its first name so updates replace files in place. GRUB's fonts are made from these by the hook
    for ttf in sorted((HERE / "fonts").glob("*.ttf")):
        out.append(write(root, f"{share}/fonts/truetype/paragon-inter/{ttf.name}", ttf.read_bytes()))
    # the boot splash's words come from the initramfs: its font and fontconfig are copied in (an encrypted disk's question)
    hook = write(root, "etc/initramfs-tools/hooks/paragon-plymouth-fonts",
                 (STATIC / "initramfs/paragon-plymouth-fonts").read_text(encoding="utf-8"))
    hook.chmod(0o755)
    out.append(hook)
    for lic in ("OFL-LICENSE.txt", "BebasNeue-OFL.txt"):
        if (HERE / "fonts" / lic).exists():
            out.append(write(root, f"{share}/fonts/truetype/paragon-inter/{lic}", (HERE / "fonts" / lic).read_bytes()))
    return out


def main(argv: list[str] | None = None) -> int:
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path(argv[0] if argv else "build/root")
    app = QApplication.instance() or QApplication([])  # noqa: F841 - fonts and painting need it
    files = build(root)
    print(f"{len(files)} files written under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
