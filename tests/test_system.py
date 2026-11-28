"""The system package's setup (firewall once, Flathub) and the look's account picture, run for real against a
stand-in root with stand-in ufw / flatpak commands that record what they were asked."""
import importlib.util
import os
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "pr7os/static"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def system(tmp_path, monkeypatch):
    root = tmp_path / "root"
    (root / "etc/ufw").mkdir(parents=True)
    (root / "etc/ufw/ufw.conf").write_text("# ufw\nENABLED=no\nLOGLEVEL=low\n")
    log = tmp_path / "calls.txt"
    for name in ("ufw", "flatpak", "systemctl"):
        tool = tmp_path / name
        tool.write_text(f'#!/bin/sh\necho "{name} $*" >> "{log}"\n')
        tool.chmod(0o755)
    monkeypatch.setenv("PR7OS_ROOT", str(root))
    monkeypatch.setenv("PR7OS_UFW", str(tmp_path / "ufw"))
    monkeypatch.setenv("PR7OS_FLATPAK", str(tmp_path / "flatpak"))
    monkeypatch.setenv("PR7OS_SYSTEMCTL", str(tmp_path / "systemctl"))
    return load(STATIC / "system/setup_system.py", "setup_system"), root, log


def test_the_firewall_is_set_up_once_and_then_left_to_you(system):
    mod, root, log = system
    (root / "run/systemd/system").mkdir(parents=True)            # a running system: switched on at once
    assert mod.main(["configure"]) == 0
    calls = log.read_text().splitlines()
    assert calls[:2] == ["ufw default deny incoming", "ufw default allow outgoing"]
    assert "ufw allow 22/tcp comment SSH" in calls and "ufw allow 1714:1764/udp comment KDE Connect" in calls
    assert "ufw --force enable" in calls
    assert "ENABLED=yes" in (root / "etc/ufw/ufw.conf").read_text() and "LOGLEVEL=low" in (root / "etc/ufw/ufw.conf").read_text()
    assert "flatpak remote-add --system --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo" in calls
    log.write_text("")
    (root / "etc/ufw/ufw.conf").write_text("ENABLED=no\n")        # you switched it off later
    mod.main(["configure"])                                       # the next update
    assert not any(c.startswith("ufw") for c in log.read_text().splitlines())
    assert (root / "etc/ufw/ufw.conf").read_text() == "ENABLED=no\n"


def test_in_the_iso_build_the_firewall_is_marked_on_for_boot(system):
    mod, root, log = system                                       # no /run/systemd/system: the build's chroot
    mod.main(["configure"])
    calls = log.read_text()
    assert "ufw --force enable" not in calls and "ENABLED=yes" in (root / "etc/ufw/ufw.conf").read_text()


def test_a_failing_rule_is_tried_again_next_time(system, tmp_path):
    mod, root, log = system
    (tmp_path / "ufw").write_text(f'#!/bin/sh\necho "ufw $*" >> "{log}"\nexit 1\n')
    assert "failed" in mod.firewall()
    assert not (root / "var/lib/paragon/firewall-configured").exists()
    assert "ENABLED=no" in (root / "etc/ufw/ufw.conf").read_text()


# --------------------------------------------------------------------------- the account picture
@pytest.fixture
def people(tmp_path):
    root = tmp_path / "root"
    (root / "etc").mkdir(parents=True)
    (root / "usr/share/paragon").mkdir(parents=True)
    (root / "usr/share/paragon/face.png").write_bytes(b"PARAGON FACE")
    (root / "usr/share/desktop-base/active-theme").mkdir(parents=True)
    (root / "usr/share/desktop-base/active-theme/swirl.png").write_bytes(b"DEBIAN SWIRL")
    users = {"ari": 1000, "sam": 1001, "kim": 1002}
    (root / "etc/passwd").write_text("root:x:0:0:root:/root:/bin/bash\n" + "".join(
        f"{n}:x:{u}:{u}::/home/{n}:/bin/bash\n" for n, u in users.items()) + "gone:x:1003:1003::/home/gone:/bin/sh\n")
    for n in users:
        (root / "home" / n).mkdir(parents=True)
    acc = root / "var/lib/AccountsService"
    (acc / "icons").mkdir(parents=True)
    (acc / "users").mkdir(parents=True)
    # ari: Debian's swirl; sam: a photo of their own; kim: nothing at all
    (acc / "icons/ari").write_bytes(b"DEBIAN SWIRL")
    (acc / "users/ari").write_text("[User]\nLanguage=en_GB\nIcon=/var/lib/AccountsService/icons/ari\n")
    (acc / "icons/sam").write_bytes(b"SAM'S OWN PHOTO")
    (acc / "users/sam").write_text("[User]\nIcon=/var/lib/AccountsService/icons/sam\n")
    return load(STATIC / "setup_look.py", "setup_look"), root


