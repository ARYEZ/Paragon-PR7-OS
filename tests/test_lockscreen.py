"""The lock screen's restyling (pr7os/static/lockscreen.py) against Plasma 6.3.6's own files, as Debian 13 installs
them: every edit applies, Plasma's unlock logic is untouched, and a file it doesn't recognise changes nothing."""
import importlib.util
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests/data/plasma-6.3.6"
SHELL = "usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen"
DELEGATE = "usr/lib/x86_64-linux-gnu/qt6/qml/org/kde/breeze/components/UserDelegate.qml"


def load():
    spec = importlib.util.spec_from_file_location("lockscreen", ROOT / "pr7os/static/lockscreen.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def system(tmp_path):
    root = tmp_path / "root"
    shutil.copytree(DATA, root)
    return root


def logic(text: str) -> list[str]:
    """What unlocks: every line that talks to the authenticator, quits, or handles the password's events."""
    keys = ("authenticator", "Qt.quit", "onAccepted", "startLogin", "onClicked", "onClearPassword", "respond(")
    return [line for line in text.splitlines() if any(k in line for k in keys)]


def test_every_edit_applies_and_the_unlocking_stays_plasmas(system):
    before = {p: (system / p).read_text() for p in (f"{SHELL}/LockScreenUi.qml", f"{SHELL}/MainBlock.qml", DELEGATE)}
    load().main([str(system)])
    ui = (system / f"{SHELL}/LockScreenUi.qml").read_text()
    block = (system / f"{SHELL}/MainBlock.qml").read_text()
    delegate = (system / DELEGATE).read_text()
    assert "        ParagonClock {\n            id: clock\n" in ui and "        Clock {" not in ui
    assert (system / f"{SHELL}/ParagonClock.qml").exists()
    assert block.count('"#FF0743"') == 2 and "implicitHeight: 48" in block and 'icon.color: "#FFFFFF"' in block
    assert "the family gradient ring around the picture" in delegate
    for rel, old in before.items():
        new = (system / rel).read_text()
        assert logic(new) == logic(old), rel                         # the unlocking, line for line
        assert new.count("{") == new.count("}") and new.count("(") == new.count(")"), rel
        assert len(new) > len(old)


def test_a_plasma_it_doesnt_recognise_changes_nothing(system):
    block = system / f"{SHELL}/MainBlock.qml"
    block.write_text(block.read_text().replace("            id: loginButton\n", "            id: unlockKey\n"))
    ui_before = (system / f"{SHELL}/LockScreenUi.qml").read_text()
    with pytest.raises(SystemExit):
        load().main([str(system)])
    assert (system / f"{SHELL}/LockScreenUi.qml").read_text() == ui_before   # checked first, nothing written
    assert not (system / f"{SHELL}/ParagonClock.qml").exists()


def test_the_image_gets_the_script_and_the_clock(built):
    root, _ = built
    assert (root / "usr/share/paragon/lockscreen.py").exists()
    assert (root / "usr/share/paragon/lockscreen/ParagonClock.qml").exists()
    assert "loglevel=3" in (root / "etc/default/grub.d/paragon.cfg").read_text()
    hook = (ROOT / "live/config/hooks/normal/0200-paragon-look.hook.chroot").read_text()
    assert "python3 /usr/share/paragon/lockscreen.py" in hook
    assert "loglevel=3" in (ROOT / "live/auto/config").read_text()
