"""Paragon PR7-OS updates: what's newer on GitHub, downloaded and checked, installed with apt (standard library only).

Each release of ARYEZ/Paragon-PR7-OS carries pr7os-update.json (every package's version, file, SHA-256 and size) and
the packages. A package whose installed version differs from the manifest's is pending; pending packages are
downloaded from that release only, checked against the manifest, and installed together with apt-get (new Debian
dependencies come from Debian). The addresses are built here from the repository and the release's tag: nothing
outside decides where the root helper downloads from. PR7OS_UPDATE_SERVER (tests) serves both the API and the
downloads; pkexec clears the environment, so it never reaches the helper there.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

REPO = "ARYEZ/Paragon-PR7-OS"
MANIFEST = "pr7os-update.json"
USER_AGENT = "Paragon-PR7-OS-update"           # names only the program
DEB_NAME = re.compile(r"^paragon-pr7os-[a-z]+_[A-Za-z0-9.+~]+_(all|amd64)\.deb$")
PACKAGE = re.compile(r"^paragon-pr7os-[a-z]+$")   # any of PR7-OS's own packages the release lists (0.2.1's fixed
                                                   # list of four skipped the new paragon-pr7os-system)


class UpdateError(Exception):
    pass


def _server() -> str | None:
    return os.environ.get("PR7OS_UPDATE_SERVER")


def api_url(path: str) -> str:
    return f"{_server() or 'https://api.github.com'}/repos/{REPO}/{path}"


def download_url(tag: str, name: str) -> str:
    return f"{_server() or 'https://github.com'}/{REPO}/releases/download/{tag}/{name}"


def fetch(url: str, timeout: float = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except OSError as e:
        raise UpdateError(f"GitHub can't be reached ({e})") from e


def _with_packages() -> list[tuple[tuple, str, dict]]:
    """Every published release that carries packages (a manifest), as (version key, tag, release); never 0.0.x."""
    try:
        rels = json.loads(fetch(api_url("releases?per_page=50")))
    except ValueError as e:
        raise UpdateError(f"the releases can't be read ({e})") from e
    out = []
    for rel in rels if isinstance(rels, list) else []:
        tag = rel.get("tag_name", "")
        names = {a.get("name") for a in rel.get("assets", [])}
        if rel.get("draft") or rel.get("prerelease") or MANIFEST not in names or not tag.startswith("v"):
            continue
        if not tag.startswith("v0.0."):
            out.append((version_key(tag[1:]), tag, rel))
    return out


def latest() -> dict:
    """The newest release: {"tag", "version", "notes", "manifest"}. The highest version that carries packages, not
    GitHub's "latest" mark: that's simply the last one published, and a release built more slowly (one with an ISO)
    can be published after a newer one (0.6.0 after 0.6.2)."""
    found = _with_packages()
    if found:
        _key, tag, rel = max(found, key=lambda x: x[0])
        return _info(tag, rel)
    try:
        rel = json.loads(fetch(api_url("releases/latest")))
        tag = rel["tag_name"]
    except (ValueError, KeyError) as e:
        raise UpdateError(f"the release's details can't be read ({e})") from e
    return _info(tag, rel)


def is_older(info: dict, have: dict[str, str]) -> bool:
    """Would installing `info` take this PC back? (Updating never does; only GO BACK may.)"""
    current = current_version(have)
    return bool(current) and version_key(info["version"]) < version_key(current)


def version_key(v: str) -> tuple:
    """"0.4.0" -> (0, 4, 0); a package's version (Python's "1+hash") sorts first."""
    return tuple(int(x) for x in re.findall(r"\d+", v.split("+")[0].split("~")[0])[:4]) or (0,)


def _info(tag: str, rel: dict) -> dict:
    if not re.fullmatch(r"v[0-9][0-9A-Za-z.+~-]*", tag):
        raise UpdateError(f"unexpected release tag {tag!r}")
    try:
        manifest = json.loads(fetch(download_url(tag, MANIFEST)))
    except ValueError as e:
        raise UpdateError(f"the release's details can't be read ({e})") from e
    return {"tag": tag, "version": manifest.get("version", tag[1:]), "notes": rel.get("body") or "",
            "manifest": manifest}


def previous(current: str) -> dict:
    """The newest release older than `current` that carries packages (Go back): {"tag", "version", ...}."""
    older = [r for r in _with_packages() if r[0] < version_key(current)]
    if not older:
        raise UpdateError(f"there's no release before {current} to go back to")
    _key, tag, rel = max(older, key=lambda x: x[0])
    return _info(tag, rel)


def current_version(have: dict[str, str]) -> str:
    """The PR7-OS version installed: its look package's (every release builds them all with the same version)."""
    return have.get("paragon-pr7os-look") or have.get("paragon-pr7os-updates") or ""


# ---------------------------------------------------------------------------------------------- Timeshift snapshots
SNAPSHOT_PREFIX = "PR7-OS before "
KEEP_SNAPSHOTS = 3
MIN_FREE = 5_000_000_000


def _timeshift() -> str | None:
    return os.environ.get("PR7OS_TIMESHIFT") or shutil.which("timeshift")


