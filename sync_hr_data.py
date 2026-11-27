"""
sync_hr_data.py
===============
Downloads the HR data CSV from a SharePoint "anyone with the link" URL,
converts the live Individual Performance Plan workbook (Google Drive) to ipp_data.json,
saves a review snapshot to ipp_history.json when a Date completed changes, and pushes
both to the GitHub repo using git CLI (handles large files).

The SharePoint export holds both teams. Athletes on the men's roster (roster.json in the
men's dashboard folder, next to this one) go to the men's repo, with a copy of this
index.html; everyone else stays in the women's hr_data.csv.

Requirements:
    pip install -r requirements.txt
    git must be installed and on PATH

Usage:
    Set GITHUB_TOKEN env var (a personal access token with repo write access), then:
        python sync_hr_data.py

Schedule via Windows Task Scheduler or cron.
"""

import csv
import json
import os
import re
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

# Men's dashboard: its own local git repo next to this one. Its roster.json lists who goes there.
MEN_REPO_DIR    = os.path.join(os.path.dirname(REPO_DIR), "men-dashboard")
MEN_GITHUB_REPO = "druskim/men_training_dashboard"
MEN_ROSTER_PATH = "roster.json"
SHARED_PAGE     = "index.html"   # the same dashboard page serves both teams (see config.js)

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


def git(args: list[str], cwd: str = REPO_DIR, **kwargs) -> subprocess.CompletedProcess:
    """Run a git command in a repo folder (default: this one)."""
    result = subprocess.run(["git"] + args, cwd=cwd,
                            capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout.strip()}\n"
            f"stderr: {result.stderr.strip()}"
        )
    return result


def push_via_git(files: dict[str, str], message: str, token: str, repo_name: str,
                 repo_dir: str = REPO_DIR) -> None:
    """Write files ({repo path: text}) into repo_dir and push via git CLI using the token for auth."""
    paths = list(files)
    for path, content in files.items():
        full_path = os.path.join(repo_dir, path)
        with open(full_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        print(f"  Written: {full_path}")

    # Check for changes
    result = subprocess.run(
        ["git", "status", "--porcelain", *paths],
        cwd=repo_dir, capture_output=True, text=True
    )
    if not result.stdout.strip():
        print("  No changes — files are identical to last push.")
        return

    # Temporarily embed token in remote URL for auth, then restore it
    remote_url     = f"https://x-access-token:{token}@github.com/{repo_name}.git"
    clean_url      = f"https://github.com/{repo_name}.git"

    git(["add", *paths], cwd=repo_dir)
    git(["commit", "-m", message], cwd=repo_dir)

    # Detect current branch
    branch = git(["branch", "--show-current"], cwd=repo_dir).stdout.strip() or "main"
    print(f"  Pushing to origin/{branch}...")

    # Embed token in remote URL only for the push, then immediately restore
    git(["remote", "set-url", "origin", remote_url], cwd=repo_dir)
    try:
        git(["push", "origin", branch], cwd=repo_dir)
    except Exception:
        # Undo the commit so the next run retries cleanly
        subprocess.run(["git", "reset", "HEAD~1"], cwd=repo_dir, capture_output=True)
        raise
    finally:
        subprocess.run(["git", "remote", "set-url", "origin", clean_url],
                       cwd=repo_dir, capture_output=True)

    print(f"  Pushed {', '.join(paths)} → {repo_name} ({branch})")


def athlete_key(file_name: str, aliases: dict[str, str]) -> str:
    """'Peter_Parsons.csv' → 'peter parsons', with roster spellings applied (as the dashboard does)."""
    name = re.sub(r"\.csv$", "", file_name.strip(), flags=re.I).replace("_", " ").lower().strip()
    return aliases.get(name, name)


def load_men_roster() -> tuple[set[str], dict[str, str]] | None:
    """Normalised names and aliases from the men's roster.json, or None if it isn't set up."""
    path = os.path.join(MEN_REPO_DIR, MEN_ROSTER_PATH)
    if not os.path.exists(path):
        print(f"  WARNING: no men's roster at {path} — all HR data stays in the women's repo")
        return None
    with open(path, encoding="utf-8") as f:
        roster = json.load(f)
    aliases = {k.lower().strip(): v.lower().strip() for k, v in roster.get("aliases", {}).items()}
    names = {aliases.get(n.lower().strip(), n.lower().strip()) for n in roster["athletes"]}
    return names, aliases


def split_hr_csv(csv_text: str, men: set[str], aliases: dict[str, str]) -> tuple[str, str]:
    """(women's CSV, men's CSV), split by the athlete in file_name; both keep the header.
    Lines are copied unchanged, so the women's file only loses the men's rows."""
    lines = csv_text.splitlines(keepends=True)
    if not lines:
        return csv_text, ""
    col = next(csv.reader([lines[0]])).index("file_name")
    women, men_lines = [lines[0]], [lines[0]]
    for line in lines[1:]:
        fields = next(csv.reader([line]), [])
        is_man = len(fields) > col and athlete_key(fields[col], aliases) in men
        (men_lines if is_man else women).append(line)
    return "".join(women), "".join(men_lines)


def sync_men(men_csv: str) -> None:
    """Push the men's HR rows and the shared dashboard page to the men's repo."""
    with open(os.path.join(REPO_DIR, SHARED_PAGE), encoding="utf-8", newline="") as f:
        page = f.read()
    push_via_git({CSV_PATH: men_csv, SHARED_PAGE: page}, "chore: auto-sync HR data from SharePoint",
                 GITHUB_TOKEN, MEN_GITHUB_REPO, MEN_REPO_DIR)


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

    print("Step 3 — Splitting women's and men's rows...")
    roster = load_men_roster()
    men_csv = None
    if roster:
        csv_text, men_csv = split_hr_csv(csv_text, *roster)
        print(f"  Women: {csv_text.count(chr(10)) - 1:,} rows · Men: {men_csv.count(chr(10)) - 1:,} rows")

    print("Step 4 — Converting IPP workbook...")
    files = {CSV_PATH: csv_text, **load_ipp_files()}

    print("Step 5 — Pushing women's dashboard to GitHub via git...")
    push_via_git(files, COMMIT_MESSAGE, GITHUB_TOKEN, GITHUB_REPO)

    if men_csv is not None:
        print("Step 6 — Pushing men's dashboard to GitHub via git...")
        sync_men(men_csv)

    print("Done.")


if __name__ == "__main__":
    main()
