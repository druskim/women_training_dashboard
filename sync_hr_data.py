"""
sync_hr_data.py
===============
Downloads the HR data CSV from a SharePoint "anyone with the link" URL,
converts the live Individual Performance Plan workbook (Google Drive) to ipp_data.json,
saves a review snapshot to ipp_history.json when a Date completed changes, and pushes
both to the GitHub repo using git CLI (handles large files).

Requirements:
    pip install -r requirements.txt
    git must be installed and on PATH

Usage:
    Set GITHUB_TOKEN env var (a personal access token with repo write access), then:
        python sync_hr_data.py

Schedule via Windows Task Scheduler or cron.
"""

import json
import os
import subprocess
from datetime import date

import requests

from ipp_to_json import (DEFAULT_XLSX, HISTORY_PATH as IPP_HISTORY_PATH, JSON_PATH as IPP_JSON_PATH,
                         to_json_text, update_history, workbook_to_data)

# ── Configuration ─────────────────────────────────────────────────────────────

SHAREPOINT_URL = (
    "https://canadiansportinstit-my.sharepoint.com/:x:/g/personal/"
    "sportlab_csiontario_ca/IQB1_y2eJFB0QJlSsO97QZpTASzsNL1Ex3Lxyld7EYEvsHU"
    "?e=cKQ4A5"
)

# IPP workbook: the live copy on Google Drive (same file the dashboard reads, see config.js).
# If it can't be downloaded, the local copy next to this script is used instead.
IPP_DRIVE_URL  = ("https://docs.google.com/spreadsheets/d/"
                  "1y_RA5llgTHyxk_ICyMNAp816ew44T-vJ/export?format=xlsx")
IPP_LOCAL_PATH = DEFAULT_XLSX

GITHUB_REPO    = "druskim/women_training_dashboard"
CSV_PATH       = "hr_data.csv"   # path inside the repo
COMMIT_MESSAGE = "chore: auto-sync HR data and IPPs from SharePoint"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Directory containing this script (= root of the git repo)
REPO_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Helpers ───────────────────────────────────────────────────────────────────

def download_sharepoint_file(sharing_url: str) -> bytes:
    """Downloads a SharePoint 'anyone with the link' file via &download=1."""
    sep = "&" if "?" in sharing_url else "?"
    url = sharing_url + sep + "download=1"
    print(f"  Fetching: {url}")
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"},
                        allow_redirects=True, timeout=120)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")
    print(f"  Content-Type: {content_type}")
    print(f"  Downloaded {len(resp.content):,} bytes")

    if "text/html" in content_type or resp.content[:5] in (b"<!DOC", b"<html"):
        raise ValueError(
            "SharePoint returned an HTML page instead of the file.\n"
            "The sharing token may have expired — generate a new link.\n"
            f"Preview: {resp.text[:300]}"
        )
    return resp.content


def to_csv_text(content: bytes) -> str:
    """Return content as a UTF-8 string. Already a CSV, so just decode."""
    print("  Detected format: CSV")
    return content.decode("utf-8-sig")  # strips BOM if present


def git(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a git command in REPO_DIR."""
    result = subprocess.run(["git"] + args, cwd=REPO_DIR,
                            capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout.strip()}\n"
            f"stderr: {result.stderr.strip()}"
        )
    return result


def push_via_git(files: dict[str, str], message: str, token: str, repo_name: str) -> None:
    """Write files ({repo path: text}) locally and push via git CLI using the token for auth."""
    paths = list(files)
    for path, content in files.items():
        full_path = os.path.join(REPO_DIR, path)
        with open(full_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        print(f"  Written: {full_path}")

    # Check for changes
    result = subprocess.run(
        ["git", "status", "--porcelain", *paths],
        cwd=REPO_DIR, capture_output=True, text=True
    )
    if not result.stdout.strip():
        print("  No changes — files are identical to last push.")
        return

    # Temporarily embed token in remote URL for auth, then restore it
    remote_url     = f"https://x-access-token:{token}@github.com/{repo_name}.git"
    clean_url      = f"https://github.com/{repo_name}.git"

    git(["add", *paths])
    git(["commit", "-m", message])

    # Detect current branch
    branch = git(["branch", "--show-current"]).stdout.strip() or "main"
    print(f"  Pushing to origin/{branch}...")

    # Embed token in remote URL only for the push, then immediately restore
    git(["remote", "set-url", "origin", remote_url])
    try:
        git(["push", "origin", branch])
    except Exception:
        # Undo the commit so the next run retries cleanly
        subprocess.run(["git", "reset", "HEAD~1"], cwd=REPO_DIR, capture_output=True)
        raise
    finally:
        subprocess.run(["git", "remote", "set-url", "origin", clean_url],
                       cwd=REPO_DIR, capture_output=True)

    print(f"  Pushed {', '.join(paths)} → {repo_name} ({branch})")


def download_ipp_workbook() -> bytes:
    """The live IPP workbook from Google Drive, or the local copy if Drive can't be reached."""
    try:
        print(f"  Fetching: {IPP_DRIVE_URL}")
        resp = requests.get(IPP_DRIVE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
        resp.raise_for_status()
        if resp.content[:2] != b"PK":  # .xlsx files are zip archives
            raise ValueError("Drive returned a web page instead of the workbook (check its sharing)")
        return resp.content
    except Exception as e:
        path = os.path.join(REPO_DIR, IPP_LOCAL_PATH)
        print(f"  WARNING: Drive download failed ({e}) — reading local file {path}")
        with open(path, "rb") as f:
            return f.read()


def load_ipp_files() -> dict[str, str]:
    """ipp_data.json, plus ipp_history.json when a review has a new Date completed.
    Returns {} on failure so the HR sync still goes ahead (the dashboard keeps the last plans)."""
    try:
        data = workbook_to_data(download_ipp_workbook())
        filled = sum(a["hasContent"] for a in data["athletes"])
        print(f"  {len(data['athletes'])} athletes on roster ({filled} with plan content)")
        files = {IPP_JSON_PATH: to_json_text(data)}

        history_file = os.path.join(REPO_DIR, IPP_HISTORY_PATH)
        history = None
        if os.path.exists(history_file):
            with open(history_file, encoding="utf-8") as f:
                history = json.load(f)
        history, added = update_history(history, data, date.today().isoformat())
        if added:
            print(f"  New review snapshots: {', '.join(added)}")
            files[IPP_HISTORY_PATH] = to_json_text(history)
        else:
            print("  No new Date completed — plan history unchanged")
        return files
    except Exception as e:
        print(f"  WARNING: skipping IPP sync — {e}")
        return {}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not GITHUB_TOKEN:
        raise EnvironmentError(
            "GITHUB_TOKEN is not set.\n"
            "Create a classic PAT with 'repo' scope at https://github.com/settings/tokens/new\n"
            "Then run:  $env:GITHUB_TOKEN = 'ghp_...'"
        )

    print("Step 1 — Downloading from SharePoint...")
    raw = download_sharepoint_file(SHAREPOINT_URL)

    print("Step 2 — Preparing CSV...")
    csv_text = to_csv_text(raw)
    print(f"  {csv_text.count(chr(10)):,} rows")

    print("Step 3 — Converting IPP workbook...")
    files = {CSV_PATH: csv_text, **load_ipp_files()}

    print("Step 4 — Pushing to GitHub via git...")
    push_via_git(files, COMMIT_MESSAGE, GITHUB_TOKEN, GITHUB_REPO)

    print("Done.")


if __name__ == "__main__":
    main()