def test_debians_picture_becomes_paragons_but_yours_stays(people):
    mod, root = people
    given = mod.faces(root)
    acc = root / "var/lib/AccountsService"
    assert sorted(given) == ["ari", "kim"]
    assert (acc / "icons/ari").read_bytes() == b"PARAGON FACE" and (acc / "icons/kim").read_bytes() == b"PARAGON FACE"
    assert (acc / "icons/sam").read_bytes() == b"SAM'S OWN PHOTO"
    assert "Language=en_GB" in (acc / "users/ari").read_text()
    assert (acc / "users/kim").read_text() == "[User]\nIcon=/var/lib/AccountsService/icons/kim\n"
    assert os.readlink(root / "home/ari/.face.icon") == "/usr/share/paragon/face.png"
    assert not (root / "home/sam/.face.icon").exists()
    assert mod.faces(root) == ["ari", "kim"]                      # again on the next update: the same, refreshed


def test_removing_the_look_takes_only_paragons_picture_back(people):
    mod, root = people
    mod.faces(root)
    mod.unfaces(root)
    acc = root / "var/lib/AccountsService"
    assert not (acc / "icons/ari").exists() and "Icon=" not in (acc / "users/ari").read_text()
    assert not (root / "home/ari/.face.icon").is_symlink()
    assert (acc / "icons/sam").read_bytes() == b"SAM'S OWN PHOTO"


def test_new_accounts_get_paragons_picture_from_skel(people):
    """desktop-base's /etc/skel/.face.icon (the swirl, and .face linking to it) is set aside, not overwritten: dpkg
    refuses a package that ships another package's file, which stopped 0.2.1's first ISO build."""
    mod, root = people
    skel = root / "etc/skel"
    skel.mkdir(parents=True)
    (skel / ".face.icon").write_bytes(b"DEBIAN SWIRL COPY")
    (skel / ".face").symlink_to(".face.icon")
    (root / "home/kim/.face.icon").write_bytes(b"DEBIAN SWIRL COPY")   # copied from skel before PR7-OS's look
    (root / "home/sam/.face.icon").write_bytes(b"DEBIAN SWIRL COPY")
    mod.skel_faces(root)
    assert os.readlink(skel / ".face.icon") == "/usr/share/paragon/face.png"
    assert os.readlink(skel / ".face") == "/usr/share/paragon/face.png"
    assert (root / "etc/paragon/skel-orig/.face.icon").read_bytes() == b"DEBIAN SWIRL COPY"
    assert sorted(f.name for f in skel.iterdir()) == [".face", ".face.icon"]   # nothing else for new accounts to copy
    mod.faces(root)
    assert os.readlink(root / "home/kim/.face.icon") == "/usr/share/paragon/face.png"   # the copied swirl replaced
    assert (root / "var/lib/AccountsService/icons/sam").read_bytes() == b"SAM'S OWN PHOTO"   # sam chose a photo:
    assert (root / "home/sam/.face.icon").read_bytes() == b"DEBIAN SWIRL COPY"              # their account untouched
    mod.skel_faces(root)                                          # every update: the same
    mod.unskel_faces(root)
    assert (skel / ".face.icon").read_bytes() == b"DEBIAN SWIRL COPY" and os.readlink(skel / ".face") == ".face.icon"


