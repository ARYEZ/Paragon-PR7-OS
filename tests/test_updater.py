"""The updater against a stand-in GitHub (a real HTTP server here): finding the release, what's pending, refusing what
doesn't match the manifest, the root helper from start to finish, the daily check's notification, the window.
apt-get, dpkg-query and notify-send are stand-in scripts that record what they were asked."""
import hashlib
import http.server
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
UPD = ROOT / "pr7os/static/updater"
TAG, VERSION = "v9.9.9", "9.9.9"


def load():
    spec = importlib.util.spec_from_file_location("pr7os_update", UPD / "pr7os_update.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def release(tmp_path):
    """A release on a local server: the API's latest-release answer, the manifest, two packages' files."""
    site = tmp_path / "site"
    files = site / "ARYEZ/Paragon-PR7-OS/releases/download" / TAG
    files.mkdir(parents=True)
    pkgs = []
    for name in ("paragon-pr7os-updates", "paragon-pr7os-look"):
        deb = files / f"{name}_{VERSION}_all.deb"
        deb.write_bytes(f"stand-in {name}".encode() * 100)
        pkgs.append({"name": name, "version": VERSION, "file": deb.name,
                     "sha256": hashlib.sha256(deb.read_bytes()).hexdigest(), "size": deb.stat().st_size})
    manifest = {"version": VERSION, "packages": pkgs}
    (files / "pr7os-update.json").write_text(json.dumps(manifest))
    api = site / "repos/ARYEZ/Paragon-PR7-OS/releases"
    api.mkdir(parents=True)
    (api / "latest").write_text(json.dumps({"tag_name": TAG, "body": "## 9.9.9\n\n- Better things."}))
    # an older release to go back to (with its own packages), a development build and one without packages
    old = site / "ARYEZ/Paragon-PR7-OS/releases/download/v9.9.8"
    old.mkdir(parents=True)
    old_pkgs = []
    for name in ("paragon-pr7os-updates", "paragon-pr7os-look"):
        deb = old / f"{name}_9.9.8_all.deb"
        deb.write_bytes(f"older {name}".encode() * 100)
        old_pkgs.append({"name": name, "version": "9.9.8", "file": deb.name,
                         "sha256": hashlib.sha256(deb.read_bytes()).hexdigest(), "size": deb.stat().st_size})
    (old / "pr7os-update.json").write_text(json.dumps({"version": "9.9.8", "packages": old_pkgs}))
    asset = [{"name": "pr7os-update.json"}]
    (api / "index.html").write_text(json.dumps([          # the releases list (the server ignores ?per_page=50)
        {"tag_name": TAG, "assets": asset, "body": "## 9.9.9\n\n- Better things."}, {"tag_name": "v9.9.8", "assets": asset},
        {"tag_name": "v9.9.7", "assets": []}, {"tag_name": "v0.0.9", "assets": asset}]))

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(site), **k)

        def log_message(self, *a):
            pass
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield {"url": f"http://127.0.0.1:{server.server_port}", "files": files, "manifest": manifest}
    server.shutdown()


