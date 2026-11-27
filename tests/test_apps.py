"""The apps in the image: staged with launcher, menu entry and icon, and every one of them starts on Linux."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from pr7os import apps, assets

FAMILY = Path(os.environ.get("PR7OS_FAMILY", Path(__file__).resolve().parents[2]))
have_family = all((FAMILY / a.repo / a.package).is_dir() for a in apps.APPS)
needs_family = pytest.mark.skipif(not have_family, reason="the app repositories aren't checked out next to this one")


@pytest.fixture(scope="module")
def staged(tmp_path_factory):
    root = tmp_path_factory.mktemp("root")
    apps.stage(FAMILY, root)
    return root


@needs_family
def test_every_app_has_code_launcher_entry_and_icon(staged):
    for app in apps.APPS:
        assert (staged / "opt/paragon/apps" / app.repo / app.package / "__main__.py").exists(), app.letter
        assert not list((staged / "opt/paragon/apps" / app.repo).rglob("__pycache__")), app.letter
        exe = staged / "usr/bin" / app.command
        assert os.access(exe, os.X_OK) and f"-m {app.package}" in exe.read_text()
        entry = (staged / "usr/share/applications" / f"{app.command}.desktop").read_text()
        main = entry.split("\n\n")[0]                    # the [Desktop Entry] section (actions follow)
        keys = dict(line.split("=", 1) for line in main.splitlines()[1:])
        assert keys["Type"] == "Application" and keys["Exec"].split()[0] == app.command
        assert keys["Icon"] == f"paragon-pr7-{app.key}" and keys["Categories"].endswith(";")
        assert (staged / f"usr/share/icons/hicolor/256x256/apps/paragon-pr7-{app.key}.png").exists()


@needs_family
def test_the_family_opens_the_files(staged):
    mime = (staged / "etc/xdg/mimeapps.list").read_text()
    for m, cmd in (("inode/directory", "pr7-e"), ("image/jpeg", "pr7-p"), ("application/pdf", "pr7-r"),
                   ("video/mp4", "pr7-m"), ("text/plain", "pr7-w"), ("application/zip", "pr7-z")):
        assert f"\n{m}={cmd}.desktop\n" in mime, m


@needs_family
def test_requirements_are_merged_without_windows_ones(staged):
    req = (staged / "opt/paragon/requirements.txt").read_text().splitlines()
    names = {r.split(">=")[0].lower() for r in req}
    assert {"pyside6", "pyqt6", "pyqt6-qscintilla", "paramiko", "keyring", "pyte", "psutil", "pykeepass",
            "mutagen", "pillow"} <= names
    assert "pywinpty" not in names
    assert "PySide6>=6.9" in req                     # the strictest bound (PR7-M's)


def test_the_panel_pins_staged_apps():
    commands = {a.command for a in apps.APPS}
    assert set(assets.LAYOUT_APPS) <= commands


@needs_family
def test_every_app_starts_on_linux(staged):
    """Each launcher's command, started for real (offscreen, a throwaway home): still running after a few seconds."""
    home = Path(tempfile.mkdtemp(prefix="pr7os-home-"))
    env = dict(os.environ, HOME=str(home), QT_QPA_PLATFORM="offscreen", XDG_CONFIG_HOME=str(home / ".config"),
               XDG_DATA_HOME=str(home / ".local/share"), XDG_RUNTIME_DIR=str(home / "run"),
               PYTHON_KEYRING_BACKEND="keyring.backends.null.Keyring")
    (home / "run").mkdir(mode=0o700)
    procs = {}
    for app in apps.APPS:
        e = dict(env, PYTHONPATH=str(staged / "opt/paragon/apps" / app.repo))
        procs[app.letter] = subprocess.Popen([sys.executable, "-m", app.package], env=e, cwd=home,
                                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(12)
    dead = {}
    for letter, p in procs.items():
        if p.poll() is not None:
            dead[letter] = p.stdout.read().decode(errors="replace")[-800:]
        else:
            p.kill()
        p.wait()
    assert not dead, "\n\n".join(f"PR7-{k} stopped:\n{v}" for k, v in dead.items())


def test_pr7q_owns_print_through_plasma_and_starts_at_sign_in(tmp_path):
    """Plasma registers the X-KDE-Shortcuts of menu entries in /usr/share/kglobalaccel (Spectacle's way to own Print);
    each runs `pr7-q --region` etc., which hands the capture to the running PR7-Q."""
    q = next(a for a in apps.APPS if a.letter == "Q")
    assert "Q" not in apps.LEFT_OUT
    entry = apps.desktop_entry(q)
    sections = {}
    for block in entry.strip().split("\n\n"):
        lines = block.splitlines()
        sections[lines[0]] = dict(l.split("=", 1) for l in lines[1:])
    assert sections["[Desktop Entry]"]["Actions"] == "region;lastregion;window;full;"
    assert sections["[Desktop Action region]"] == {"Name": "Capture region", "Exec": "pr7-q --region",
                                                   "X-KDE-Shortcuts": "Print"}
    assert sections["[Desktop Action full]"]["X-KDE-Shortcuts"] == "Ctrl+Print"
    assert "Exec=pr7-q --tray" in apps.autostart_entry(q)
    from pr7os import packages
    assert packages.is_app_file("usr/share/kglobalaccel/pr7-q.desktop")
    assert packages.is_app_file("etc/xdg/autostart/paragon-pr7-q.desktop")


def test_ci_downloads_every_app():
    """CI clones the app repositories from build.yml's APPS list: 0.2.3's first build had no PR7-Q (q missing)."""
    import re as _re
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/build.yml").read_text()
    listed = set(_re.search(r'^  APPS: "([^"]+)"', workflow, _re.M).group(1).split())
    assert listed == {a.key for a in apps.APPS}


def test_the_apps_get_bebas_neue_for_inter(tmp_path):
    """The apps ask for Inter (their own theme); on PR7-OS their launcher's font configuration hides Inter and answers
    with Bebas Neue, the owner's font; monospaced text stays monospaced. Checked in a real Qt process, with a copy of
    PR7-OS's configuration that also sees this repository's fonts (Inter included, as a system copy would be)."""
    fonts = Path(apps.__file__).resolve().parent / "fonts"
    conf = tmp_path / "fonts-apps.conf"
    conf.write_text(apps.FONTS_APPS.replace("</fontconfig>", f"  <dir>{fonts}</dir>\n  <cachedir>{tmp_path / 'cache'}</cachedir>\n</fontconfig>"))
    probe = ("import os; os.environ['QT_QPA_PLATFORM']='offscreen'\n"
             "from PySide6.QtGui import QFont, QFontInfo\nfrom PySide6.QtWidgets import QApplication, QLabel\n"
             "app = QApplication([]); lab = QLabel('x'); lab.setStyleSheet('font-family: Inter;'); lab.ensurePolished()\n"
             "print(QFontInfo(QFont('Inter')).family(), QFontInfo(lab.font()).family(), "
             "QFontInfo(QFont('DejaVu Sans Mono')).fixedPitch(), sep='|')")
    out = subprocess.run([sys.executable, "-c", probe], env=dict(os.environ, FONTCONFIG_FILE=str(conf)),
                         capture_output=True, text=True, timeout=60).stdout.strip().splitlines()[-1]
    assert out == "Bebas Neue|Bebas Neue|True"
    assert "FONTCONFIG_FILE=/etc/paragon/fonts-apps.conf" in apps.launcher(apps.APPS[0])
