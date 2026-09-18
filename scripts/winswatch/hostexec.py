"""Run a host job through the Unraid user script 'winswatch'. Usage: python hostexec.py run labels"""
import shutil, sys
from pathlib import Path
import requests

APP = Path("/mnt/nastower/appdata/scripts/winswatch")
TOKEN = Path.home().joinpath(".config/nastower/api_token").read_text().strip()

def run(job: str):
    # Jobs are resolved relative to this file (the repo checkout), so a job committed
    # here deploys identically whether run from the repo or the NFS-mounted server tree.
    src = Path(__file__).parent / "host/jobs" / f"{job}.sh"
    shutil.copy(src, APP / "host/job.sh")
    r = requests.post("http://192.168.0.15:8043/api/v1/user-scripts/winswatch/execute", headers={"Authorization": f"Bearer {TOKEN}"},
                      json={"wait": True}, timeout=1800)
    d = r.json(); print(d.get("output") or d.get("message") or d)
    log = APP / "host/last.log"
    if log.exists(): print(log.read_text()[-6000:])
    return d.get("success", False)

if __name__ == "__main__":
    sys.exit(0 if run(sys.argv[2]) else 1)