@pytest.fixture
def tools(tmp_path):
    """Stand-in apt-get / dpkg-query / notify-send that record their arguments."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.txt"

    def script(name, body):
        p = bin_dir / name
        p.write_text("#!/bin/sh\n" + body)
        p.chmod(0o755)
        return p
    script("apt-get", f'echo "apt-get $*" >> "{log}"\necho "Setting up stand-in ..."\n')
    script("dpkg-query", 'printf "paragon-pr7os-updates\\t0.1.1\\tinstalled\\n"\n')
    script("notify-send", f'echo "notify-send $*" >> "{log}"\ncat "{tmp_path}/answer" 2>/dev/null\n')
    return {"bin": bin_dir, "log": log, "answer": tmp_path / "answer"}


@pytest.fixture
def env(release, tools, tmp_path, monkeypatch):
    monkeypatch.setenv("PR7OS_UPDATE_SERVER", release["url"])
    monkeypatch.setenv("PR7OS_APT", str(tools["bin"] / "apt-get"))
    monkeypatch.setenv("PR7OS_DPKG_QUERY", str(tools["bin"] / "dpkg-query"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("PATH", f"{tools['bin']}{os.pathsep}{os.environ['PATH']}")
    return dict(os.environ)


def test_the_newest_release_and_whats_pending(env):
    u = load()
    info = u.latest()
    assert info["tag"] == TAG and info["version"] == VERSION and "Better things" in info["notes"]
    have = u.installed()
    assert have == {"paragon-pr7os-updates": "0.1.1"}
    names = [p["name"] for p in u.pending(info["manifest"], have)]
    assert names == ["paragon-pr7os-updates", "paragon-pr7os-look"]                     # the look isn't there yet
    assert u.pending(info["manifest"], {p["name"]: VERSION for p in info["manifest"]["packages"]}) == []
    # a package the updater has never heard of is installed too, if it's PR7-OS's (0.2.1's fixed list of four skipped
    # the new paragon-pr7os-system); anything else in a manifest is ignored
    extra = {"packages": [{"name": "paragon-pr7os-system", "version": VERSION},
                          {"name": "paragon-pr7os-brandnew", "version": VERSION},
                          {"name": "openssh-server", "version": "1"}, {"name": "paragon-pr7os-../x", "version": "1"}]}
    assert [p["name"] for p in u.pending(extra, have)] == ["paragon-pr7os-system", "paragon-pr7os-brandnew"]
    assert u.needs_logout(u.pending(info["manifest"], have))


def test_nothing_that_doesnt_match_the_release_is_installed(env, release, tmp_path):
    u = load()
    info = u.latest()
    pkgs = info["manifest"]["packages"]
    got = u.download(info["tag"], pkgs, tmp_path)
    assert [f.name for f in got] == [p["file"] for p in pkgs]
    bad = [dict(pkgs[0], sha256="0" * 64)]
    with pytest.raises(u.UpdateError, match="intact"):
        u.download(info["tag"], bad, tmp_path)
    for name in ("../../etc/passwd", "evil_1.0_all.deb", "paragon-pr7os-look_1.0_all.deb/../x", "paragon-pr7os-look.sh"):
        with pytest.raises(u.UpdateError, match="unexpected file"):
            u.download(info["tag"], [dict(pkgs[0], file=name)], tmp_path)


def test_the_helper_installs_the_release(env, tools):
    done = subprocess.run([sys.executable, str(UPD / "pr7os-update-helper")], env=env, capture_output=True, text=True,
                          timeout=60)
    lines = done.stdout.splitlines()
    assert done.returncode == 0, done.stdout + done.stderr
    assert lines[0] == "STEP Looking for the newest release"
    assert "PROGRESS 1 2 paragon-pr7os-updates_9.9.9_all.deb" in lines
    assert lines[-1] == f"DONE logout {VERSION}"                      # the look changed: log out to see it
    # the updater updated itself, so its new copy looked again (once: the stand-in dpkg never changes its answer)
    assert lines.count("STEP The updater was updated: checking again with the new one") == 1
    assert lines.count("STEP Looking for the newest release") == 2
    calls = tools["log"].read_text().splitlines()
    assert calls[0] == "apt-get -o DPkg::Lock::Timeout=600 update -qq"     # waits out Debian's daily security updates
    install = calls[1].split()
    assert install[:6] == ["apt-get", "-o", "DPkg::Lock::Timeout=600", "install", "-y", "--allow-downgrades"]
    assert "Dpkg::Options::=--force-confold" in install                  # your changed config files stay yours
    assert [Path(a).name for a in install if a.endswith(".deb")] == [
        "paragon-pr7os-updates_9.9.9_all.deb", "paragon-pr7os-look_9.9.9_all.deb"]


def test_the_helper_takes_no_orders_from_its_command_line(env, tools):
    """Anything but the one word `previous` is refused, and nothing is installed."""
    done = subprocess.run([sys.executable, str(UPD / "pr7os-update-helper"), "--server", "http://evil.example",
                           "/tmp/evil.deb"], env=env, capture_output=True, text=True, timeout=60)
    assert done.returncode == 2 and not tools["log"].exists()


def test_going_back_to_the_release_before(env, tools):
    """Go back: the release just before the installed one (not a development build, not one without packages), every
    package of it installed with apt (downgrades allowed), and no re-run of the updater (it would update again)."""
    u = load()
    assert u.previous("9.9.9")["tag"] == "v9.9.8"
    with pytest.raises(u.UpdateError, match="no release before"):
        u.previous("9.9.8")                                   # 9.9.7 has no packages, 0.0.9 is a development build
    tools["bin"].joinpath("dpkg-query").write_text(
        "#!/bin/sh\nprintf 'paragon-pr7os-updates\\t9.9.9\\tinstalled\\nparagon-pr7os-look\\t9.9.9\\tinstalled\\n'\n")
    done = subprocess.run([sys.executable, str(UPD / "pr7os-update-helper"), "previous"], env=env,
                          capture_output=True, text=True, timeout=60)
    lines = done.stdout.splitlines()
    assert done.returncode == 0, done.stdout + done.stderr
    assert lines[-1] == "DONE logout 9.9.8 back"
    assert "STEP The updater was updated: checking again with the new one" not in lines
    install = tools["log"].read_text().splitlines()[1].split()
    assert "--allow-downgrades" in install
    assert [Path(a).name for a in install if a.endswith(".deb")] == ["paragon-pr7os-updates_9.9.8_all.deb",
                                                                     "paragon-pr7os-look_9.9.8_all.deb"]


TIMESHIFT_STANDIN = """#!/bin/sh
echo "$*" >> "LOG"
if [ "$1" = --list ]; then
  echo "Num     Name                 Tags  Description"
  echo "0    >  2026-01-01_10-00-00  O     PR7-OS before 0.2.0"
  echo "1    >  2026-02-01_10-00-00  O     PR7-OS before 0.3.0"
  echo "2    >  2026-02-15_10-00-00  D     my own snapshot"
  echo "3    >  2026-03-01_10-00-00  O     PR7-OS before 0.4.0"
  echo "4    >  2026-04-01_10-00-00  O     PR7-OS before 0.5.0"
