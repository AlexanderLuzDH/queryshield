#!/usr/bin/env python3
import io
import json
import os
import sys
import zipfile
from datetime import datetime

import requests


def log(msg):
    print(f"[commit_artifacts] {msg}")


def download_artifact(session, url):
    r = session.get(url)
    r.raise_for_status()
    return io.BytesIO(r.content)


def extract_first_matching(zb, suffix):
    with zipfile.ZipFile(zb) as z:
        for name in z.namelist():
            if name.endswith(suffix):
                with z.open(name) as f:
                    return f.read()
    return None


def main():
    if os.environ.get("CI") != "true":
        log("Not in CI; skipping")
        return 0
    if os.environ.get("PUBLISH_EVIDENCE", "").lower() not in ("1", "true", "yes"):
        log("PUBLISH_EVIDENCE is not enabled; skipping")
        return 0
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if not token or not repo or not run_id:
        log("Missing GITHUB_TOKEN/GITHUB_REPOSITORY/GITHUB_RUN_ID")
        return 1
    owner, name = repo.split("/")
    api = f"https://api.github.com/repos/{owner}/{name}/actions/runs/{run_id}/artifacts"
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    resp = s.get(api)
    resp.raise_for_status()
    arts = resp.json().get("artifacts", [])
    if not arts:
        log("No artifacts found")
        return 1
    # Map by name
    def pick(name):
        items = [a for a in arts if a.get("name") == name]
        if not items:
            return None
        # pick latest
        items.sort(key=lambda a: a.get("updated_at", ""))
        return items[-1]

    before = pick("queryshield-report-failing")
    after = pick("queryshield-report-passing")
    ddl = pick("ddl-suggestions.txt")

    outdir = os.path.join("queryshield", "sample-django-app", ".queryshield")
    os.makedirs(outdir, exist_ok=True)

    changed = False
    if before:
        zb = download_artifact(s, before.get("archive_download_url"))
        data = extract_first_matching(zb, "queryshield_report.json")
        if data:
            path = os.path.join(outdir, "before.json")
            if not os.path.exists(path) or open(path, "rb").read() != data:
                open(path, "wb").write(data)
                changed = True
                log(f"Wrote {path}")
    if after:
        zb = download_artifact(s, after.get("archive_download_url"))
        data = extract_first_matching(zb, "queryshield_report.json")
        if data:
            path = os.path.join(outdir, "after.json")
            if not os.path.exists(path) or open(path, "rb").read() != data:
                open(path, "wb").write(data)
                changed = True
                log(f"Wrote {path}")
    if ddl:
        zb = download_artifact(s, ddl.get("archive_download_url"))
        data = extract_first_matching(zb, "ddl-suggestions.txt")
        if data:
            path = os.path.join(outdir, "ddl-suggestions.txt")
            if not os.path.exists(path) or open(path, "rb").read() != data:
                open(path, "wb").write(data)
                changed = True
                log(f"Wrote {path}")

    if not changed:
        log("No changes to commit")
        return 0

    # Commit and push
    def sh(cmd):
        from subprocess import check_call
        check_call(cmd, shell=True)

    sh("git config user.name 'github-actions[bot]'")
    sh("git config user.email 'github-actions[bot]@users.noreply.github.com'")
    sh(f"git add {outdir}")
    sh("git commit -m 'chore: commit CI artifacts (before/after/ddl)' || echo 'nothing to commit'")
    sh("git push")
    log("Committed and pushed artifacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())

