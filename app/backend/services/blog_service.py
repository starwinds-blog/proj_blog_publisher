from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.backend.models.story_log import StoryAuditLog
from scripts.check_env import collect_env_status
from scripts.pipeline_core import (
    APPROVED_DIR,
    DRAFTS_DIR,
    PROJECT_ROOT,
    RAW_DIR,
    SITE_POSTS_DIR,
    build_markdown_post,
    ensure_directories,
    load_publications_registry,
    load_publishing_config,
    now_kst_iso,
    parse_front_matter,
    save_publishing_config,
    slugify,
)
from scripts.prepare_publish import _build_expected_url, approve_post, prepare_and_publish
from scripts.publication_status import verify_and_update_status
from scripts.story_editor import create_draft_from_raw, infer_title_and_body
from scripts.validate_post import validate_markdown_file


def record_audit_log(
    db: Optional[Session],
    slug: str,
    action: str,
    status: str,
    summary: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    if db is None:
        return
    entry = StoryAuditLog(
        slug=slug,
        action=action,
        status=status,
        summary=summary,
        details_json=json.dumps(details or {}, ensure_ascii=False),
    )
    db.add(entry)
    db.commit()


def list_all_stories() -> List[Dict[str, Any]]:
    """Aggregate all stories across raw, drafts, approved, and publications registry."""
    ensure_directories()
    registry = load_publications_registry().get("items", {})

    slug_map: Dict[str, Dict[str, Any]] = {}

    # 1. Scan raw files
    for raw_file in sorted(RAW_DIR.glob("*")):
        if not raw_file.is_file() or raw_file.name.startswith("."):
            continue
        raw_text = raw_file.read_text(encoding="utf-8")
        title, _ = infer_title_and_body(raw_text)
        slug = slugify(raw_file.stem or title)
        slug_map[slug] = {
            "slug": slug,
            "title": title,
            "stage": "raw",
            "template": "auto",
            "tags": [],
            "date": "",
            "description": "",
            "raw_file": f"stories/raw/{raw_file.name}",
            "draft_file": None,
            "approved_file": None,
            "site_file": None,
            "url": None,
            "commit_sha": None,
            "updated_at": now_kst_iso(),
            "validation_valid": None,
        }

    # 2. Scan draft files & review reports
    for draft_file in sorted(DRAFTS_DIR.glob("*.md")):
        slug = draft_file.stem
        draft_text = draft_file.read_text(encoding="utf-8")
        meta, _, _ = parse_front_matter(draft_text)
        review_file = DRAFTS_DIR / f"{slug}.review.json"
        review_data = {}
        if review_file.exists():
            try:
                review_data = json.loads(review_file.read_text(encoding="utf-8"))
            except Exception:
                review_data = {}

        raw_rel = review_data.get("raw_file")
        raw_path = (PROJECT_ROOT / raw_rel) if raw_rel else None
        val = validate_markdown_file(draft_file, raw_path if (raw_path and raw_path.exists()) else None)

        item = slug_map.get(slug, {"slug": slug})
        categories = meta.get("categories") or []
        item.update(
            {
                "slug": slug,
                "title": meta.get("title") or item.get("title") or slug,
                "stage": "draft",
                "template": categories[0] if categories else review_data.get("template", "essay"),
                "tags": meta.get("tags") or [],
                "date": str(meta.get("date") or ""),
                "description": str(meta.get("description") or ""),
                "raw_file": raw_rel or item.get("raw_file"),
                "draft_file": f"stories/drafts/{draft_file.name}",
                "updated_at": review_data.get("created_at") or item.get("updated_at") or now_kst_iso(),
                "validation_valid": val["valid"],
                "validation_errors_count": len(val["errors"]),
                "validation_warnings_count": len(val["warnings"]),
            }
        )
        slug_map[slug] = item

    # 3. Scan approved files
    for app_file in sorted(APPROVED_DIR.glob("*.md")):
        slug = app_file.stem
        meta, _, _ = parse_front_matter(app_file.read_text(encoding="utf-8"))
        item = slug_map.get(slug, {"slug": slug})
        item["approved_file"] = f"stories/approved/{app_file.name}"
        item["title"] = meta.get("title") or item.get("title") or slug
        item["stage"] = "approved"
        slug_map[slug] = item

    # 4. Overlay publication records & site files
    for slug, rec in registry.items():
        item = slug_map.get(slug, {"slug": slug})
        site_post = SITE_POSTS_DIR / f"{slug}.md"
        if site_post.exists():
            item["site_file"] = f"site/content/posts/{slug}.md"
        rec_status = rec.get("status")
        if rec_status in ("approved", "staged", "pending_verification", "published", "deploy_failed"):
            item["stage"] = rec_status
        item["url"] = rec.get("url")
        item["commit_sha"] = rec.get("commit_sha")
        item["updated_at"] = rec.get("updated_at") or rec.get("approved_at") or item.get("updated_at")
        slug_map[slug] = item

    return sorted(slug_map.values(), key=lambda x: str(x.get("updated_at") or ""), reverse=True)


def get_story_detail(slug: str) -> Optional[Dict[str, Any]]:
    ensure_directories()
    stories = {s["slug"]: s for s in list_all_stories()}
    summary = stories.get(slug)
    if not summary:
        return None

    raw_content = ""
    raw_rel = summary.get("raw_file")
    raw_path: Optional[Path] = None
    if raw_rel:
        candidate = PROJECT_ROOT / raw_rel
        if candidate.exists():
            raw_path = candidate
            raw_content = candidate.read_text(encoding="utf-8")

    draft_path = DRAFTS_DIR / f"{slug}.md"
    approved_path = APPROVED_DIR / f"{slug}.md"
    active_md_path = draft_path if draft_path.exists() else (approved_path if approved_path.exists() else None)

    draft_markdown = ""
    front_matter: Dict[str, Any] = {}
    body_markdown = ""
    validation: Optional[Dict[str, Any]] = None

    if active_md_path and active_md_path.exists():
        draft_markdown = active_md_path.read_text(encoding="utf-8")
        front_matter, body_markdown, _ = parse_front_matter(draft_markdown)
        validation = validate_markdown_file(active_md_path, raw_path)

    review_path = DRAFTS_DIR / f"{slug}.review.json"
    review_report: Dict[str, Any] = {}
    if review_path.exists():
        try:
            review_report = json.loads(review_path.read_text(encoding="utf-8"))
        except Exception:
            review_report = {}

    registry = load_publications_registry().get("items", {})
    publication_record = registry.get(slug)

    return {
        "summary": summary,
        "raw_content": raw_content,
        "draft_markdown": draft_markdown,
        "front_matter": front_matter,
        "body_markdown": body_markdown,
        "review_report": review_report,
        "validation": validation,
        "publication_record": publication_record,
    }


def create_story_and_draft(
    db: Optional[Session],
    raw_text: str,
    title: Optional[str] = None,
    slug: Optional[str] = None,
    template: str = "auto",
    tags: Optional[List[str]] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Save raw input to stories/raw/<slug>.md (without overwriting existing raw unless new slug) and generate draft."""
    ensure_directories()
    inferred_title, _ = infer_title_and_body(raw_text)
    effective_title = (title or inferred_title or "새 스토리").strip()
    effective_slug = slugify(slug or effective_title)

    raw_path = RAW_DIR / f"{effective_slug}.md"
    # Preserve raw if identical or write initial raw
    if not raw_path.exists():
        raw_path.write_text(raw_text.strip() + "\n", encoding="utf-8")
    else:
        # If user submits a new raw version with same slug, keep immutable backup if content differs
        existing_raw = raw_path.read_text(encoding="utf-8")
        if existing_raw.strip() != raw_text.strip():
            backup_ts = now_kst_iso().replace(":", "").replace("+", "_")
            backup_path = RAW_DIR / f"{effective_slug}.{backup_ts}.bak.md"
            backup_path.write_text(existing_raw, encoding="utf-8")
            raw_path.write_text(raw_text.strip() + "\n", encoding="utf-8")

    report = create_draft_from_raw(
        raw_path=raw_path,
        template=template,
        title_override=title,
        slug_override=effective_slug,
        tags_override=tags,
        description_override=description,
    )

    record_audit_log(
        db,
        slug=effective_slug,
        action="generate_draft",
        status="success",
        summary=f"'{effective_title}' 원문 저장 및 '{report['template']}' 템플릿 초안 생성",
        details={"template": report["template"], "raw_file": report["raw_file"]},
    )
    return get_story_detail(effective_slug) or report


def update_draft_content(
    db: Optional[Session],
    slug: str,
    title: str,
    description: str,
    tags: List[str],
    category: str,
    body_markdown: str,
) -> Dict[str, Any]:
    """Update draft Markdown from user's manual edits in the dashboard studio and refresh diff & validation."""
    ensure_directories()
    draft_path = DRAFTS_DIR / f"{slug}.md"
    existing_meta: Dict[str, Any] = {}
    if draft_path.exists():
        existing_meta, _, _ = parse_front_matter(draft_path.read_text(encoding="utf-8"))

    meta = {
        "title": title.strip() or existing_meta.get("title") or slug,
        "date": existing_meta.get("date") or now_kst_iso(),
        "draft": True,
        "description": description.strip(),
        "tags": tags,
        "categories": [category or "essay"],
        "slug": slug,
    }
    updated_md = build_markdown_post(meta, body_markdown)
    draft_path.write_text(updated_md, encoding="utf-8")

    # Refresh diff against raw
    review_path = DRAFTS_DIR / f"{slug}.review.json"
    review_data: Dict[str, Any] = {}
    if review_path.exists():
        try:
            review_data = json.loads(review_path.read_text(encoding="utf-8"))
        except Exception:
            review_data = {}

    raw_rel = review_data.get("raw_file") or f"stories/raw/{slug}.md"
    raw_path = PROJECT_ROOT / raw_rel
    if raw_path.exists():
        raw_text = raw_path.read_text(encoding="utf-8")
        diff_lines = list(
            difflib.unified_diff(
                raw_text.splitlines(),
                updated_md.splitlines(),
                fromfile=raw_rel,
                tofile=f"stories/drafts/{slug}.md",
                lineterm="",
            )
        )
        review_data["diff"] = "\n".join(diff_lines)
        review_data["front_matter"] = meta
        review_data["updated_at"] = now_kst_iso()
        review_path.write_text(json.dumps(review_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    record_audit_log(
        db,
        slug=slug,
        action="edit_draft",
        status="success",
        summary=f"'{meta['title']}' 초안 수동 편집 및 Diff 갱신",
    )
    return get_story_detail(slug) or {}


def run_approve_and_publish_workflow(
    db: Optional[Session],
    slug: str,
    approve: bool = False,
    dry_run: bool = True,
    upsert: bool = True,
    publish_remote: bool = False,
    confirm_public_push: bool = False,
) -> Dict[str, Any]:
    res = prepare_and_publish(
        slug=slug,
        approve=approve,
        dry_run=dry_run,
        upsert=upsert,
        publish_remote=publish_remote,
        confirm_public_push=confirm_public_push,
    )
    action_name = "publish_remote" if publish_remote else ("approve_and_stage" if not dry_run else "dry_run")
    status_str = "success" if res.get("ok") else "failed"
    if res.get("ok") and dry_run:
        status_str = "dry_run"

    record_audit_log(
        db,
        slug=slug,
        action=action_name,
        status=status_str,
        summary=res.get("error") or f"상태: {res.get('status')} ({'Dry-run' if dry_run else '실제 반영'})",
        details=res,
    )
    return res


def get_dashboard_overview(db: Optional[Session] = None) -> Dict[str, Any]:
    env = collect_env_status()
    stories = list_all_stories()
    pub_cfg = load_publishing_config()
    pub_status = verify_and_update_status(check_remote=False)

    counts = {
        "total": len(stories),
        "raw": len([s for s in stories if s["stage"] == "raw"]),
        "draft": len([s for s in stories if s["stage"] == "draft"]),
        "approved": len([s for s in stories if s["stage"] == "approved"]),
        "staged": len([s for s in stories if s["stage"] == "staged"]),
        "pending_verification": len([s for s in stories if s["stage"] == "pending_verification"]),
        "published": len([s for s in stories if s["stage"] == "published"]),
    }

    recent_logs: List[Dict[str, Any]] = []
    if db is not None:
        rows = db.query(StoryAuditLog).order_by(StoryAuditLog.id.desc()).limit(12).all()
        for r in rows:
            recent_logs.append(
                {
                    "id": r.id,
                    "slug": r.slug,
                    "action": r.action,
                    "status": r.status,
                    "summary": r.summary,
                    "created_at": r.created_at.isoformat(timespec="seconds") if r.created_at else "",
                }
            )

    return {
        "server_time_kst": now_kst_iso(),
        "env": env,
        "counts": counts,
        "stories": stories,
        "publishing_config": pub_cfg,
        "publications": pub_status.get("results", {}),
        "recent_logs": recent_logs,
    }


def update_publishing_settings(db: Optional[Session], payload: Dict[str, Any]) -> Dict[str, Any]:
    allowed_keys = {
        "site_title",
        "site_description",
        "author_name",
        "language_code",
        "github_owner",
        "github_repo",
        "repo_type",
        "base_url",
        "branch",
        "default_dry_run",
        "approval_mode",
    }
    filtered = {k: v for k, v in payload.items() if k in allowed_keys}
    save_publishing_config(filtered)

    # Sync site/hugo.toml title and baseURL if provided
    hugo_toml_path = PROJECT_ROOT / "site" / "hugo.toml"
    if hugo_toml_path.exists():
        toml_text = hugo_toml_path.read_text(encoding="utf-8")
        if "site_title" in filtered and filtered["site_title"]:
            import re
            toml_text = re.sub(
                r'^title\s*=\s*".*"',
                f'title = {json.dumps(str(filtered["site_title"]), ensure_ascii=False)}',
                toml_text,
                flags=re.MULTILINE,
            )
        if "base_url" in filtered and filtered["base_url"]:
            import re
            b_url = str(filtered["base_url"]).rstrip("/") + "/"
            toml_text = re.sub(
                r'^baseURL\s*=\s*".*"',
                f'baseURL = {json.dumps(b_url, ensure_ascii=False)}',
                toml_text,
                flags=re.MULTILINE,
            )
        hugo_toml_path.write_text(toml_text, encoding="utf-8")

    # Sync site/.git remote origin if github_owner & github_repo are configured
    site_git_dir = PROJECT_ROOT / "site" / ".git"
    owner = str(filtered.get("github_owner") or "").strip()
    repo = str(filtered.get("github_repo") or "").strip()
    if site_git_dir.exists() and owner and repo:
        import subprocess
        cur_remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(PROJECT_ROOT / "site"),
            capture_output=True,
            text=True,
        )
        host_prefix = "git@github.com:"
        if cur_remote.returncode == 0 and ":" in cur_remote.stdout:
            host_prefix = cur_remote.stdout.strip().split(":", 1)[0] + ":"
        new_remote_url = f"{host_prefix}{owner}/{repo}.git"
        subprocess.run(
            ["git", "remote", "set-url", "origin", new_remote_url],
            cwd=str(PROJECT_ROOT / "site"),
            check=False,
        )

    updated_cfg = load_publishing_config()
    registry = load_publications_registry()
    for slug, rec in list(registry["items"].items()):
        rec["url"] = _build_expected_url(slug, updated_cfg)
        registry["items"][slug] = rec
    save_publications_registry(registry)

    record_audit_log(
        db,
        slug="system-config",
        action="update_settings",
        status="success",
        summary="블로그 및 GitHub Pages 배포 설정 업데이트",
        details=filtered,
    )
    return updated_cfg
