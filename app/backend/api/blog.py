from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.services.blog_service import (
    create_story_and_draft,
    get_story_detail,
    list_all_stories,
    record_audit_log,
    run_approve_and_publish_workflow,
    update_draft_content,
    update_publishing_settings,
)
from scripts.check_env import collect_env_status
from scripts.pipeline_core import (
    APPROVED_DIR,
    DRAFTS_DIR,
    PROJECT_ROOT,
    load_publishing_config,
)
from scripts.prepare_publish import approve_post
from scripts.publication_status import verify_and_update_status
from scripts.validate_post import validate_markdown_file

router = APIRouter()


class CreateStoryRequest(BaseModel):
    raw_text: str = Field(..., min_length=5, description="자유 형식 원문 스토리/메모")
    title: Optional[str] = None
    slug: Optional[str] = None
    template: str = "auto"
    tags: Optional[List[str]] = None
    description: Optional[str] = None


class UpdateDraftRequest(BaseModel):
    title: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    category: str = "essay"
    body_markdown: str


class PublishWorkflowRequest(BaseModel):
    approve: bool = False
    dry_run: bool = True
    upsert: bool = True
    publish_remote: bool = False
    confirm_public_push: bool = False


class PublishingConfigRequest(BaseModel):
    site_title: Optional[str] = None
    site_description: Optional[str] = None
    author_name: Optional[str] = None
    language_code: Optional[str] = None
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    repo_type: Optional[str] = None
    base_url: Optional[str] = None
    branch: Optional[str] = None
    default_dry_run: Optional[bool] = None
    approval_mode: Optional[str] = None


@router.get("/env")
def api_get_env():
    return collect_env_status()


@router.get("/stories")
def api_list_stories():
    return {"items": list_all_stories()}


@router.get("/stories/{slug}")
def api_get_story(slug: str):
    detail = get_story_detail(slug)
    if not detail:
        raise HTTPException(status_code=404, detail=f"스토리를 찾을 수 없습니다: {slug}")
    return detail


@router.post("/stories")
def api_create_story(req: CreateStoryRequest, db: Session = Depends(get_db)):
    try:
        return create_story_and_draft(
            db=db,
            raw_text=req.raw_text,
            title=req.title,
            slug=req.slug,
            template=req.template,
            tags=req.tags,
            description=req.description,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/stories/{slug}/draft")
def api_update_draft(slug: str, req: UpdateDraftRequest, db: Session = Depends(get_db)):
    detail = get_story_detail(slug)
    if not detail:
        raise HTTPException(status_code=404, detail=f"스토리를 찾을 수 없습니다: {slug}")
    return update_draft_content(
        db=db,
        slug=slug,
        title=req.title,
        description=req.description,
        tags=req.tags,
        category=req.category,
        body_markdown=req.body_markdown,
    )


@router.post("/stories/{slug}/validate")
def api_validate_story(slug: str, db: Session = Depends(get_db)):
    detail = get_story_detail(slug)
    if not detail:
        raise HTTPException(status_code=404, detail=f"스토리를 찾을 수 없습니다: {slug}")

    draft_path = DRAFTS_DIR / f"{slug}.md"
    approved_path = APPROVED_DIR / f"{slug}.md"
    target = draft_path if draft_path.exists() else approved_path
    if not target.exists():
        raise HTTPException(status_code=400, detail="검증할 초안 또는 승인본 파일이 없습니다.")

    raw_rel = detail["summary"].get("raw_file")
    raw_path = (PROJECT_ROOT / raw_rel) if raw_rel else None
    res = validate_markdown_file(target, raw_path if (raw_path and raw_path.exists()) else None)
    record_audit_log(
        db,
        slug=slug,
        action="validate",
        status="success" if res["valid"] else "failed",
        summary="품질/보안 검증 통과" if res["valid"] else f"검증 오류 {len(res['errors'])}건 발생",
        details=res,
    )
    return res


@router.post("/stories/{slug}/approve")
def api_approve_story(slug: str, db: Session = Depends(get_db)):
    res = approve_post(slug)
    record_audit_log(
        db,
        slug=slug,
        action="approve",
        status="success" if res.get("ok") else "failed",
        summary=res.get("error") or f"'{slug}' 게시물 발행 승인 완료 (draft: false)",
        details=res,
    )
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error") or "승인 실패")
    return get_story_detail(slug)


@router.post("/stories/{slug}/publish")
def api_publish_story(slug: str, req: PublishWorkflowRequest, db: Session = Depends(get_db)):
    res = run_approve_and_publish_workflow(
        db=db,
        slug=slug,
        approve=req.approve,
        dry_run=req.dry_run,
        upsert=req.upsert,
        publish_remote=req.publish_remote,
        confirm_public_push=req.confirm_public_push,
    )
    return res


@router.get("/publications/status")
def api_publication_status(slug: Optional[str] = None, check_remote: bool = False):
    return verify_and_update_status(slug=slug, check_remote=check_remote)


@router.get("/settings/publishing")
def api_get_publishing_settings():
    return load_publishing_config()


@router.put("/settings/publishing")
def api_update_publishing_settings(req: PublishingConfigRequest, db: Session = Depends(get_db)):
    payload = {k: v for k, v in req.model_dump().items() if v is not None}
    return update_publishing_settings(db, payload)