def timeshift_config(path: str | None = None) -> None:
    """Timeshift's settings the first time (Timeshift's own app writes them otherwise): rsync snapshots of the system on
    the drive it runs from, home folders left out (yours are PR7-BK's to back up), no schedule of its own."""
    path = path or os.environ.get("PR7OS_TIMESHIFT_CONFIG", "/etc/timeshift/timeshift.json")
    if os.path.exists(path):
        return
    uuid = subprocess.run(["findmnt", "-no", "UUID", "/"], capture_output=True, text=True).stdout.strip()
    conf = {"backup_device_uuid": uuid, "parent_device_uuid": "", "do_first_run": "false", "btrfs_mode": "false",
            "include_btrfs_home_for_backup": "false", "include_btrfs_home_for_restore": "false",
            "stop_cron_emails": "true", "schedule_monthly": "false", "schedule_weekly": "false",
            "schedule_daily": "false", "schedule_hourly": "false", "schedule_boot": "false", "count_monthly": "2",
            "count_weekly": "3", "count_daily": "5", "count_hourly": "6", "count_boot": "5",
            "date_format": "%Y-%m-%d %H:%M:%S", "exclude": ["/root/**", "/home/*/**"], "exclude-apps": []}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(conf, fh, indent=2)


def snapshots(run=subprocess.run) -> list[str]:
    """PR7-OS's own Timeshift snapshots, oldest first."""
    ts = _timeshift()
    if not ts:
        return []
    out = run([ts, "--list", "--scripted"], capture_output=True, text=True).stdout
    names = []
    for line in out.splitlines():
        m = re.match(r"^\s*\d+\s+>\s+(\S+)\s+\S*\s+(.*)$", line)
        if m and m.group(2).strip().startswith(SNAPSHOT_PREFIX):
            names.append(m.group(1))
    return sorted(names)


def snapshot(label: str, run=subprocess.run) -> str:
    """A Timeshift snapshot of the system before an update ("taken", or why not: an update never fails for it)."""
    ts = _timeshift()
    if not ts:
        return "skipped (Timeshift isn't installed)"
    root = os.environ.get("PR7OS_SNAPSHOT_ROOT", "/")
    if shutil.disk_usage(root).free < MIN_FREE:
        return "skipped (less than 5 GB free)"
    try:
        timeshift_config()
        done = run([ts, "--create", "--comments", SNAPSHOT_PREFIX + label, "--tags", "O", "--scripted"],
                   capture_output=True, text=True, timeout=3600)
    except (OSError, subprocess.SubprocessError) as e:
        return f"skipped ({e})"
    if done.returncode:
        return f"failed ({(done.stdout + done.stderr).strip().splitlines()[-1:] or ['?']})"
    for old in snapshots(run)[:-KEEP_SNAPSHOTS]:
        run([ts, "--delete", "--snapshot", old, "--scripted"], capture_output=True, text=True)
    return "taken"


def installed() -> dict[str, str]:
    """The PR7-OS packages installed now and their versions (dpkg's records)."""
    cmd = os.environ.get("PR7OS_DPKG_QUERY", "dpkg-query")
    done = subprocess.run([cmd, "-W", "-f", "${Package}\\t${Version}\\t${db:Status-Status}\\n", "paragon-pr7os-*"],
                          capture_output=True, text=True)
    out = {}
    for line in done.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[2] == "installed":
            out[parts[0]] = parts[1]
    return out


def pending(manifest: dict, have: dict[str, str]) -> list[dict]:
    """The manifest's packages whose installed version differs (or that aren't installed yet)."""
    out = []
    for p in manifest.get("packages", []):
        if PACKAGE.match(str(p.get("name", ""))) and have.get(p["name"]) != p.get("version"):
            out.append(p)
    return out


def needs_logout(pkgs: list[dict]) -> bool:
    """The look changes what Plasma loaded at login: logging out and in shows it everywhere."""
    return any(p["name"] == "paragon-pr7os-look" for p in pkgs)


def download(tag: str, pkgs: list[dict], folder: Path, progress=None) -> list[Path]:
    """Each package from the release, checked against the manifest (name, size, SHA-256)."""
    files = []
    for i, p in enumerate(pkgs, 1):
        name = p.get("file", "")
        if not DEB_NAME.match(name) or not name.startswith(p["name"] + "_"):
            raise UpdateError(f"the manifest names an unexpected file {name!r}")
        if progress:
            progress(i, len(pkgs), name)
        data = fetch(download_url(tag, name), timeout=600)
        if len(data) != int(p["size"]) or hashlib.sha256(data).hexdigest() != p["sha256"]:
            raise UpdateError(f"{name} didn't arrive intact (its size or checksum doesn't match the release)")
        path = folder / name
        path.write_bytes(data)
        files.append(path)
    return files


def install(files: list[Path], output=print) -> int:
    """apt-get installs the packages together (Debian's dependencies from Debian); changed config files are kept."""
    apt = os.environ.get("PR7OS_APT", "apt-get")
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
    wait = ["-o", "DPkg::Lock::Timeout=600"]     # Debian's daily security updates may hold apt's lock: wait for them
    subprocess.run([apt, *wait, "update", "-qq"], env=env)          # best effort: fresh lists for new dependencies
    cmd = [apt, *wait, "install", "-y", "--allow-downgrades", "-o", "Dpkg::Options::=--force-confdef",
           "-o", "Dpkg::Options::=--force-confold"] + [str(f.resolve()) for f in files]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        output(line.rstrip())
    return proc.wait()


def settings_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "paragon" / "pr7os-update.json"


def skipped() -> str:
    try:
        return json.loads(settings_path().read_text()).get("skip", "")
    except (OSError, ValueError):
        return ""


def skip(version: str) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"skip": version}))
