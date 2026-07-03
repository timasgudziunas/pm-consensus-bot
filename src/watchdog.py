"""Paper-trading watchdog: restart paper.py if its process has died.

Runs as a Windows scheduled task every few minutes (see README note in
data/logs/watchdog.log after first run), so paper trading survives crashes,
reboots into a logged-in session, and Claude sessions ending. It reads the PID
paper.py writes to data/logs/paper.pid, verifies a python process with that
PID is alive via tasklist, and relaunches paper.py detached if not — logging
the last stderr lines first so crash evidence is never lost.

This never touches live trading; it only supervises the paper loop.

Run: python src/watchdog.py   (normally via Task Scheduler, task
     "pm-copybot-paper-watchdog")
"""
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(REPO_ROOT, "data", "logs")
PID_FILE = os.path.join(LOGS_DIR, "paper.pid")
WATCHDOG_LOG = os.path.join(LOGS_DIR, "watchdog.log")
STDERR_LOG = os.path.join(LOGS_DIR, "paper_stderr.log")
STDOUT_LOG = os.path.join(LOGS_DIR, "paper_stdout.log")

DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000


def wlog(msg: str) -> None:
    """Append a timestamped line to the watchdog log."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}Z {msg}\n")


def paper_alive() -> bool:
    """True if the PID recorded in paper.pid is a live python process."""
    try:
        with open(PID_FILE, encoding="utf-8") as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return False
    # tasklist instead of os.kill: on Windows, os.kill(pid, 0) TERMINATES the
    # target (TerminateProcess), it is not a liveness probe
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True)
    return f'"{pid}"' in out.stdout and "python" in out.stdout.lower()


def capture_crash_evidence() -> None:
    """Log the tail of paper's stderr so the crash cause survives the restart."""
    try:
        with open(STDERR_LOG, encoding="utf-8", errors="replace") as f:
            tail = [ln.rstrip() for ln in f.readlines()[-15:] if ln.strip()]
        if tail:
            wlog("last stderr before restart: " + " | ".join(tail[-5:]))
    except OSError:
        pass


def restart_paper() -> None:
    """Relaunch paper.py detached, appending to its standard logs."""
    with open(STDOUT_LOG, "a", encoding="utf-8") as out, \
         open(STDERR_LOG, "a", encoding="utf-8") as err:
        p = subprocess.Popen([sys.executable, os.path.join(REPO_ROOT, "src", "paper.py")],
                             cwd=REPO_ROOT, stdout=out, stderr=err,
                             creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW)
    wlog(f"paper.py was DOWN — restarted as PID {p.pid}")


def main() -> None:
    """One check-and-restart cycle (scheduled task fires this repeatedly)."""
    if paper_alive():
        return
    capture_crash_evidence()
    restart_paper()


if __name__ == "__main__":
    main()
