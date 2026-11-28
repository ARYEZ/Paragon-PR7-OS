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
    w.nm = lambda args, **k: subprocess.CompletedProcess(args, 0, "", "")   # no network to change
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
    ss = tmp_path / "ss"
    ss.write_text('#!/bin/sh\necho \'LISTEN 0 2 *:3389 *:* users:(("xrdp",pid=900,fd=11))\'\n')
    ss.chmod(0o755)
    env = dict(os.environ, PR7OS_APT=str(tmp_path / "apt-get"), PR7OS_SYSTEMCTL=str(tmp_path / "systemctl"),
               PR7OS_SS=str(ss))
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


class FakeNM:
    """nmcli as it answers for one Wi-Fi network set up by this account (the password in its wallet)."""
    def __init__(self, perms="user:aryez", flags="1 (agent-owned)", psk="secret pass"):
        self.calls, self.perms, self.flags, self.psk = [], perms, flags, psk

    def __call__(self, args, **k):
        self.calls.append(args)
        a = [x for x in args[1:] if x != "-s"]                       # -s (show secrets) only reads the password
        out = ""
        if a[:2] == ["-t", "-f"]:
            out = "u-1:802-11-wireless:Home\\:5G\nu-2:loopback:lo\n"
        elif a[:2] == ["-g", "connection.permissions"]:
            out = self.perms
        elif a[:2] == ["-g", "802-11-wireless-security.psk-flags"]:
            out = self.flags
        elif a[:2] == ["-g", "802-11-wireless-security.psk"]:
            out = self.psk
        return subprocess.CompletedProcess(args, 0, out + "\n", "")


def test_turn_on_makes_the_network_the_pcs(welcome, monkeypatch):
    mod, w, tmp = welcome
    nm = FakeNM()
    said = mod.network_for_everyone(nm)
    assert ["nmcli", "-s", "-g", "802-11-wireless-security.psk", "connection", "show", "u-1"] in nm.calls
    assert ["nmcli", "connection", "modify", "u-1", "connection.permissions", "",
            "802-11-wireless-security.psk-flags", "0", "802-11-wireless-security.psk", "secret pass"] in nm.calls
    assert said == "Home:5G: now the PC's, not only your account's"
    already = FakeNM(perms="", flags="0 (none)")
    assert mod.network_for_everyone(already) == ""                   # already the PC's: nothing changed
    assert not any(c[1:3] == ["connection", "modify"] for c in already.calls)
    monkeypatch.setattr(mod, "krdp_units", lambda: [])
    w.nm = FakeNM()
    w.remote_key.click()                                             # TURN ON does it, and says so
    assert w.remote == "on" and "Network: Home:5G: now the PC's" in w.remote_text.text()


def test_the_remote_helper_says_when_krdp_holds_the_port(tmp_path):
    """After a restart KRdp, started with the desktop, held 3389 and xrdp failed: TURN ON says so, by name."""
    for name in ("apt-get", "systemctl"):
        tool = tmp_path / name
        tool.write_text("#!/bin/sh\nexit 0\n")
        tool.chmod(0o755)
    ss = tmp_path / "ss"
    ss.write_text('#!/bin/sh\necho \'LISTEN 0 2 *:3389 *:* users:(("krdpserver",pid=1327,fd=9))\'\n')
    ss.chmod(0o755)
    env = dict(os.environ, PR7OS_APT=str(tmp_path / "apt-get"), PR7OS_SYSTEMCTL=str(tmp_path / "systemctl"),
               PR7OS_SS=str(ss))
    on = subprocess.run([sys.executable, str(WELCOME / "pr7os-remote-helper"), "on"], env=env, capture_output=True,
                        text=True)
    assert on.returncode == 1 and "held by krdpserver" in on.stdout.splitlines()[-1]


