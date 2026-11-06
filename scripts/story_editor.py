#!/usr/bin/env python3
"""Story Editor: transforms raw free-form notes into Hugo Markdown drafts with diff & review reports.

Respects editorial policy:
- Never modifies raw file
- Protects fenced code blocks
- Does not fabricate facts/links/dates
- Marks uncertain statements with [검증 필요]
- Separates AI/editor suggestions into a separate list
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.pipeline_core import (  # noqa: E402
    DRAFTS_DIR,
    RAW_DIR,
    build_markdown_post,
    ensure_directories,
    now_kst_iso,
    parse_front_matter,
    slugify,
)

# Conservative Korean spacing/typo normalization rules (applied ONLY outside code blocks)
SAFE_REPLACEMENTS: List[Tuple[str, str, str]] = [
    (r"되서", "되어서", "맞춤법 교정 ('되서' -> '되어서')"),
    (r"안되요", "안 돼요", "맞춤법 교정 ('안되요' -> '안 돼요')"),
    (r"안됩니다", "안 됩니다", "띄어쓰기 교정 ('안됩니다' -> '안 됩니다')"),
    (r"할수있", "할 수 있", "의존명사 띄어쓰기 교정 ('할수있' -> '할 수 있')"),
    (r"할수없", "할 수 없", "의존명사 띄어쓰기 교정 ('할수없' -> '할 수 없')"),
    (r"인것같다", "인 것 같다", "의존명사 띄어쓰기 교정"),
    (r"인거같다", "인 것 같다", "구어체/띄어쓰기 정리"),
    (r"그랫다", "그랬다", "맞춤법 교정"),
    (r"어쨋든", "어쨌든", "맞춤법 교정"),
    (r"몇일", "며칠", "맞춤법 교정 ('몇일' -> '며칠')"),
    (r"금새", "금세", "맞춤법 교정 ('금새' -> '금세')"),
    (r"웬지", "왠지", "맞춤법 교정 ('웬지' -> '왠지')"),
]

UNCERTAINTY_PATTERNS: List[Tuple[str, str]] = [
    (r"(정확한\s*(수치|날짜|버전)는\s*기억나지\s*않|기억이\s*가물가물|아마\s*\d+%|\?\?\?)", "작성자가 불확실하다고 언급한 수치/사실 확인 필요"),
    (r"(나중에\s*링크\s*추가|TODO|TBD|FIXME)", "미완성 메모/링크 보완 필요"),
]


def detect_template_type(text: str) -> str:
    """Recommend one of: essay, experience, technical-note, review."""
    lowered = text.lower()
    if "```" in text or any(k in lowered for k in ["버그", "에러", "설치", "명령어", "설정", "코드", "api", "cli", "환경", "재현"]):
        return "technical-note"
    if any(k in lowered for k in ["장단점", "장점", "단점", "총평", "후기", "리뷰", "비교해", "구매", "사용기"]):
        return "review"
    if any(k in lowered for k in ["배경", "시도", "해결", "교훈", "배운 점", "프로젝트", "도입기", "진행했"]):
        return "experience"
    return "essay"


def extract_code_blocks(text: str) -> Tuple[str, List[str]]:
    """Replace fenced code blocks with placeholders so text polishing never touches code."""
    blocks: List[str] = []
    pattern = re.compile(r"(```[^\n]*\n.*?\n```)", re.DOTALL)

    def _repl(match: re.Match[str]) -> str:
        idx = len(blocks)
        blocks.append(match.group(1))
        return f"@@CODE_BLOCK_{idx}@@"

    masked = pattern.sub(_repl, text)
    return masked, blocks


def restore_code_blocks(masked_text: str, blocks: List[str]) -> str:
    result = masked_text
    for idx, block in enumerate(blocks):
        result = result.replace(f"@@CODE_BLOCK_{idx}@@", block)
    return result


def infer_title_and_body(raw_text: str) -> Tuple[str, str]:
    """Infer title from first Markdown heading or first short line; preserve full narrative."""
    lines = [ln.rstrip() for ln in raw_text.strip().splitlines()]
    if not lines:
        return "제목 없는 이야기", ""

    first = lines[0].strip()
    if first.startswith("#"):
        title = first.lstrip("#").strip()
        rest = "\n".join(lines[1:]).strip()
        return (title or "새 글"), rest

    if first.lower().startswith("제목:") or first.lower().startswith("title:"):
        title = first.split(":", 1)[1].strip()
        rest = "\n".join(lines[1:]).strip()
        return (title or "새 글"), rest

    # If the first line is a short standalone title followed by a blank line
    if len(lines) >= 2 and not lines[1].strip() and len(first) <= 60 and not first.endswith((".", "다.", "요.", "까?")):
        title = first
        rest = "\n".join(lines[2:]).strip()
        return title, rest

    # Otherwise derive title from first sentence without deleting it from body
    first_sentence = re.split(r"(?<=[.!?])\s+", first)[0].strip()
    title = first_sentence[:45].rstrip(".!?")
    return (title or "새 블로그 글"), "\n".join(lines).strip()


def infer_tags(text: str, template_type: str) -> List[str]:
    candidates = [
        ("Hugo", ["hugo", "휴고"]),
        ("GitHub Pages", ["github pages", "깃허브 페이지", "github actions"]),
        ("자동화", ["자동화", "워크플로", "파이프라인", "스크립트"]),
        ("AI", ["ai", "codex", "에이전트", "llm"]),
        ("개발노트", ["코드", "버그", "설치", "빌드", "설정"]),
        ("회고", ["회고", "생각", "느낀", "돌아보", "마음"]),
        ("경험", ["경험", "시도", "과정", "배운"]),
        ("리뷰", ["리뷰", "후기", "장단점", "비교"]),
    ]
    lowered = text.lower()
    tags: List[str] = []
    for tag, keywords in candidates:
        if any(kw in lowered for kw in keywords):
            tags.append(tag)
    if not tags:
        default_by_tpl = {
            "essay": ["생각", "회고"],
            "experience": ["경험", "기록"],
            "technical-note": ["기술노트", "개발"],
            "review": ["리뷰", "후기"],
        }
        tags = default_by_tpl.get(template_type, ["기록"])
    return tags[:5]


def polish_paragraphs_and_structure(
    body: str,
    template_type: str,
) -> Tuple[str, List[str], List[str], List[str]]:
    """Polish prose while strictly preserving author's meaning and code blocks."""
    masked, code_blocks = extract_code_blocks(body)
    changes_made: List[str] = []
    fact_checks: List[str] = []
    suggestions: List[str] = []

    # Normalize excessive horizontal spaces & Windows line endings
    cleaned = masked.replace("\r\n", "\n")

    # Apply conservative spelling/spacing fixes outside code blocks
    for pattern, replacement, reason in SAFE_REPLACEMENTS:
        if re.search(pattern, cleaned):
            cleaned = re.sub(pattern, replacement, cleaned)
            if reason not in changes_made:
                changes_made.append(reason)

    # Detect uncertain phrases and mark with [검증 필요] if not already marked
    for pattern, desc in UNCERTAINTY_PATTERNS:
        matches = list(re.finditer(pattern, cleaned, flags=re.IGNORECASE))
        if matches:
            fact_checks.append(f"{desc} ('{matches[0].group(0)}')")
            cleaned = re.sub(
                pattern,
                lambda m: m.group(0) if "[검증 필요]" in m.group(0) else f"{m.group(0)} `[검증 필요]`",
                cleaned,
                flags=re.IGNORECASE,
            )

    # Split into paragraphs and break overly dense single-block paragraphs (>350 chars without code placeholder)
    raw_paragraphs = [p.strip() for p in re.split(r"\n{2,}", cleaned) if p.strip()]
    normalized_paragraphs: List[str] = []
    split_count = 0

    for para in raw_paragraphs:
        if "@@CODE_BLOCK_" in para or para.startswith(("#", "-", "*", ">", "|", "1.")):
            normalized_paragraphs.append(para)
            continue
        sentences = re.split(r"(?<=[.!?다요죠])\s+", para)
        if len(para) > 260 and len(sentences) >= 4:
            mid = len(sentences) // 2
            normalized_paragraphs.append(" ".join(sentences[:mid]).strip())
            normalized_paragraphs.append(" ".join(sentences[mid:]).strip())
            split_count += 1
        else:
            normalized_paragraphs.append(para)

    if split_count > 0:
        changes_made.append(f"가독성을 위해 긴 문단 {split_count}건을 호흡 단위로 분리")

    # Apply light template structuring ONLY if user has no headings and post is multi-paragraph non-essay
    has_headings = any(p.startswith("#") for p in normalized_paragraphs)
    if not has_headings and template_type in ("experience", "technical-note", "review") and len(normalized_paragraphs) >= 3:
        section_titles = {
            "experience": ["## 배경과 상황", "## 진행 과정", "## 결과 및 배운 점"],
            "technical-note": ["## 문제와 배경", "## 검토 및 해결 과정", "## 정리"],
            "review": ["## 검토 배경", "## 사용 경험과 특징", "## 종합 의견"],
        }[template_type]
        structured: List[str] = []
        structured.append(section_titles[0])
        structured.append(normalized_paragraphs[0])
        structured.append(section_titles[1])
        structured.extend(normalized_paragraphs[1:-1])
        structured.append(section_titles[2])
        structured.append(normalized_paragraphs[-1])
        normalized_paragraphs = structured
        changes_made.append(f"'{template_type}' 템플릿에 맞춰 소제목(H2) 구조 적용")
    elif template_type == "essay":
        suggestions.append("에세이/회고 유형이므로 원문의 서사 흐름을 살려 인위적인 H2 소제목 분할을 생략했습니다.")

    if not changes_made:
        changes_made.append("원문 문단 호흡 및 마크다운 서식 정리, YAML Front Matter 생성")

    if len(normalized_paragraphs) <= 1:
        suggestions.append("글의 분량이 짧습니다. 독자의 이해를 돕기 위해 당시 배경이나 구체적인 예시 한두 문장을 덧붙여도 좋습니다.")

    final_masked = "\n\n".join(normalized_paragraphs)
    restored = restore_code_blocks(final_masked, code_blocks)
    return restored, changes_made, fact_checks, suggestions


