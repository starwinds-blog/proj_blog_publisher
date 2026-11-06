#!/usr/bin/env python3
"""Prepare and execute blog post publication with explicit approval and allowlist safety.

Workflow:
1. Validate draft or approved post (blocks on secrets, broken front matter, missing images).
2. If --approve is passed, set draft: false and save to stories/approved/<slug>.md.
3. Copy ONLY approved post into site/content/posts/<slug>.md (checks duplicate slug unless --upsert).
4. Run local `hugo --minify` build check if hugo is installed.
5. If --publish and --confirm-public-push (and not --dry-run), commit & git push to configured remote.
6. Update stories/records/publications.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.pipeline_core import (  # noqa: E402
    APPROVED_DIR,
    DRAFTS_DIR,
    PROJECT_ROOT,
    RAW_DIR,
    SITE_DIR,
    SITE_POSTS_DIR,
    build_markdown_post,
    ensure_directories,
    load_publications_registry,
    load_publishing_config,
    now_kst_iso,
    parse_front_matter,
    save_publications_registry,
)
from scripts.validate_post import validate_markdown_file  # noqa: E402


def _compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resolve_raw_file(slug: str) -> Optional[Path]:
    review_file = DRAFTS_DIR / f"{slug}.review.json"
    if review_file.exists():
        try:
            review_data = json.loads(review_file.read_text(encoding="utf-8"))
            raw_rel = review_data.get("raw_file")
            if raw_rel:
                candidate = PROJECT_ROOT / raw_rel
                if candidate.exists():
                    return candidate
        except Exception:
            pass
    for ext in (".md", ".txt"):
        candidate = RAW_DIR / f"{slug}{ext}"
        if candidate.exists():
            return candidate
    return None


def _build_expected_url(slug: str, pub_cfg: Dict[str, Any]) -> str:
    base_url = str(pub_cfg.get("base_url") or "").strip().rstrip("/")
    gh_owner = str(pub_cfg.get("github_owner") or "").strip()
    gh_repo = str(pub_cfg.get("github_repo") or "").strip()
    repo_type = str(pub_cfg.get("repo_type") or "user").strip()

    if (not base_url or "localhost" in base_url) and gh_owner:
        if repo_type == "project" and gh_repo and gh_repo != f"{gh_owner}.github.io":
            base_url = f"https://{gh_owner}.github.io/{gh_repo}"
        else:
            base_url = f"https://{gh_owner}.github.io"
    if not base_url:
        base_url = "http://localhost:1313"
    return f"{base_url}/posts/{slug}/"


def approve_post(slug: str) -> Dict[str, Any]:
    """Promote stories/drafts/<slug>.md -> stories/approved/<slug>.md with draft: false."""
    ensure_directories()
    draft_path = DRAFTS_DIR / f"{slug}.md"
    approved_path = APPROVED_DIR / f"{slug}.md"
    source_path = draft_path if draft_path.exists() else approved_path

    if not source_path.exists():
        return {
            "ok": False,
            "slug": slug,
            "error": f"초안 파일을 찾을 수 없습니다: stories/drafts/{slug}.md",
        }

    raw_path = _resolve_raw_file(slug)
    validation = validate_markdown_file(source_path, raw_path)
    if not validation["valid"]:
        return {
            "ok": False,
            "slug": slug,
            "error": "품질/보안 검증을 통과하지 못해 승인할 수 없습니다.",
            "validation": validation,
        }

    text = source_path.read_text(encoding="utf-8")
    meta, body, _ = parse_front_matter(text)
    meta["draft"] = False
    meta["slug"] = slug

    approved_text = build_markdown_post(meta, body)
    approved_path.write_text(approved_text, encoding="utf-8")

    # Also update draft file's draft flag to keep in sync
    if draft_path.exists():
        draft_path.write_text(approved_text, encoding="utf-8")

    registry = load_publications_registry()
    existing = registry["items"].get(slug, {})
    registry["items"][slug] = {
        **existing,
        "slug": slug,
        "title": meta.get("title", slug),
        "raw_file": str(raw_path.relative_to(PROJECT_ROOT)) if raw_path else existing.get("raw_file"),
        "draft_file": f"stories/drafts/{slug}.md",
        "approved_file": f"stories/approved/{slug}.md",
        "status": "approved",
        "approved_at": now_kst_iso(),
        "content_sha256": _compute_sha256(approved_text),
    }
    save_publications_registry(registry)

    return {
        "ok": True,
        "slug": slug,
        "status": "approved",
        "approved_file": f"stories/approved/{slug}.md",
        "validation": validation,
    }


def prepare_and_publish(
    slug: str,
    approve: bool = False,
    dry_run: bool = True,
    upsert: bool = False,
    publish_remote: bool = False,
    confirm_public_push: bool = False,
) -> Dict[str, Any]:
    """Stage approved post to site/content/posts/, run local Hugo check, and optionally git push."""
    ensure_directories()
    pub_cfg = load_publishing_config()
    logs: list[str] = []

    if approve:
        app_res = approve_post(slug)
        if not app_res["ok"]:
            return app_res
        logs.append(f"[APPROVE] '{slug}' 게시물이 승인되었습니다 (stories/approved/{slug}.md).")

    approved_path = APPROVED_DIR / f"{slug}.md"
    if not approved_path.exists():
        return {
            "ok": False,
            "slug": slug,
            "error": (
                f"승인된 게시물이 없습니다(stories/approved/{slug}.md). "
                "먼저 검토 게이트에서 승인(--approve)을 수행하세요."
            ),
            "logs": logs,
        }

    raw_path = _resolve_raw_file(slug)
    validation = validate_markdown_file(approved_path, raw_path)
    if not validation["valid"]:
        return {
            "ok": False,
            "slug": slug,
            "error": "승인본 검증 실패로 발행이 차단되었습니다.",
            "validation": validation,
            "logs": logs,
        }

    approved_text = approved_path.read_text(encoding="utf-8")
    content_hash = _compute_sha256(approved_text)
    meta, _, _ = parse_front_matter(approved_text)

    target_site_post = SITE_POSTS_DIR / f"{slug}.md"
    registry = load_publications_registry()
    existing_rec = registry["items"].get(slug, {})
    commit_sha: Optional[str] = existing_rec.get("commit_sha")
    if (SITE_DIR / ".git").exists():
        head_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(SITE_DIR),
            capture_output=True,
            text=True,
        )
        if head_proc.returncode == 0 and head_proc.stdout.strip():
            commit_sha = head_proc.stdout.strip()

    # Duplicate / idempotency check
    if target_site_post.exists():
        existing_site_hash = _compute_sha256(target_site_post.read_text(encoding="utf-8"))
        if existing_site_hash == content_hash and not publish_remote and not dry_run:
            expected_url = _build_expected_url(slug, pub_cfg)
            registry["items"][slug] = {
                **existing_rec,
                "slug": slug,
                "title": meta.get("title", slug),
                "site_file": f"site/content/posts/{slug}.md",
                "commit_sha": commit_sha,
                "url": expected_url,
                "updated_at": now_kst_iso(),
            }
            save_publications_registry(registry)
            logs.append(f"[SKIP] 동일한 내용의 게시물이 이미 site/content/posts/{slug}.md에 반영되어 있습니다(중복 스테이징 생략, URL 갱신 완료).")
            return {
                "ok": True,
                "slug": slug,
                "status": existing_rec.get("status", "staged"),
                "dry_run": dry_run,
                "duplicate_skipped": True,
                "site_post": f"site/content/posts/{slug}.md",
                "expected_url": expected_url,
                "logs": logs,
            }
        if existing_site_hash != content_hash and not upsert:
            return {
                "ok": False,
                "slug": slug,
                "error": (
                    f"동일한 slug('{slug}')의 게시물이 이미 site/content/posts/{slug}.md에 존재하며 내용이 다릅니다. "
                    "수정 발행하려면 --upsert 옵션을 지정하세요."
                ),
                "logs": logs,
            }

    if dry_run:
        logs.append(f"[DRY-RUN] allowlist 복사 시뮬레이션: stories/approved/{slug}.md -> site/content/posts/{slug}.md")
    else:
        target_site_post.write_text(approved_text, encoding="utf-8")
        logs.append(f"[STAGE] allowlist 복사 완료: site/content/posts/{slug}.md")

    # Local Hugo build test if hugo binary is available
    hugo_bin = shutil.which("hugo") or (
        str(Path.home() / ".local" / "bin" / "hugo")
        if (Path.home() / ".local" / "bin" / "hugo").exists()
        else None
    )
    hugo_build_ok: Optional[bool] = None
    if hugo_bin:
        cmd = [hugo_bin, "--minify", "--source", str(SITE_DIR)]
        if dry_run:
            cmd.extend(["--buildDrafts"])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        hugo_build_ok = proc.returncode == 0
        if not hugo_build_ok:
            err_out = (proc.stderr or proc.stdout or "").strip()
            logs.append(f"[HUGO BUILD FAIL] {err_out}")
            return {
                "ok": False,
                "slug": slug,
                "error": f"로컬 Hugo 빌드에 실패했습니다: {err_out[:300]}",
                "logs": logs,
            }
        logs.append("[HUGO BUILD] hugo --minify 로컬 정적 빌드 검증 성공.")
    else:
        logs.append("[HUGO BUILD] 로컬 hugo CLI 미설치 — 정적 문법/Front Matter 검증으로 대체됨 (GitHub Actions에서 Hugo 빌드 수행).")

    expected_url = _build_expected_url(slug, pub_cfg)
    final_status = existing_rec.get("status", "approved")

    if not dry_run:
        final_status = "staged"

    # Optional Git commit & remote push
    if publish_remote:
        if dry_run:
            logs.append("[DRY-RUN] 원격 Git Push가 요청되었으나 --dry-run 모드이므로 실제 push를 수행하지 않았습니다.")
        else:
            if not confirm_public_push:
                return {
                    "ok": False,
                    "slug": slug,
                    "error": "공개 저장소 배포를 위해서는 명시적 승인 플래그(--confirm-public-push)가 필요합니다.",
                    "logs": logs,
                }
            gh_owner = str(pub_cfg.get("github_owner") or "").strip()
            gh_repo = str(pub_cfg.get("github_repo") or "").strip()
            if not gh_owner or not gh_repo:
                return {
                    "ok": False,
                    "slug": slug,
                    "error": " 배포 설정(config/publishing.yaml)에 github_owner 및 github_repo가 설정되지 않았습니다.",
                    "logs": logs,
                }

            git_cwd = SITE_DIR if (SITE_DIR / ".git").exists() else PROJECT_ROOT
            # Ensure git author is not 'github-actions@github.com', which GitHub suppresses from triggering workflows
            email_proc = subprocess.run(
                ["git", "config", "user.email"],
                cwd=str(git_cwd),
                capture_output=True,
                text=True,
            )
            if "github-actions" in (email_proc.stdout or "").lower():
                subprocess.run(
                    ["git", "config", "user.name", gh_owner],
                    cwd=str(git_cwd),
                    check=False,
                )
                subprocess.run(
                    ["git", "config", "user.email", f"{gh_owner}@users.noreply.github.com"],
                    cwd=str(git_cwd),
                    check=False,
                )

            if git_cwd == SITE_DIR:
                # Stage base Hugo scaffold files (hugo.toml, layouts, workflow) + approved post
                for base_item in (".gitignore", "hugo.toml", "layouts", ".github", "static", f"content/posts/{slug}.md"):
                    if (SITE_DIR / base_item).exists():
                        subprocess.run(["git", "add", base_item], cwd=str(git_cwd), check=False)
            else:
                rel_post_path = f"site/content/posts/{slug}.md"
                subprocess.run(["git", "add", rel_post_path], cwd=str(git_cwd), check=False)
            commit_msg = f"publish(post): {slug} - {meta.get('title', slug)}"
            commit_proc = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=str(git_cwd),
                capture_output=True,
                text=True,
            )
            if commit_proc.returncode == 0:
                logs.append(f"[GIT COMMIT] 커밋 생성 완료: {commit_msg}")
            else:
                logs.append("[GIT COMMIT] 변경 사항이 이미 커밋되었거나 새로운 커밋이 필요하지 않습니다.")

            sha_proc = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(git_cwd),
                capture_output=True,
                text=True,
            )
            if sha_proc.returncode == 0:
                commit_sha = sha_proc.stdout.strip()

            branch = str(pub_cfg.get("branch") or "main")
            push_proc = subprocess.run(
                ["git", "push", "origin", branch],
                cwd=str(git_cwd),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if push_proc.returncode != 0:
                err_msg = (push_proc.stderr or push_proc.stdout or "").strip()
                logs.append(f"[GIT PUSH FAIL] {err_msg}")
                return {
                    "ok": False,
                    "slug": slug,
                    "error": f"원격 Git Push 실패: {err_msg}",
                    "logs": logs,
                }
            logs.append(f"[GIT PUSH] origin/{branch} 브랜치로 푸시 완료 (SHA: {commit_sha or 'unknown'}).")
            final_status = "pending_verification"

    if not dry_run:
        registry = load_publications_registry()
        registry["items"][slug] = {
            **existing_rec,
            "slug": slug,
            "title": meta.get("title", slug),
            "raw_file": str(raw_path.relative_to(PROJECT_ROOT)) if raw_path else existing_rec.get("raw_file"),
            "draft_file": f"stories/drafts/{slug}.md",
            "approved_file": f"stories/approved/{slug}.md",
            "site_file": f"site/content/posts/{slug}.md",
            "status": final_status,
            "commit_sha": commit_sha,
            "url": expected_url,
            "content_sha256": content_hash,
            "hugo_build_verified": hugo_build_ok,
            "updated_at": now_kst_iso(),
        }
        save_publications_registry(registry)

    return {
        "ok": True,
        "slug": slug,
        "title": meta.get("title", slug),
        "status": final_status if not dry_run else f"dry_run_ok ({existing_rec.get('status', 'approved')})",
        "dry_run": dry_run,
        "site_post": f"site/content/posts/{slug}.md",
        "commit_sha": commit_sha,
        "expected_url": expected_url,
        "hugo_build_verified": hugo_build_ok,
        "logs": logs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare and publish approved Hugo blog post.")
    parser.add_argument("--slug", required=True, help="Post slug to prepare/publish")
    parser.add_argument("--approve", action="store_true", help="Mark post as approved (draft: false) before staging")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Simulate staging and build without writing to site/")
    parser.add_argument("--stage", action="store_true", help="Actually copy approved post into site/content/posts/")
    parser.add_argument("--upsert", action="store_true", help="Allow updating an existing post with the same slug")
    parser.add_argument("--publish", action="store_true", help="Commit and push to remote GitHub repository")
    parser.add_argument(
        "--confirm-public-push",
        action="store_true",
        help="Explicit confirmation required to push to a public GitHub repository",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    # Default is dry-run unless --stage or --publish is passed
    effective_dry_run = True
    if args.stage or args.publish:
        effective_dry_run = False
    if args.dry_run:
        effective_dry_run = True

    result = prepare_and_publish(
        slug=args.slug,
        approve=args.approve,
        dry_run=effective_dry_run,
        upsert=args.upsert,
        publish_remote=args.publish,
        confirm_public_push=args.confirm_public_push,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1

    print(f"=== 발행 준비/실행 결과 ({args.slug}) ===")
    for log_line in result.get("logs", []):
        print(f"  {log_line}")

    if not result["ok"]:
        print(f"\n[오류] {result.get('error')}")
        return 1

    print(f"\n- 상태: {result['status']}")
    print(f"- 대상 경로: {result.get('site_post')}")
    print(f"- 예상 URL: {result.get('expected_url')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
