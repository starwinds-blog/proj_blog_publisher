#!/usr/bin/env python3
"""Validate Hugo Markdown post: Front Matter, code blocks, links/images, privacy/secrets, and raw preservation."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.pipeline_core import (  # noqa: E402
    PROJECT_ROOT,
    SITE_DIR,
    SITE_IMAGES_DIR,
    now_kst_iso,
    parse_front_matter,
)
from scripts.story_editor import extract_code_blocks  # noqa: E402

SECRET_PATTERNS = [
    ("github_token", r"gh[pousr]_[A-Za-z0-9_]{20,}", "error", "GitHub Personal/OAuth Token 패턴이 감지되었습니다."),
    ("openai_or_api_key", r"sk-[A-Za-z0-9_-]{20,}", "error", "API Secret Key(sk-...) 패턴이 감지되었습니다."),
    ("aws_access_key", r"AKIA[0-9A-Z]{16}", "error", "AWS Access Key ID 패턴이 감지되었습니다."),
    ("private_key_block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "error", "개인키(Private Key) 블록이 감지되었습니다."),
    (
        "generic_secret_assignment",
        r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
        "error",
        "비밀번호/API 키 문자열 할당 패턴이 감지되었습니다.",
    ),
    (
        "internal_ip_or_corp_url",
        r"https?://(10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|[^/\s]+\.(internal|corp|lan))",
        "warning",
        "사내/내부망 IP 또는 비공개 도메인 URL이 포함되어 있습니다.",
    ),
    (
        "phone_number_kr",
        r"(?<!\d)01[016789]-\d{3,4}-\d{4}(?!\d)",
        "warning",
        "개인 휴대전화 번호 형식이 포함되어 있습니다.",
    ),
]

REQUIRED_FRONT_MATTER_KEYS = ["title", "date", "draft", "description", "tags", "categories", "slug"]


def validate_markdown_file(file_path: Path, raw_path: Optional[Path] = None) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    checks: Dict[str, bool] = {
        "front_matter_valid": True,
        "code_blocks_balanced": True,
        "links_and_images_valid": True,
        "no_secrets_found": True,
        "raw_code_preserved": True,
    }

    if not file_path.exists():
        return {
            "valid": False,
            "file": str(file_path),
            "checked_at": now_kst_iso(),
            "errors": [f"파일이 존재하지 않습니다: {file_path}"],
            "warnings": [],
            "checks": {k: False for k in checks},
            "front_matter": {},
        }

    text = file_path.read_text(encoding="utf-8")
    meta, body, fm_errors = parse_front_matter(text)
    if fm_errors:
        errors.extend(fm_errors)
        checks["front_matter_valid"] = False

    for req_key in REQUIRED_FRONT_MATTER_KEYS:
        if req_key not in meta or meta[req_key] == "" or meta[req_key] is None:
            errors.append(f"Front Matter 필수 키 누락 또는 빈 값: '{req_key}'")
            checks["front_matter_valid"] = False

    slug_val = str(meta.get("slug") or "")
    if slug_val and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug_val):
        errors.append(f"slug 형식이 올바르지 않습니다(영문 소문자/숫자/하이픈만 허용): '{slug_val}'")
        checks["front_matter_valid"] = False

    if not body.strip():
        errors.append("본문(Body) 내용이 비어 있습니다.")

    # Check fenced code block balance
    fence_lines = [ln for ln in body.splitlines() if ln.lstrip().startswith("```")]
    if len(fence_lines) % 2 != 0:
        errors.append(f"코드 블록(```)의 시작과 끝 개수가 맞지 않습니다 (감지된 ``` 라인 수: {len(fence_lines)}).")
        checks["code_blocks_balanced"] = False

    # Check links and images (outside code blocks)
    masked_body, draft_code_blocks = extract_code_blocks(body)

    # Empty markdown links: [label]()
    for match in re.finditer(r"\[([^\]]+)\]\(\s*\)", masked_body):
        errors.append(f"비어 있는 링크 URL이 존재합니다: [{match.group(1)}]()")
        checks["links_and_images_valid"] = False

    # Image references: ![alt](path)
    for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", masked_body):
        alt_text, img_target = match.group(1).strip(), match.group(2).strip()
        if not alt_text:
            warnings.append(f"이미지 대체 텍스트(alt)가 비어 있습니다: !![]({img_target})")
        if img_target.startswith(("http://", "https://")):
            warnings.append(f"외부 이미지 URL이 참조되었습니다(저작권/링크 깨짐 확인 필요): {img_target}")
        else:
            # Check local image existence in site/static/
            normalized_rel = img_target.lstrip("/")
            candidate_paths = [
                SITE_DIR / "static" / normalized_rel,
                SITE_IMAGES_DIR / Path(normalized_rel).name,
                file_path.parent / normalized_rel,
            ]
            if not any(p.exists() for p in candidate_paths):
                errors.append(f"참조된 로컬 이미지 파일을 찾을 수 없습니다: {img_target} (기대 경로: site/static/{normalized_rel})")
                checks["links_and_images_valid"] = False

    # Check secrets & privacy patterns across full text
    for pat_name, regex, severity, message in SECRET_PATTERNS:
        found = re.search(regex, text)
        if found:
            sample = found.group(0)
            masked_sample = sample[:6] + "***" if len(sample) > 8 else "***"
            if severity == "error":
                errors.append(f"[보안 차단: {pat_name}] {message} (감지값: {masked_sample})")
                checks["no_secrets_found"] = False
            else:
                warnings.append(f"[프라이버시 주의: {pat_name}] {message} (감지값: {masked_sample})")

    # Check unresolved [검증 필요] markers
    if "[검증 필요]" in body:
        warnings.append("본문에 '[검증 필요]' 표시가 남아 있습니다. 공개 발행 전에 사실 여부를 확인하세요.")

    # Verify code blocks preserved from raw file if raw_path provided
    if raw_path and raw_path.exists():
        raw_text = raw_path.read_text(encoding="utf-8")
        _, raw_code_blocks = extract_code_blocks(raw_text)
        if raw_code_blocks and raw_code_blocks != draft_code_blocks:
            errors.append("원문(raw)의 코드 블록 내용이 편집 과정에서 변경되었거나 누락되었습니다.")
            checks["raw_code_preserved"] = False

    return {
        "valid": len(errors) == 0,
        "file": str(file_path.relative_to(PROJECT_ROOT)) if file_path.is_relative_to(PROJECT_ROOT) else str(file_path),
        "checked_at": now_kst_iso(),
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "front_matter": meta,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Hugo Markdown blog post.")
    parser.add_argument("--file", required=True, help="Path to Markdown file to validate")
    parser.add_argument("--raw", default=None, help="Optional path to original raw story file")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    file_path = Path(args.file).resolve()
    raw_path = Path(args.raw).resolve() if args.raw else None

    result = validate_markdown_file(file_path, raw_path)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1

    status_label = "PASS (유효함)" if result["valid"] else "FAIL (오류 있음)"
    print(f"=== 게시물 검증 결과: {status_label} ===")
    print(f"- 대상 파일: {result['file']}")
    for k, ok in result["checks"].items():
        print(f"  * {k:24s}: {'OK' if ok else 'FAIL'}")

    if result["warnings"]:
        print("\n[경고 (Warnings)]")
        for w in result["warnings"]:
            print(f"  - {w}")

    if result["errors"]:
        print("\n[오류 (Errors)]")
        for e in result["errors"]:
            print(f"  ! {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