def create_draft_from_raw(
    raw_path: Path,
    template: str = "auto",
    title_override: Optional[str] = None,
    slug_override: Optional[str] = None,
    tags_override: Optional[List[str]] = None,
    date_override: Optional[str] = None,
    description_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Read raw file (read-only), generate draft Markdown + review JSON in stories/drafts/."""
    ensure_directories()
    if not raw_path.exists():
        raise FileNotFoundError(f"원본 파일을 찾을 수 없습니다: {raw_path}")

    raw_content = raw_path.read_text(encoding="utf-8")
    existing_fm, raw_body_if_fm, fm_errors = parse_front_matter(raw_content)
    source_body = raw_body_if_fm if (existing_fm and not fm_errors) else raw_content

    inferred_title, body_without_title = infer_title_and_body(source_body)
    final_title = (title_override or existing_fm.get("title") or inferred_title).strip()

    chosen_template = template if template in ("essay", "experience", "technical-note", "review") else detect_template_type(source_body)
    stem_fallback = raw_path.stem.lower()
    final_slug = slugify(slug_override or str(existing_fm.get("slug") or "") or stem_fallback or final_title)

    polished_body, changes_made, fact_checks, suggestions = polish_paragraphs_and_structure(
        body_without_title, chosen_template
    )

    # Generate concise summary description from first non-heading, non-code paragraph
    plain_paras = [
        re.sub(r"[`*_>#\[\]]", "", p).strip()
        for p in polished_body.split("\n\n")
        if p.strip() and not p.strip().startswith(("```", "#"))
    ]
    first_para = plain_paras[0] if plain_paras else final_title
    inferred_desc = (first_para[:110] + "...") if len(first_para) > 110 else first_para
    final_description = (description_override or existing_fm.get("description") or inferred_desc).strip()

    final_tags = tags_override if tags_override else (existing_fm.get("tags") or infer_tags(source_body, chosen_template))
    final_date = date_override or existing_fm.get("date") or now_kst_iso()

    front_matter = {
        "title": final_title,
        "date": final_date,
        "draft": True,
        "description": final_description,
        "tags": final_tags,
        "categories": [chosen_template],
        "slug": final_slug,
    }

    draft_markdown = build_markdown_post(front_matter, polished_body)
    draft_path = DRAFTS_DIR / f"{final_slug}.md"
    review_path = DRAFTS_DIR / f"{final_slug}.review.json"

    draft_path.write_text(draft_markdown, encoding="utf-8")

    diff_lines = list(
        difflib.unified_diff(
            raw_content.splitlines(),
            draft_markdown.splitlines(),
            fromfile=f"stories/raw/{raw_path.name}",
            tofile=f"stories/drafts/{draft_path.name}",
            lineterm="",
        )
    )

    review_report = {
        "slug": final_slug,
        "title": final_title,
        "template": chosen_template,
        "raw_file": f"stories/raw/{raw_path.name}",
        "draft_file": f"stories/drafts/{draft_path.name}",
        "created_at": now_kst_iso(),
        "front_matter": front_matter,
        "change_summary": {
            "grammar_and_structure": changes_made,
            "fact_check_items": fact_checks,
            "suggestions": suggestions,
        },
        "diff": "\n".join(diff_lines),
    }
    review_path.write_text(json.dumps(review_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return review_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Transform raw story into Hugo Markdown draft.")
    parser.add_argument("--input", required=True, help="Path to raw file in stories/raw/")
    parser.add_argument(
        "--template",
        default="auto",
        choices=["auto", "essay", "experience", "technical-note", "review"],
        help="Content template type",
    )
    parser.add_argument("--title", default=None, help="Explicit post title")
    parser.add_argument("--slug", default=None, help="Explicit URL slug")
    parser.add_argument("--tags", default=None, help="Comma-separated tags")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    args = parser.parse_args()

    raw_path = Path(args.input).resolve()
    tags_list = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None

    report = create_draft_from_raw(
        raw_path=raw_path,
        template=args.template,
        title_override=args.title,
        slug_override=args.slug,
        tags_override=tags_list,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"=== 초안 생성 완료: {report['slug']} ===")
    print(f"- 원본 파일 (보존됨): {report['raw_file']}")
    print(f"- 초안 파일: {report['draft_file']}")
    print(f"- 적용 템플릿: {report['template']}")
    print("- 변경 요약:")
    for item in report["change_summary"]["grammar_and_structure"]:
        print(f"  * {item}")
    if report["change_summary"]["fact_check_items"]:
        print("- [검증 필요] 항목:")
        for fc in report["change_summary"]["fact_check_items"]:
            print(f"  ! {fc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
