"""Paragon Welcome (static/welcome): the finish, the commands its keys start (recorded, not run), SSH through a
stand-in helper, "Show at sign-in"; and the real SSH helper with stand-in apt-get / systemctl."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

WELCOME = Path(__file__).resolve().parents[1] / "pr7os/static/welcome"


@pytest.fixture
def welcome(tmp_path, monkeypatch, qapp):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.delenv("PARAGON_FAMILY_FILE", raising=False)
    state = tmp_path / "ssh-state"
    state.write_text("off")
    helper = tmp_path / "ssh-helper"
    helper.write_text(f'#!/bin/sh\nif [ "$1" = state ]; then cat "{state}"; exit 0; fi\n'
                      f'echo "STEP Starting it"\necho "$1" > "{state}"\necho "DONE $1"\n')
    helper.chmod(0o755)
    monkeypatch.setenv("PR7OS_SSH_HELPER", str(helper))
    rstate = tmp_path / "remote-state"
    rstate.write_text("off")
    rhelper = tmp_path / "remote-helper"
    rhelper.write_text(f'#!/bin/sh\nif [ "$1" = state ]; then cat "{rstate}"; exit 0; fi\n'
                       f'echo "STEP Starting it"\necho "$1" > "{rstate}"\necho "DONE $1"\n')
    rhelper.chmod(0o755)
    monkeypatch.setenv("PR7OS_REMOTE_HELPER", str(rhelper))
    spec = importlib.util.spec_from_file_location("welcome", WELCOME / "welcome.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    w = mod.Window(sync=True)
    w.start = lambda command: w.started.append(command)        # recorded, never started
    w.configured = []
    w.configure = lambda args: w.configured.append(args)         # recorded, never run
    yield mod, w, tmp_path
    w.close()


def test_choosing_a_finish_is_the_familys_choice(welcome):
    mod, w, tmp = welcome
    assert w.finish_keys["obsidian"].isChecked()                 # nothing chosen yet: OBSIDIAN, PR7-OS's default
    w.finish_keys["aurora"].click()
    assert (tmp / "config/paragon/family-finish").read_text() == "aurora"      # every app (and finish_sync) follows
    assert w.finish_keys["aurora"].isChecked() and not w.finish_keys["obsidian"].isChecked()


def test_the_keys_start_what_they_say(welcome):
    mod, w, tmp = welcome
    from PySide6.QtWidgets import QPushButton
    keys = {b.text(): b for b in w.findChildren(QPushButton)}
    for text in ("ADD A PRINTER", "GET STEAM", "BACK UP TO A DRIVE", "CHECK FOR UPDATES"):
        keys[text].click()
    assert w.started == [["systemsettings", "kcm_printer_manager"], ["pr7os-steam"],
                         ["pr7-bk", "--new-home-backup"], ["pr7os-update"]]


def test_ssh_on_and_off(welcome):
    mod, w, tmp = welcome
    assert w.ssh == "off" and w.ssh_key.text() == "TURN ON"
    w.ssh_key.click()
    assert (tmp / "ssh-state").read_text().strip() == "on" and w.ssh == "on"
    assert w.ssh_key.text() == "TURN OFF" and ".local" in w.ssh_text.text()
    w.ssh_key.click()
    assert w.ssh == "off" and w.ssh_key.text() == "TURN ON"


def test_show_at_sign_in(welcome):
    mod, w, tmp = welcome
    assert w.at_sign_in.isChecked()
    w.at_sign_in.setChecked(False)
    assert mod.main(["--first-run"]) == 0                        # switched off: the autostart opens nothing


def test_the_ssh_helper(tmp_path):
    """The real helper, with apt-get / systemctl stand-ins: installs openssh-server when it's missing, starts it."""
    log = tmp_path / "calls"
    for name in ("apt-get", "systemctl"):
        t = tmp_path / name
        t.write_text(f'#!/bin/sh\necho "{name} $*" >> "{log}"\n[ "$1" = is-active ] && echo inactive\nexit 0\n')
        t.chmod(0o755)
    env = dict(os.environ, PR7OS_APT=str(tmp_path / "apt-get"), PR7OS_SYSTEMCTL=str(tmp_path / "systemctl"))
    helper = str(WELCOME / "pr7os-ssh-helper")
    on = subprocess.run([sys.executable, helper, "on"], env=env, capture_output=True, text=True)
    assert on.returncode == 0 and on.stdout.splitlines()[-1] == "DONE on"
    calls = log.read_text()
    if "openssh-server" not in subprocess.run(["dpkg-query", "-W", "openssh-server"], capture_output=True, text=True).stdout:
        assert "install -y openssh-server" in calls
    assert "systemctl enable --now ssh" in calls
    assert subprocess.run([sys.executable, helper, "off"], env=env, capture_output=True, text=True).returncode == 0
    assert "systemctl disable --now ssh" in log.read_text()
    bad = subprocess.run([sys.executable, helper, "on", "--evil"], env=env, capture_output=True, text=True)
    assert bad.returncode == 2                                    # one word only