fi
"""


def test_a_timeshift_snapshot_before_each_update(tmp_path, monkeypatch):
    """Timeshift's settings written the first time (system only, home folders out), a snapshot named for the update,
    and only PR7-OS's three newest kept (other snapshots are left alone)."""
    u = load()
    log = tmp_path / "ts.log"
    ts = tmp_path / "timeshift"
    ts.write_text(TIMESHIFT_STANDIN.replace("LOG", str(log)))
    ts.chmod(0o755)
    conf = tmp_path / "etc/timeshift/timeshift.json"
    monkeypatch.setenv("PR7OS_TIMESHIFT", str(ts))
    monkeypatch.setenv("PR7OS_TIMESHIFT_CONFIG", str(conf))
    monkeypatch.setenv("PR7OS_SNAPSHOT_ROOT", str(tmp_path))
    assert u.snapshot("0.5.0") == "taken"
    settings = json.loads(conf.read_text())
    assert settings["btrfs_mode"] == "false" and "/home/*/**" in settings["exclude"] and settings["do_first_run"] == "false"
    calls = log.read_text().splitlines()
    assert calls[0] == "--create --comments PR7-OS before 0.5.0 --tags O --scripted"
    assert "--delete --snapshot 2026-01-01_10-00-00 --scripted" in calls               # the oldest of PR7-OS's four
    assert not any("2026-02-15" in c for c in calls if c.startswith("--delete"))       # yours is never touched
    monkeypatch.setattr(u, "MIN_FREE", 10 ** 18)
    assert u.snapshot("0.6.0").startswith("skipped")                                    # not enough room: no snapshot
    monkeypatch.delenv("PR7OS_TIMESHIFT")
    monkeypatch.setattr(u.shutil, "which", lambda name: None)
    assert u.snapshot("0.6.0") == "skipped (Timeshift isn't installed)"


def test_the_daily_check_notifies_and_remembers_skip(env, tools):
    tools["answer"].write_text("skip\n")
    subprocess.run([sys.executable, str(UPD / "pr7os-update"), "--check"], env=env, timeout=60, check=True)
    calls = tools["log"].read_text()
    assert f"Paragon PR7-OS {VERSION} is ready" in calls and "--action=update=UPDATE" in calls
    settings = Path(env["XDG_CONFIG_HOME"]) / "paragon/pr7os-update.json"
    assert json.loads(settings.read_text()) == {"skip": VERSION}
    tools["log"].write_text("")
    subprocess.run([sys.executable, str(UPD / "pr7os-update"), "--check"], env=env, timeout=60, check=True)
    assert tools["log"].read_text() == ""                              # skipped: not asked again for this version


