"""The generated theme files: family colours only, complete formats, references that exist, a working login."""
import colorsys
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

HEX = re.compile(r"#([0-9A-Fa-f]{6})(?:[0-9A-Fa-f]{2})?\b|#([0-9A-Fa-f]{2})([0-9A-Fa-f]{6})\b")
RGB = re.compile(r"^\s*\w+=(\d{1,3}),(\d{1,3}),(\d{1,3})\s*$", re.M)


def family(r: int, g: int, b: int) -> bool:
    """The family rule: anything coloured has a hue between ~318 and ~42 degrees (pink, red, orange); greys and
    near-greys (low chroma) are pearl and onyx."""
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    chroma = (max(r, g, b) - min(r, g, b)) / 255
    if chroma < 0.12:
        return True
    deg = h * 360
    return deg >= 315 or deg <= 45


def colours_in(text: str):
    for m in HEX.finditer(text):
        if m.group(1):
            v = m.group(1)
        else:                       # QML's #AARRGGBB
            v = m.group(3)
        yield tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    for m in RGB.finditer(text):
        yield tuple(int(x) for x in m.groups())


def test_every_colour_is_the_familys(built):
    root, files = built
    checked = 0
    for f in files:
        if f.suffix in (".png", ".jpg", ".ttf", ".txt") and f.name != "theme.txt":
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        for c in colours_in(text):
            checked += 1
            assert family(*c), f"{f.relative_to(root)}: {c} is outside the family's colours"
    static = Path(__file__).resolve().parents[1] / "pr7os" / "static"
    for f in list(static.rglob("*.qml")) + list(static.rglob("*.script")):
        for c in colours_in(f.read_text(encoding="utf-8")):
            checked += 1
            assert family(*c), f"{f.name}: {c}"
    assert checked > 200


