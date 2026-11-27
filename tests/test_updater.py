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
    """Its arguments are ignored: it only installs the newest release of PR7-OS's own repository."""
    done = subprocess.run([sys.executable, str(UPD / "pr7os-update-helper"), "--server", "http://evil.example",
                           "/tmp/evil.deb"], env=env, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0 and "evil" not in tools["log"].read_text()


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