def test_alt_space_leaves_krunner(tmp_path, monkeypatch):
    """KRunner's kglobalaccel entry is diverted and replaced by a copy without Alt+Space (PR7-LN's key); again on every
    update it's the same; removing the look puts KRunner's own back. dpkg-divert is a stand-in that renames as it does."""
    mod = load(STATIC / "setup_look.py", "setup_look_kr")
    keys = tmp_path / "kglobalaccel"
    keys.mkdir()
    real = tmp_path / "applications_krunner.desktop"
    real.write_text("[Desktop Entry]\nName=KRunner\nX-KDE-Shortcuts=Alt+Space,Alt+F2,Search\nExec=krunner\n")
    (keys / "org.kde.krunner.desktop").symlink_to(real)               # Debian ships it as a link to the menu entry
    db = tmp_path / "diversions"
    tool = tmp_path / "bin/dpkg-divert"
    tool.parent.mkdir()
    tool.write_text(f'''#!/bin/sh
db="{db}"; touch "$db"
case "$1" in
  --list) grep -F "$2" "$db" | sed 's/$/ by paragon/' ;;
  --package) shift 2
    if [ "$1" = --divert ]; then to="$2"; shift 3; path="$2"; mv "$path" "$to"; echo "$path" >> "$db"
    else path="$3"; grep -vF "$path" "$db" > "$db.n"; mv "$db.n" "$db"; mv "$path.paragon-orig" "$path"; fi ;;
esac
''')
    tool.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tool.parent}:{os.environ['PATH']}")
    monkeypatch.setattr(mod, "KRUNNER_KEYS", keys / "org.kde.krunner.desktop")
    monkeypatch.setattr(mod, "KRUNNER_ORIG", keys / "org.kde.krunner.desktop.paragon-orig")
    mod.krunner_keys()
    ours = (keys / "org.kde.krunner.desktop").read_text()
    assert "X-KDE-Shortcuts=Alt+F2,Search\n" in ours and "Exec=krunner" in ours
    assert not (keys / "org.kde.krunner.desktop").is_symlink()
    mod.krunner_keys()                                                  # every update: the same
    assert (keys / "org.kde.krunner.desktop").read_text() == ours
    mod.krunner_keys_back()
    assert (keys / "org.kde.krunner.desktop").is_symlink() and "Alt+Space" in (keys / "org.kde.krunner.desktop").read_text()


def test_remote_desktop_from_home_networks_only_once(system):
    mod, root, log = system
    (root / "var/lib/paragon").mkdir(parents=True)
    (root / "var/lib/paragon/firewall-configured").write_text("yours\n")      # an installed PC: firewall set up long ago
    mod.main(["configure"])
    calls = [c for c in log.read_text().splitlines() if c.startswith("ufw")]
    assert calls == [f"ufw allow from {net} to any port 3389 proto tcp comment Remote desktop (home)"
                     for net in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]   # never "allow 3389" from anywhere
    log.write_text("")
    mod.main(["configure"])                                                     # the next update: left to you
    assert not any(c.startswith("ufw") for c in log.read_text().splitlines())


def test_the_flatpak_nvidia_service_is_switched_on(system):
    mod, root, log = system
    mod.main(["configure"])
    assert "systemctl enable pr7os-flatpak-gl.service pr7os-remote-desktop-firewall.service pr7os-remote-awake.service pr7os-greeter-check.service" in log.read_text().splitlines()


def test_at_start_up_the_remote_desktop_rules_are_retried_until_in(system, tmp_path):
    mod, root, log = system
    bad = tmp_path / "ufw"
    bad.write_text(f'#!/bin/sh\necho "ufw $*" >> "{log}"\ncase "$*" in *172.16*) echo "ERROR: initcaps" >&2; exit 1;; esac\n')
    assert mod.main(["remote-desktop"]) == 1                         # the second network refused: no marker
    assert not (root / "var/lib/paragon/remote-desktop-allowed").exists()
    bad.write_text(f'#!/bin/sh\necho "ufw $*" >> "{log}"\n')
    assert mod.main(["remote-desktop"]) == 0                         # the next start: all three, then never again
    assert (root / "var/lib/paragon/remote-desktop-allowed").exists()


