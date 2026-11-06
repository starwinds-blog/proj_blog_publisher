#!/usr/bin/env python3
"""Check local environment tools, Git remotes, and publishing readiness."""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.pipeline_core import (  # noqa: E402
    PROJECT_ROOT,
    SITE_DIR,
    ensure_directories,
    load_publishing_config,
    now_kst_iso,
)


def _run_cmd(cmd: list[str], cwd: Path = PROJECT_ROOT) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = (proc.stdout or proc.stderr or "").strip()
        return proc.returncode, out
    except FileNotFoundError:
        return 127, "not installed"
    except Exception as exc:
        return 1, str(exc)


def _check_binary(name: str, version_arg: str = "--version", required: bool = True) -> Dict[str, Any]:
    path = shutil.which(name) or (str(Path.home() / ".local" / "bin" / name) if (Path.home() / ".local" / "bin" / name).exists() else None)
    if not path:
        return {
            "name": name,
            "installed": False,
            "required": required,
            "path": None,
            "version": None,
        }
    code, out = _run_cmd([name, version_arg])
    first_line = out.splitlines()[0] if out else ""
    return {
        "name": name,
        "installed": code == 0,
        "required": required,
        "path": path,
        "version": first_line,
    }


def collect_env_status() -> Dict[str, Any]:
    ensure_directories()
    pub_cfg = load_publishing_config()

    tools = {
        "python": {
            "name": "python3",
            "installed": True,
            "required": True,
            "path": sys.executable,
            "version": f"Python {platform.python_version()}",
        },
        "git": _check_binary("git", "--version", required=True),
        "hugo": _check_binary("hugo", "version", required=False),  # Recommended for local build/preview
        "codex": _check_binary("codex", "--version", required=False),
        "gh": _check_binary("gh", "--version", required=False),  # Optional; replaced by git + urllib
        "node": _check_binary("node", "--version", required=False),
    }

    _, git_remotes = _run_cmd(["git", "remote", "-v"], cwd=PROJECT_ROOT)
    _, git_branch = _run_cmd(["git", "branch", "--show-current"], cwd=PROJECT_ROOT)

    site_is_separate_git = (SITE_DIR / ".git").exists()
    site_hugo_toml = (SITE_DIR / "hugo.toml").exists()
    site_workflow = (SITE_DIR / ".github" / "workflows" / "hugo.yml").exists() or (
        PROJECT_ROOT / ".github" / "workflows" / "hugo.yml"
    ).exists()

    gh_owner = str(pub_cfg.get("github_owner") or "").strip()
    gh_repo = str(pub_cfg.get("github_repo") or "").strip()
    remote_configured = bool(gh_owner and gh_repo)

    blockers: list[str] = []
    warnings: list[str] = []

    if not tools["git"]["installed"]:
        blockers.append("git CLI가 설치되어 있지 않습니다.")
    if not tools["hugo"]["installed"]:
        warnings.append(
            "hugo CLI가 설치되어 있지 않습니다. 로컬 초안 편집·검증·승인 및 대시보드 미리보기는 즉시 가능하며, "
            "로컬 정적 사이트 빌드 테스트 시 hugo 설치가 권장됩니다 (GitHub Actions 배포 시에는 CI에서 Hugo가 실행됩니다)."
        )
    if not remote_configured:
        warnings.append(
            "공개 배포 대상 GitHub 계정(github_owner) 및 저장소(github_repo)가 아직 미설정 상태입니다. "
            "현재는 안전한 로컬/dry-run 모드로 동작합니다."
        )

    return {
        "checked_at": now_kst_iso(),
        "os": f"{platform.system()} {platform.release()}",
        "project_root": str(PROJECT_ROOT),
        "tools": tools,
        "git": {
            "branch": git_branch or "main",
            "remotes": git_remotes.splitlines() if git_remotes else [],
            "site_is_separate_git": site_is_separate_git,
        },
        "site": {
            "hugo_toml_exists": site_hugo_toml,
            "workflow_exists": site_workflow,
            "github_owner": gh_owner,
            "github_repo": gh_repo,
            "repo_type": pub_cfg.get("repo_type", "user"),
            "base_url": pub_cfg.get("base_url", "http://localhost:1313/"),
            "remote_configured": remote_configured,
        },
        "ready_for_local_mvp": len(blockers) == 0,
        "ready_for_public_publish": len(blockers) == 0 and remote_configured,
        "blockers": blockers,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check AI Story-to-Blog Publisher environment.")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    status = collect_env_status()
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0 if status["ready_for_local_mvp"] else 1

    print("=== AI Story-to-Blog Publisher 환경 점검 ===")
    print(f"- 시각: {status['checked_at']}")
    print(f"- OS: {status['os']}")
    print(f"- 작업 경로: {status['project_root']}")
    print("\n[도구 상태]")
    for key, info in status["tools"].items():
        badge = "OK" if info["installed"] else ("MISSING(필수)" if info["required"] else "OPTIONAL(미설치)")
        ver = info["version"] or "-"
        print(f"  * {key:8s}: {badge:16s} | {ver}")

    print("\n[Hugo & 배포 설정]")
    print(f"  * site/hugo.toml 존재: {status['site']['hugo_toml_exists']}")
    print(f"  * GitHub Actions workflow 존재: {status['site']['workflow_exists']}")
    print(f"  * 설정된 GitHub 저장소: {status['site']['github_owner'] or '(미설정)'}/{status['site']['github_repo'] or '(미설정)'}")
    print(f"  * 로컬 MVP 준비 완료: {status['ready_for_local_mvp']}")
    print(f"  * 원격 공개 배포 준비 완료: {status['ready_for_public_publish']}")

    if status["warnings"]:
        print("\n[참고/주의 사항]")
        for w in status["warnings"]:
            print(f"  - {w}")
    if status["blockers"]:
        print("\n[Blocker]")
        for b in status["blockers"]:
            print(f"  ! {b}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