def test_the_wallpaper_and_the_boot_art_are_the_familys(built):
    from PySide6.QtGui import QImage
    root, _ = built
    for rel in ("usr/share/wallpapers/Paragon/contents/images_dark/3840x2160.png",
                "usr/share/wallpapers/Paragon/contents/images/3840x2160.png",
                "usr/share/grub/themes/paragon/background.png", "usr/share/sddm/themes/paragon/background.png",
                "usr/share/paragon/face.png"):
        img = QImage(str(root / rel))
        assert not img.isNull(), rel
        for y in range(0, img.height(), max(1, img.height() // 40)):
            for x in range(0, img.width(), max(1, img.width() // 40)):
                c = img.pixelColor(x, y)
                assert family(c.red(), c.green(), c.blue()), (rel, x, y, c.name())
    assert QImage(str(root / "usr/share/wallpapers/Paragon/contents/images/3840x2160.png")).size().width() == 3840


@pytest.mark.parametrize("scheme", ["ParagonObsidian", "ParagonAurora"])
def test_colour_schemes_fill_every_role(built, scheme):
    root, _ = built
    text = (root / f"usr/share/color-schemes/{scheme}.colors").read_text()
    for role in ("Window", "View", "Button", "Header", "Tooltip", "Complementary", "Selection"):
        group = re.search(rf"^\[Colors:{role}\]\n((?:\w+=.*\n)+)", text, re.M)
        assert group, role
        keys = dict(line.split("=", 1) for line in group.group(1).strip().splitlines())
        assert set(keys) >= {"BackgroundNormal", "BackgroundAlternate", "ForegroundNormal", "ForegroundInactive",
                             "ForegroundActive", "ForegroundLink", "ForegroundVisited", "ForegroundNegative",
                             "ForegroundNeutral", "ForegroundPositive", "DecorationFocus", "DecorationHover"}, role
    assert "[WM]" in text and f"ColorScheme={scheme}" in text
    # keys and tooltips stay dark in both finishes (the family's piano-black keys)
    button = re.search(r"^\[Colors:Button\]\n(?:.*\n)*?BackgroundNormal=(.*)$", text, re.M).group(1)
    assert sum(int(x) for x in button.split(",")) < 150


@pytest.mark.parametrize("finish", ["Obsidian", "Aurora"])
def test_the_window_decoration(built, finish):
    root, _ = built
    d = root / f"usr/share/aurorae/themes/Paragon-{finish}"
    ids = {e.get("id") for e in ET.parse(d / "decoration.svg").iter() if e.get("id")}
    for prefix in ("decoration", "decoration-inactive"):
        for piece in ("topleft", "top", "topright", "left", "center", "right", "bottomleft", "bottom", "bottomright"):
            assert f"{prefix}-{piece}" in ids
    for button in ("close", "minimize", "maximize", "restore"):
        ids = {e.get("id") for e in ET.parse(d / f"{button}.svg").iter() if e.get("id")}
        assert {"active-center", "hover-center", "pressed-center", "inactive-center"} <= ids, button
    assert "url(#fam)" in (d / "close.svg").read_text()                 # the gradient close key
    rc = (d / f"Paragon-{finish}rc").read_text()
    assert "TitleAlignment=Center" in rc and "ButtonHeight=22" in rc
    assert f"X-KDE-PluginInfo-Name=Paragon-{finish}" in (d / "metadata.desktop").read_text()


@pytest.mark.parametrize("finish", ["obsidian", "aurora"])
def test_global_themes(built, finish):
    root, _ = built
    d = root / f"usr/share/plasma/look-and-feel/org.paragon.pr7os.{finish}"
    meta = json.loads((d / "metadata.json").read_text())
    assert meta["KPlugin"]["Id"] == f"org.paragon.pr7os.{finish}"
    assert meta["KPackageStructure"] == "Plasma/LookAndFeel"
    defaults = (d / "contents/defaults").read_text()
    assert f"theme=__aurorae__svg__Paragon-{finish.title()}" in defaults
    assert f"ColorScheme=Paragon{finish.title()}" in defaults and "font=Inter," in defaults
    layout = (d / "contents/layouts/org.kde.plasma.desktop-layout.js").read_text()
    assert "org.kde.plasma.kickoff" in layout and "pr7os-start" in layout and "panel.floating = true" in layout
    assert layout.count("{") == layout.count("}") and layout.count("(") == layout.count(")")
    assert (d / "contents/splash/Splash.qml").exists() and (d / "contents/splash/images/mark.png").exists()
    assert (d / "contents/previews/preview.png").exists()
    json.loads((root / "usr/share/wallpapers/Paragon/metadata.json").read_text())


def test_system_defaults_are_obsidian(built):
    root, _ = built
    kdeglobals = (root / "etc/xdg/kdeglobals").read_text()
    assert "LookAndFeelPackage=org.paragon.pr7os.obsidian" in kdeglobals and "[Colors:Window]" in kdeglobals
    assert "theme=__aurorae__svg__Paragon-Obsidian" in (root / "etc/xdg/kwinrc").read_text()
    assert "name=paragon" in (root / "etc/xdg/plasmarc").read_text()
    assert "[Colors:Complementary]" in (root / "usr/share/paragon/plasma-colors").read_text()


def test_boot_menu_and_splash_find_their_files(built):
    root, _ = built
    grub = root / "usr/share/grub/themes/paragon"
    theme_txt = (grub / "theme.txt").read_text()
    for name in re.findall(r'"([\w*]+\.png)"', theme_txt):
        if "*" in name:
            assert list(grub.glob(name)), name
        else:
            assert (grub / name).exists(), name
    assert "__timeout__" in theme_txt
    assert 'GRUB_THEME="/usr/share/grub/themes/paragon/theme.txt"' in (root / "etc/default/grub.d/paragon.cfg").read_text()
    ply = root / "usr/share/plymouth/themes/paragon"
    script = (ply / "paragon.script").read_text()
    for name in re.findall(r'Image\("([\w.]+\.png)"\)', script):
        assert (ply / name).exists(), name
    assert "ModuleName=script" in (ply / "paragon.plymouth").read_text()
    assert script.count("{") == script.count("}")


def test_start_icon_is_an_svg(built):
    root, _ = built
    tree = ET.parse(root / "usr/share/icons/hicolor/scalable/apps/pr7os-start.svg")
    assert tree.getroot().tag.endswith("svg")


def test_the_login_screen_logs_in(built, qapp):
    """The real Main.qml, with stand-ins for SDDM: typing a password and Enter asks SDDM to log the account in."""
    import login_preview
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    root, _ = built
    view, sddm, img = login_preview.render(root)
    assert img.width() == 1920

    def type_text(text):              # QTest.keyClicks takes widgets only; a QQuickView is a window
        for ch in text:
            QTest.keyClick(view, ch)
    type_text("s3cret pass")
    QTest.keyClick(view, Qt.Key.Key_Return)
    assert sddm.calls == [("login", "ari", "s3cret pass", 0)]
    # a wrong password: SDDM says so, and the field empties for the next try
    sddm.loginFailed.emit()
    for _ in range(5):
        qapp.processEvents()
    QTest.keyClick(view, Qt.Key.Key_Return)
    assert sddm.calls[-1] == ("login", "ari", "", 0)
    # the session: a click goes to the next one, and the next login uses it
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(190, 1024))
    for _ in range(5):
        qapp.processEvents()
    type_text("again")
    QTest.keyClick(view, Qt.Key.Key_Return)
    assert sddm.calls[-1] == ("login", "ari", "again", 1)
    # power keys
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(1796, 1022))
    assert sddm.calls[-1] == ("powerOff",)
    view.close()


def test_login_has_no_onscreen_keyboard_and_the_panel_pins_a_list(built):
    """The first boot test: Debian's SDDM put Qt's virtual keyboard over the password, and one comma-joined string
    of launchers gave the panel a single unknown icon."""
    root, _ = built
    conf = (root / "etc/sddm.conf.d/10-paragon.conf").read_text()
    assert "[General]" in conf and "\nInputMethod=\n" in conf
    layout = (root / "usr/share/plasma/look-and-feel/org.paragon.pr7os.obsidian/contents/layouts/"
                     "org.kde.plasma.desktop-layout.js").read_text()
    assert 'writeConfig("launchers", ["applications:pr7-e.desktop", ' in layout


def test_the_lock_screen_has_the_paragon_wallpaper(built):
    root, _ = built
    conf = (root / "etc/xdg/kscreenlockerrc").read_text()
    assert "[Greeter]\nWallpaperPlugin=org.kde.image" in conf
    assert "[Greeter][Wallpaper][org.kde.image][General]\nImage=file:///usr/share/wallpapers/Paragon/" in conf