def test_awake_while_someone_is_connected(tmp_path, monkeypatch):
    """pr7os-remote-awake: the inhibitor is held while SSH / remote desktop connections exist, released after."""
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader("remote_awake", str(STATIC / "system/pr7os-remote-awake"))
    spec = importlib.util.spec_from_loader("remote_awake", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    conns = tmp_path / "conns"
    ss = tmp_path / "ss"
    ss.write_text(f'#!/bin/sh\necho "$*" > {tmp_path}/ss-args\ncat "{conns}"\n')
    ss.chmod(0o755)
    monkeypatch.setenv("PR7OS_SS", str(ss))

    class Holder:
        def __init__(self, args):
            self.args, self.ended = args, False

        def poll(self):
            return 0 if self.ended else None

        def terminate(self):
            self.ended = True
    started = []
    awake = mod.Awake(start=lambda args: started.append(Holder(args)) or started[-1])
    conns.write_text("")
    assert not awake.once() and started == []                        # nobody connected: the PC may sleep
    conns.write_text("0 0 10.0.0.17:22 10.0.0.5:51000\n")
    assert awake.once() and awake.once() and len(started) == 1      # one inhibitor, held while connected
    assert started[0].args[:3] == ["systemd-inhibit", "--what=sleep:idle", "--who=Paragon PR7-OS"]
    assert "sport = :22 or sport = :3389" in (tmp_path / "ss-args").read_text()
    conns.write_text("")
    assert not awake.once() and started[0].ended                     # the last one left: let go


@pytest.fixture
def seat(tmp_path, monkeypatch):
    """A PC set to the Wayland login screen, with stand-ins for pgrep / loginctl / systemctl."""
    root, bin_ = tmp_path / "root", tmp_path / "bin"
    (root / "etc/sddm.conf.d").mkdir(parents=True)
    (root / "etc/sddm.conf.d/20-paragon-wayland.conf").write_text("[General]\nDisplayServer=wayland\n")
    bin_.mkdir()
    log, greeter, session = tmp_path / "log", tmp_path / "greeter", tmp_path / "session"
    log.write_text("")
    tools = {"pgrep": f'[ -f "{greeter}" ] && [ "$2" = sddm-greeter-qt6 ] && echo 1234; exit 0',
             "loginctl": f'case "$1" in show-seat) [ -f "{session}" ] && echo c2;; show-session) cat "{session}";; esac',
             "systemctl": f'echo "systemctl $*" >> "{log}"'}
    for name, body in tools.items():
        f = bin_ / name
        f.write_text("#!/bin/sh\n" + body + "\n")
        f.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("PR7OS_ROOT", str(root))
    monkeypatch.setenv("PR7OS_GREETER_WAIT", "3")
    monkeypatch.setenv("PR7OS_GREETER_STEP", "0.5")
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader("greeter_check", str(STATIC / "system/pr7os-greeter-check"))
    spec = importlib.util.spec_from_loader("greeter_check", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod, root, log, greeter, session


def test_wayland_login_screen_up_is_left_alone(seat):
    mod, root, log, greeter, session = seat
    greeter.write_text("")
    assert mod.main() == 0
    assert not (root / mod.FALLBACK).exists() and log.read_text() == ""


def test_a_desktop_already_running_counts(seat):
    mod, root, log, greeter, session = seat
    session.write_text("user\n")
    assert mod.main() == 0 and not (root / mod.FALLBACK).exists()


def test_no_login_screen_goes_back_to_x11_once(seat):
    mod, root, log, greeter, session = seat
    assert mod.main() == 0                                       # nothing came up
    conf = (root / mod.FALLBACK).read_text()
    assert "DisplayServer=x11" in conf and "systemctl restart sddm" in log.read_text()
    log.write_text("")
    assert mod.main() == 0 and log.read_text() == ""             # the marker: never again, no restart loop