def test_the_font_switch(welcome):
    """FONT: your choice saved for the apps' launchers, and Plasma's own font keys written (System Settings > Fonts
    writes the same) - recorded here, never run."""
    mod, w, tmp = welcome
    assert w.font_keys["bebas"].isChecked()                       # PR7-OS's font until you choose
    written = []
    w.configure = lambda args: written.append(args)
    w.font_keys["inter"].click()
    assert (tmp / "config/paragon/font").read_text() == "inter" and w.font_keys["inter"].isChecked()
    keys = {(a[4], a[6]): a[7] for a in written}
    assert keys[("General", "font")].startswith("Inter,10,") and keys[("WM", "activeFont")].startswith("Inter,10,")
    assert keys[("General", "smallestReadableFont")].startswith("Inter,8,")
    assert "Inter" in w.styleSheet() and "sign out" in w.font_text.text().lower()
    written.clear()
    w.font_keys["bebas"].click()
    assert all(a[7].startswith("Bebas Neue,") for a in written) and len(written) == 5


def test_the_launcher_follows_the_font_choice(tmp_path):
    """The apps' launcher (run for real by sh): Bebas Neue's font configuration unless your choice says inter."""
    import subprocess
    from pr7os import apps
    script = tmp_path / "pr7-e"
    text = apps.launcher(apps.APPS[0]).replace('exec /opt/paragon/venv/bin/python -m pr7e "$@"',
                                               'echo "FONTCONFIG=${FONTCONFIG_FILE:-none}"')
    script.write_text(text)
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "XDG_CONFIG_HOME": str(tmp_path / "cfg")}
    run = lambda: subprocess.run(["sh", str(script)], env=env, capture_output=True, text=True).stdout.strip()
    assert run() == "FONTCONFIG=/etc/paragon/fonts-apps.conf"      # nothing chosen: Bebas Neue
    (tmp_path / "cfg/paragon").mkdir(parents=True)
    (tmp_path / "cfg/paragon/font").write_text("inter\n")
    assert run() == "FONTCONFIG=none"                               # Inter: the system's Inter answers them
    (tmp_path / "cfg/paragon/font").write_text("bebas")
    assert run() == "FONTCONFIG=/etc/paragon/fonts-apps.conf"


def test_press_clicks_a_key_like_a_mouse(welcome):
    mod, w, tmp = welcome
    assert mod.press(w, "GET STEAM") and w.started[-1] == ["pr7os-steam"]
    assert not mod.press(w, "NO SUCH KEY")


def test_remote_desktop_on_and_off(welcome, monkeypatch):
    """TURN ON: KRdp stopped for this account first (it holds port 3389), then xrdp through the helper; the card says
    where to connect and to sign out here first."""
    mod, w, tmp = welcome
    monkeypatch.setattr(mod, "krdp_units", lambda: ["plasma-krdp_server.service"])
    assert w.remote == "off" and w.remote_key.text() == "TURN ON"
    w.remote_key.click()
    assert (tmp / "remote-state").read_text().strip() == "on" and w.remote == "on"
    assert w.configured[0] == ["systemctl", "--user", "disable", "--now", "plasma-krdp_server.service"]
    assert w.configured[1][:2] == ["pkill", "-u"] and w.configured[1][-1] == "krdpserver"
    assert w.remote_key.text() == "TURN OFF" and "Sign out here first" in w.remote_text.text()
    w.configured.clear()
    w.remote_key.click()
    assert w.remote == "off" and w.remote_key.text() == "TURN ON" and w.configured == []   # turning off leaves KRdp be
    on = mod.remote_view(True, "outpost", "10.0.0.17")
    assert "computer 10.0.0.17" in on
    assert "computer outpost.local" in mod.remote_view(True, "outpost", "127.0.0.1")      # offline: the name


def test_the_remote_helper(tmp_path):
    """The real helper with apt-get / systemctl stand-ins: xrdp started and enabled; one word only."""
    log = tmp_path / "calls"
    for name in ("apt-get", "systemctl"):
        tool = tmp_path / name
        tool.write_text(f'#!/bin/sh\necho "{name} $*" >> "{log}"\n[ "$1" = is-active ] && echo inactive\nexit 0\n')
        tool.chmod(0o755)
    env = dict(os.environ, PR7OS_APT=str(tmp_path / "apt-get"), PR7OS_SYSTEMCTL=str(tmp_path / "systemctl"))
    helper = str(WELCOME / "pr7os-remote-helper")
    on = subprocess.run([sys.executable, helper, "on"], env=env, capture_output=True, text=True)
    assert on.returncode == 0 and on.stdout.splitlines()[-1] == "DONE on"
    assert "systemctl enable --now xrdp" in log.read_text()
    assert subprocess.run([sys.executable, helper, "off"], env=env, capture_output=True, text=True).returncode == 0
    assert "systemctl disable --now xrdp" in log.read_text()
    assert subprocess.run([sys.executable, helper, "on", "--x"], env=env, capture_output=True, text=True).returncode == 2


def test_press_picks_the_key_on_its_card(welcome):
    mod, w, tmp = welcome
    assert mod.press(w, "REMOTE DESKTOP/TURN ON") and w.remote == "on" and w.ssh == "off"
    assert mod.press(w, "SSH/TURN ON") and w.ssh == "on"
    assert not mod.press(w, "PRINTERS/TURN ON")