def test_the_daily_check_is_quiet_offline(env, monkeypatch, tools):
    env = dict(env, PR7OS_UPDATE_SERVER="http://127.0.0.1:9")          # nothing listens there
    done = subprocess.run([sys.executable, str(UPD / "pr7os-update"), "--check"], env=env, timeout=60,
                          capture_output=True, text=True)
    assert done.returncode == 0 and not tools["log"].exists()


def test_the_window_updates(env, tools, tmp_path, monkeypatch, qapp):
    sys.path.insert(0, str(UPD))
    import window
    u = window.u
    fake = tmp_path / "helper.sh"
    fake.write_text("#!/bin/sh\necho 'STEP Downloading Paragon PR7-OS 9.9.9'\necho 'PROGRESS 1 2 a.deb'\n"
                    "echo 'PROGRESS 2 2 b.deb'\necho 'LOG Setting up paragon-pr7os-look'\necho 'DONE logout 9.9.9'\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PR7OS_UPDATE_HELPER", str(fake))
    w = window.Window(sync=True)
    assert w.state == "available" and "9.9.9 is ready" in w.heading.text() and w.update_key.isEnabled()
    assert "You have" not in w.status.text() and "2 packages" in w.status.text()
    w.start()
    qapp.processEvents()
    assert w.state == "done" and "9.9.9 is installed" in w.heading.text()
    assert w.update_key.text() == "LOG OUT NOW" and "Setting up paragon-pr7os-look" in w.details.toPlainText()
    w.close()
    # a cancelled password: nothing changed, UPDATE still there
    cancel = tmp_path / "cancel.sh"
    cancel.write_text("#!/bin/sh\nexit 126\n")
    cancel.chmod(0o755)
    monkeypatch.setenv("PR7OS_UPDATE_HELPER", str(cancel))
    w = window.Window(sync=True)
    w.start()
    qapp.processEvents()
    assert w.state == "available" and "Nothing was changed" in w.status.text() and w.update_key.isEnabled()
    w.close()



def test_the_window_goes_back(env, tools, tmp_path, monkeypatch, qapp):
    """GO BACK asks first, runs the helper with `previous`, says which version it's back to, and skips the newer one
    so the daily check doesn't offer it straight away."""
    sys.path.insert(0, str(UPD))
    import window
    u = window.u
    calls = tmp_path / "helper-args"
    fake = tmp_path / "helper.sh"
    fake.write_text(f'#!/bin/sh\necho "$*" > "{calls}"\necho "STEP Looking for the release before this one"\n'
                    "echo 'DONE logout 9.9.8 back'\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PR7OS_UPDATE_HELPER", str(fake))
    w = window.Window(sync=True)
    w.confirm = lambda text: False                          # "No": nothing happens
    w.back.click()
    assert not calls.exists() and w.state == "available"
    w.confirm = lambda text: True
    w.back.click()
    qapp.processEvents()
    assert calls.read_text().strip() == "previous"
    assert w.state == "done" and "Back to Paragon PR7-OS 9.9.8" in w.heading.text()
    assert u.skipped() == VERSION                           # 9.9.9 isn't offered again by the daily check
    w.close()


def test_the_newest_version_wins_over_githubs_latest_mark(release, monkeypatch):
    """A slower release (one with an ISO) published after a newer one gets GitHub's "latest" mark: the updater takes
    the highest version that carries packages, and an update never takes a PC back."""
    site = Path(str(release["files"]).split("/ARYEZ/")[0])
    (site / "repos/ARYEZ/Paragon-PR7-OS/releases/latest").write_text(json.dumps({"tag_name": "v9.9.8", "body": ""}))
    monkeypatch.setenv("PR7OS_UPDATE_SERVER", release["url"])
    u = load()
    assert u.latest()["version"] == VERSION
    newer = {"paragon-pr7os-look": "10.0.0", "paragon-pr7os-updates": "10.0.0"}
    assert u.is_older(u.latest(), newer) and not u.is_older(u.latest(), {"paragon-pr7os-look": "9.9.8"})
    assert not u.is_older(u.latest(), {})
