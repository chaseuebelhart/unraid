"""Run a host job through the Unraid user script 'winswatch'. Usage: python hostexec.py run labels"""
import re, shutil, sys, time
from pathlib import Path
import requests

APP = Path("/mnt/nastower/appdata/scripts/winswatch")
TOKEN = Path.home().joinpath(".config/nastower/api_token").read_text().strip()
LOG = APP / "host/last.log"
EXIT_RE = re.compile(r"^=== exit (\d+) ===", re.M)

def _wait_for_log(started: float, timeout: int = 1800) -> int | None:
    """The agent closes the HTTP connection after ~60s but the job keeps running; watch last.log for its exit marker."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if LOG.exists() and LOG.stat().st_mtime >= started:
            m = EXIT_RE.search(LOG.read_text())
            if m:
                return int(m.group(1))
        time.sleep(5)
    return None

def run(job: str):
    # Jobs are resolved relative to this file (the repo checkout), so a job committed
    # here deploys identically whether run from the repo or the NFS-mounted server tree.
    src = Path(__file__).parent / "host/jobs" / f"{job}.sh"
    shutil.copy(src, APP / "host/job.sh")
    started = time.time() - 5
    ok = None
    try:
        r = requests.post("http://192.168.0.15:8043/api/v1/user-scripts/winswatch/execute", headers={"Authorization": f"Bearer {TOKEN}"},
                          json={"wait": True}, timeout=1800)
        d = r.json(); print(d.get("output") or d.get("message") or d)
        ok = d.get("success", False)
    except requests.exceptions.ConnectionError:
        print("agent closed the connection (long job); waiting on host/last.log ...")
    code = _wait_for_log(started)
    if LOG.exists(): print(LOG.read_text()[-6000:])
    if code is None:
        print("no exit marker in last.log (timed out?)"); return False
    return code == 0 if ok is None else (ok and code == 0)

if __name__ == "__main__":
    sys.exit(0 if run(sys.argv[2]) else 1)
