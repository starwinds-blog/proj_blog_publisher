#!/usr/bin/env python3
"""Check and update publication status using GitHub REST API (urllib) and live URL HTTP check.

Replaces `gh` CLI requirement with standard library `urllib.request`.
Never marks a post as `published` unless workflow succeeded (or URL is live HTTP 200).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.pipeline_core import (  # noqa: E402
    load_publications_registry,
    load_publishing_config,
    now_kst_iso,
    save_publications_registry,
)


def check_github_actions_status(owner: str, repo: str, commit_sha: Optional[str] = None) -> Dict[str, Any]:
    """Query GitHub REST API for latest workflow run without requiring gh CLI."""
    if not owner or not repo:
        return {"checked": False, "reason": "github_owner 또는 github_repo 미설정"}

    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs?per_page=5"
    if commit_sha:
        url += f"&head_sha={commit_sha}"

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ai-story-blog-publisher/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            runs = payload.get("workflow_runs") or []
            if not runs:
                return {"checked": True, "found": False, "status": "no_runs_found"}
            latest = runs[0]
            return {
                "checked": True,
                "found": True,
                "run_id": latest.get("id"),
                "name": latest.get("name"),
                "status": latest.get("status"),          # queued, in_progress, completed
                "conclusion": latest.get("conclusion"),  # success, failure, cancelled, etc.
                "html_url": latest.get("html_url"),
                "head_sha": latest.get("head_sha"),
            }
    except urllib.error.HTTPError as exc:
        return {"checked": False, "reason": f"GitHub API HTTP {exc.code}"}
    except Exception as exc:
        return {"checked": False, "reason": f"네트워크/API 조회 실패: {exc}"}


def check_live_url(url: str) -> Dict[str, Any]:
    if not url or "localhost" in url:
        return {"checked": False, "reachable": False, "reason": "로컬 URL이거나 실제 배포 도메인이 미설정됨"}

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ai-story-blog-publisher/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            code = getattr(resp, "status", 200)
            return {"checked": True, "reachable": 200 <= code < 400, "http_status": code}
    except urllib.error.HTTPError as exc:
        return {"checked": True, "reachable": False, "http_status": exc.code, "reason": f"HTTP {exc.code}"}
    except Exception as exc:
        return {"checked": False, "reachable": False, "reason": f"네트워크 연결 실패: {exc}"}


def verify_and_update_status(slug: Optional[str] = None, check_remote: bool = False) -> Dict[str, Any]:
    registry = load_publications_registry()
    pub_cfg = load_publishing_config()
    items = registry.get("items", {})

    targets = [slug] if slug else list(items.keys())
    results: Dict[str, Any] = {}

    for target_slug in targets:
        rec = items.get(target_slug)
        if not rec:
            results[target_slug] = {"found": False, "error": f"'{target_slug}' 발행 이력이 없습니다."}
            continue

        actions_info = {"checked": False}
        url_info = {"checked": False}

        if check_remote:
            owner = str(pub_cfg.get("github_owner") or "").strip()
            repo = str(pub_cfg.get("github_repo") or "").strip()
            actions_info = check_github_actions_status(owner, repo, rec.get("commit_sha"))
            url_info = check_live_url(str(rec.get("url") or ""))

            # State transitions based on honest verification
            if actions_info.get("found") and actions_info.get("status") == "completed":
                if actions_info.get("conclusion") == "failure":
                    rec["status"] = "deploy_failed"
                elif actions_info.get("conclusion") == "success" and url_info.get("reachable"):
                    rec["status"] = "published"
                    rec["published_at"] = now_kst_iso()
            elif url_info.get("reachable"):
                rec["status"] = "published"
                rec["published_at"] = rec.get("published_at") or now_kst_iso()

            rec["last_verified_at"] = now_kst_iso()
            rec["actions_check"] = actions_info
            rec["url_check"] = url_info
            items[target_slug] = rec

        results[target_slug] = {
            "found": True,
            "record": rec,
            "actions_check": actions_info,
            "url_check": url_info,
        }

    if check_remote:
        save_publications_registry(registry)

    return {
        "checked_at": now_kst_iso(),
        "remote_checked": check_remote,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect and verify publication status.")
    parser.add_argument("--slug", default=None, help="Specific post slug (omit to list all)")
    parser.add_argument("--check-remote", action="store_true", help="Query GitHub Actions API and live URL")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    report = verify_and_update_status(slug=args.slug, check_remote=args.check_remote)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print("=== 게시물 발행 이력 및 상태 ===")
    if not report["results"]:
        print("  (등록된 발행 이력이 없습니다)")
        return 0

    for k, val in report["results"].items():
        if not val.get("found"):
            print(f"  * {k}: {val.get('error')}")
            continue
        rec = val["record"]
        print(f"  * [{rec.get('status')}] {k} — {rec.get('title')}")
        print(f"    - URL: {rec.get('url') or '(미지정)'}")
        print(f"    - Commit SHA: {rec.get('commit_sha') or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