def test_turn_on_removes_krdps_autostart_entries(welcome, monkeypatch):
    mod, w, tmp = welcome
    auto = tmp / "config/autostart"
    auto.mkdir(parents=True)
    (auto / "org.kde.krdpserver.desktop").write_text("[Desktop Entry]\n")
    (auto / "other.desktop").write_text("[Desktop Entry]\n")
    cmds = mod.krdp_off_commands([])
    assert ["rm", "-f", str(auto / "org.kde.krdpserver.desktop")] in cmds
    assert not any("other.desktop" in " ".join(c) for c in cmds)


def test_big_picture_at_sign_in(welcome):
    mod, w, tmp = welcome
    entry = tmp / "config/autostart/paragon-steam-bigpicture.desktop"
    assert not w.bigpicture.isChecked() and not entry.exists()
    w.bigpicture.setChecked(True)
    assert "Exec=pr7os-steam --if-installed -bigpicture" in entry.read_text()
    w.bigpicture.setChecked(False)
    assert not entry.exists()


def test_pr7os_steam_if_installed(tmp_path):
    """Big Picture at sign-in does nothing when Steam isn't installed (no Discover at every sign-in)."""
    log = tmp_path / "log"
    for name, body in (("flatpak", f'echo "flatpak $*" >> "{log}"; [ "$1" = info ] && exit 1; exit 0'),
                       ("xdg-open", f'echo "xdg-open $*" >> "{log}"')):
        f = tmp_path / name
        f.write_text("#!/bin/sh\n" + body + "\n")
        f.chmod(0o755)
    env = dict(os.environ, PATH=f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    script = str(Path(__file__).resolve().parents[1] / "pr7os/static/system/pr7os-steam")
    log.write_text("")
    assert subprocess.run(["sh", script, "--if-installed", "-bigpicture"], env=env).returncode == 0
    assert "xdg-open" not in log.read_text()
    subprocess.run(["sh", script], env=env)
    assert "xdg-open appstream://com.valvesoftware.Steam" in log.read_text()


def test_the_remote_account(tmp_path):
    """The real helper with useradd / chpasswd stand-ins: <you>-remote made once, its password from stdin only."""
    import pwd
    log = tmp_path / "log"
    for name, body in (("useradd", f'echo "useradd $*" >> "{log}"'),
                       ("chpasswd", f'echo "chpasswd $(cat)" >> "{log}"')):
        f = tmp_path / name
        f.write_text("#!/bin/sh\n" + body + "\n")
        f.chmod(0o755)
    me = pwd.getpwuid(os.getuid()).pw_name
    env = dict(os.environ, PATH=f"{tmp_path}{os.pathsep}{os.environ['PATH']}", PR7OS_APT="apt-get",
               PKEXEC_UID=str(os.getuid()))
    helper = str(WELCOME / "pr7os-remote-helper")
    done = subprocess.run([sys.executable, helper, "account"], env=env, input="s3cret pw\n", capture_output=True,
                          text=True)
    assert done.returncode == 0 and done.stdout.splitlines()[-1] == f"DONE account {me}-remote"
    calls = log.read_text()
    assert f"--comment Remote desktop ({me}) {me}-remote" in calls
    assert f"chpasswd {me}-remote:s3cret pw" in calls
    assert "s3cret" not in " ".join(done.args)                      # never on a command line
    short = subprocess.run([sys.executable, helper, "account"], env=env, input="x\n", capture_output=True, text=True)
    assert short.returncode == 1
    nobody = subprocess.run([sys.executable, helper, "account"], env={**env, "PKEXEC_UID": ""}, input="s3cret pw\n",
                            capture_output=True, text=True)
    assert nobody.returncode == 1                                    # who asked must be known


def test_remote_account_key(welcome, monkeypatch):
    mod, w, tmp = welcome
    answers = iter(["pw1", "pw2"])
    w.ask_password = lambda prompt: next(answers)
    w.account_key.click()
    assert "weren't the same" in w.remote_text.text()
    answers = iter(["s3cret pw", "s3cret pw"])
    w.ask_password = lambda prompt: next(answers)
    sent = []
    monkeypatch.setattr(w, "_run", lambda cmd, var, word, text, done, stdin="": sent.append((word, stdin)))
    w.account_key.click()
    assert sent == [("account", "s3cret pw\n")]
