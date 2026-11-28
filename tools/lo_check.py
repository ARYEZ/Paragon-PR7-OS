"""CI: does LibreOffice itself see PR7-OS's settings? Starts it headless, asks its configuration (through UNO) for the
values paragon.xcd sets, and compares them with pr7os.assets. A name LibreOffice doesn't know is silently ignored, so
only asking LibreOffice proves the settings took. Run in the clean Debian 13 (install_test.sh), with python3-uno."""
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import uno  # noqa: E402  (python3-uno)
from com.sun.star.beans import PropertyValue  # noqa: E402

LO_DOC_FONT = "Inter"
LO_CHART = ["#DE0639", "#F2781E", "#D9468C", "#FFB347", "#8A8A92", "#FF4F7B", "#A0420A", "#B9B5B8", "#7A0A2E",
            "#FFA05C", "#4A4A52", "#C2185B"]


def read(ctx, node: str, prop: str):
    provider = ctx.ServiceManager.createInstanceWithContext("com.sun.star.configuration.ConfigurationProvider", ctx)
    arg = PropertyValue()
    arg.Name, arg.Value = "nodepath", node
    access = provider.createInstanceWithArguments("com.sun.star.configuration.ConfigurationAccess", (arg,))
    return access.getPropertyValue(prop)


def main() -> int:
    profile = tempfile.mkdtemp(prefix="lo-profile-")
    office = subprocess.Popen(["soffice", "--headless", "--invisible", "--norestore", "--nologo",
                               f"-env:UserInstallation=file://{profile}", "--accept=pipe,name=pr7oscheck;urp;"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    ctx = None
    for _ in range(90):
        try:
            ctx = resolver.resolve("uno:pipe,name=pr7oscheck;urp;StarOffice.ComponentContext")
            break
        except Exception:
            time.sleep(1)
    if ctx is None:
        office.kill()
        print("FAILED: LibreOffice didn't start")
        return 1
    problems = []
    for prop in ("Standard", "Heading", "List", "Caption", "Index"):
        got = read(ctx, "/org.openoffice.Office.Writer/DefaultFont", prop)
        if got != LO_DOC_FONT:
            problems.append(f"Writer DefaultFont/{prop} is {got!r}, not {LO_DOC_FONT!r}")
    series = [int(v) & 0xFFFFFFFF for v in read(ctx, "/org.openoffice.Office.Chart/DefaultColor", "Series")]
    want = [int(c[1:], 16) for c in LO_CHART]
    if series != want:
        problems.append(f"Chart DefaultColor/Series is {[hex(v) for v in series]}")
    office.terminate()
    try:
        office.wait(30)
    except subprocess.TimeoutExpired:
        office.kill()
    for p in problems:
        print("FAILED:", p)
    if not problems:
        print("LibreOffice sees PR7-OS's settings: documents in Inter, charts in the family's colours")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
