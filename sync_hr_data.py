"""
sync_hr_data.py
===============
Downloads the HR data CSV from a SharePoint "anyone with the link" URL
and pushes it to the GitHub repo using git CLI (handles large files).

Requirements:
    pip install requests
    git must be installed and on PATH

Usage:
    Set GITHUB_TOKEN env var (a personal access token with repo write access), then:
        python sync_hr_data.py

Schedule via Windows Task Scheduler or cron.
"""

import os
import subprocess

import requests

# ── Configuration ─────────────────────────────────────────────────────────────

SHAREPOINT_URL = (
    "https://canadiansportinstit-my.sharepoint.com/:x:/g/personal/"
    "sportlab_csiontario_ca/IQDLcEm2AgpMRbbeO6qx9szCAUwZS3sio6QbyxiNfeD-2Cs"
    "?e=9ga0rl"
)

GITHUB_REPO    = "druskim/women_training_dashboard"
CSV_PATH       = "hr_data.csv"   # path inside the repo
COMMIT_MESSAGE = "chore: auto-sync HR data from SharePoint"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Directory containing this script (= root of the git repo)
REPO_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Helpers ───────────────────────────────────────────────────────────────────

def download_sharepoint_file(sharing_url: str) -> bytes:
    """Downloads a SharePoint 'anyone with the link' file via &download=1."""
    url = sharing_url + "&download=1"
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


def push_via_git(csv_content: str, path: str, message: str, token: str, repo_name: str) -> None:
    """Write file locally and push via git CLI using the token for auth."""
    # Write the CSV
    full_path = os.path.join(REPO_DIR, path)
    with open(full_path, "w", encoding="utf-8", newline="") as f:
        f.write(csv_content)
    print(f"  Written: {full_path}")

    # Check for changes
    result = subprocess.run(
        ["git", "status", "--porcelain", path],
        cwd=REPO_DIR, capture_output=True, text=True
    )
    if not result.stdout.strip():
        print("  No changes — file is identical to last push.")
        return

    # Temporarily embed token in remote URL for auth, then restore it
    remote_url     = f"https://x-access-token:{token}@github.com/{repo_name}.git"
    clean_url      = f"https://github.com/{repo_name}.git"

    git(["add", path])
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

    print(f"  Pushed '{path}' → {repo_name} ({branch})")


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

    print("Step 3 — Pushing to GitHub via git...")
    push_via_git(csv_text, CSV_PATH, COMMIT_MESSAGE, GITHUB_TOKEN, GITHUB_REPO)

    print("Done.")


if __name__ == "__main__":
    main()
