"""Unattended start for Fri 13 Nov 2026, run by Windows Task Scheduler at 19:47 IST (after the 19:45 kickoff).

1. Start the first cloud run (gpt-oss) on GitHub Actions.
2. Run the Llama arm locally (Ollama), keeping the laptop awake while it runs.
3. Commit and push the Llama data so the cloud runner labels its titles.
Everything is written to logs/start_tonight.log. Safe to run twice: collection resumes and skips finished calls.
"""
import ctypes
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "start_tonight.log"
GIT = r"C:\Users\harsh sawant\AppData\Local\Programs\Git\cmd\git.exe"
GH = r"C:\Program Files\GitHub CLI\gh.exe"
REPO = "harshnsawant-source/apart-epistemics-2026"


def log(msg):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")


def sh(args, timeout=None):
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout)
    log(f"$ {' '.join(map(str, args))} -> exit {r.returncode}")
    for line in (r.stdout + r.stderr).strip().splitlines()[-25:]:
        log(f"    {line}")
    return r.returncode


def ollama_up():
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=10):
            return True
    except Exception:
        return False


def main():
    log("=== start ===")
    # Keep the PC awake while this script runs (an application request; no settings are changed).
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)

    sh([GH, "workflow", "run", "collect.yml", "--repo", REPO], timeout=120)

    if not ollama_up():
        log("Ollama not responding; trying to start it")
        subprocess.Popen(["ollama", "serve"], cwd=ROOT, creationflags=0x08000000)
        for _ in range(30):
            time.sleep(5)
            if ollama_up():
                break
    if not ollama_up():
        log("Ollama still not responding; Llama arm NOT run. Run it by hand: python src/run.py --arm llama --minutes 240 --no-verify")
    else:
        sh([sys.executable, "src/run.py", "--arm", "llama", "--minutes", "240", "--no-verify"], timeout=5 * 3600)

    sh([GIT, "add", "raw/generations_llama.jsonl", "raw/generations_llama_attempts.jsonl"])
    if sh([GIT, "diff", "--cached", "--quiet"]) != 0:
        sh([GIT, "-c", "user.name=Harsh Sawant", "-c", "user.email=281931449+harshnsawant-source@users.noreply.github.com", "commit", "-m",
            "collect: Llama arm (laptop, Ollama)\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
            "Claude-Session: https://claude.ai/code/session_01XsfVaNDvdkvWdsH8iuCgyB"])
        for _ in range(3):
            if sh([GIT, "pull", "--rebase"], timeout=300) == 0 and sh([GIT, "push"], timeout=300) == 0:
                break
            time.sleep(30)
    log("=== DONE ===")
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FAILED: {e!r}")
        log("=== DONE ===")
        raise
