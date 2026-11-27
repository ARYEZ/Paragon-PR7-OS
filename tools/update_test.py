"""A real update, in a Debian 13 container (CI: docker run debian:trixie): the updater package's old version is
installed with apt, the new one is published on a local stand-in release, and the root helper updates to it.

    python3 tools/update_test.py        (as root, with the repository as the working folder)

What it proves: the packages install with apt (their dependencies from Debian), the helper finds the release, checks
the package against the manifest, installs it, and dpkg then has the new version.
"""
import hashlib
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pr7os import packages  # noqa: E402

OLD, NEW = "0.0.1", "0.0.2"


def installed_version() -> str:
    return subprocess.run(["dpkg-query", "-W", "-f", "${Version}", "paragon-pr7os-updates"],
                          capture_output=True, text=True).stdout.strip()


def main() -> int:
    work = Path(tempfile.mkdtemp())
    files = {rel: packages.STATIC / "updater" / src for rel, src in packages.UPDATER_FILES.items()}
    old = packages.build_deb("paragon-pr7os-updates", OLD, files, work)
    site = work / "site"
    rel = site / "ARYEZ/Paragon-PR7-OS/releases/download" / f"v{NEW}"
    rel.mkdir(parents=True)
    new = packages.build_deb("paragon-pr7os-updates", NEW, files, rel)
    (rel / "pr7os-update.json").write_text(json.dumps({"version": NEW, "packages": [{
        "name": "paragon-pr7os-updates", "version": NEW, "file": new.name,
        "sha256": hashlib.sha256(new.read_bytes()).hexdigest(), "size": new.stat().st_size}]}))
    api = site / "repos/ARYEZ/Paragon-PR7-OS/releases"
    api.mkdir(parents=True)
    (api / "latest").write_text(json.dumps({"tag_name": f"v{NEW}", "body": "test"}))

    subprocess.run(["apt-get", "install", "-y", str(old)], check=True,
                   env=dict(os.environ, DEBIAN_FRONTEND="noninteractive"))
    assert installed_version() == OLD, installed_version()
    print(f"installed {OLD} with apt")

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(site), **k)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    env = dict(os.environ, PR7OS_UPDATE_SERVER=f"http://127.0.0.1:{server.server_port}")
    done = subprocess.run(["/usr/libexec/paragon/pr7os-update-helper"], env=env, capture_output=True, text=True)
    print(done.stdout, done.stderr)
    assert done.returncode == 0 and done.stdout.strip().splitlines()[-1] == f"DONE installed {NEW}", done.stdout
    assert "STEP The updater was updated: checking again with the new one" in done.stdout   # its new copy looked again
    assert installed_version() == NEW, installed_version()
    again = subprocess.run(["/usr/libexec/paragon/pr7os-update-helper"], env=env, capture_output=True, text=True)
    assert again.stdout.strip().splitlines()[-1] == f"DONE up-to-date {NEW}", again.stdout
    print(f"updated to {NEW} by the helper; running it again: up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
