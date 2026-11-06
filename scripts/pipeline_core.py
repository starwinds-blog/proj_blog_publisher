"""Core pipeline utilities for AI Story-to-Blog Publisher (standard library only)."""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
STORIES_DIR = PROJECT_ROOT / "stories"
RAW_DIR = STORIES_DIR / "raw"
DRAFTS_DIR = STORIES_DIR / "drafts"
APPROVED_DIR = STORIES_DIR / "approved"
RECORDS_DIR = STORIES_DIR / "records"
SITE_DIR = PROJECT_ROOT / "site"
SITE_POSTS_DIR = SITE_DIR / "content" / "posts"
SITE_IMAGES_DIR = SITE_DIR / "static" / "images"
PUBLICATIONS_FILE = RECORDS_DIR / "publications.json"


def ensure_directories() -> None:
    for d in (RAW_DIR, DRAFTS_DIR, APPROVED_DIR, RECORDS_DIR, SITE_POSTS_DIR, SITE_IMAGES_DIR):
        d.mkdir(parents=True, exist_ok=True)


def now_kst_iso() -> str:
    return dt.datetime.now(KST).isoformat(timespec="seconds")


def slugify(text: str, fallback: str = "story-post") -> str:
    """Create a safe URL slug. Preserves ASCII alphanumerics and hyphens; converts spaces."""
    lowered = text.strip().lower()
    # Keep ASCII letters/digits/hyphens
    ascii_part = re.sub(r"[^a-z0-9\s_-]", "", lowered)
    ascii_part = re.sub(r"[\s_]+", "-", ascii_part).strip("-")
    ascii_part = re.sub(r"-{2,}", "-", ascii_part)
    if ascii_part and len(ascii_part) >= 3:
        return ascii_part[:64]

    # Map common Korean keywords or hash suffix for deterministic ASCII slug
    keyword_map = {
        "첫": "first",
        "시작": "start",
        "블로그": "blog",
        "테스트": "test",
        "회고": "retrospect",
        "경험": "experience",
        "기술": "tech",
        "노트": "note",
        "리뷰": "review",
        "후기": "review",
        "메모": "memo",
        "개발": "dev",
        "일기": "diary",
        "생각": "thought",
    }
    tokens: List[str] = []
    for ko, en in keyword_map.items():
        if ko in text and en not in tokens:
            tokens.append(en)
    if ascii_part:
        tokens.append(ascii_part)
    if tokens:
        candidate = "-".join(tokens)
        candidate = re.sub(r"-{2,}", "-", candidate).strip("-")
        if len(candidate) >= 3:
            return candidate[:64]

    # Deterministic short suffix from unicode codepoints
    checksum = sum(ord(ch) * (idx + 1) for idx, ch in enumerate(text)) % 100000
    return f"{fallback}-{checksum:05d}"


def parse_front_matter(markdown_text: str) -> Tuple[Dict[str, Any], str, List[str]]:
    """Parse YAML front matter delimited by --- using standard library."""
    errors: List[str] = []
    text = markdown_text.lstrip("\ufeff")
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return {}, markdown_text, ["Front Matter 시작 구분자('---')가 없습니다."]

    lines = text.splitlines(keepends=True)
    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break

    if end_idx is None:
        return {}, markdown_text, ["Front Matter 종료 구분자('---')가 없습니다."]

    fm_lines = [line.rstrip("\r\n") for line in lines[1:end_idx]]
    body = "".join(lines[end_idx + 1 :]).lstrip("\r\n")
    meta: Dict[str, Any] = {}
    current_list_key: Optional[str] = None

    for raw_line in fm_lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_list_key:
            item_val = _parse_scalar(stripped[2:].strip())
            if isinstance(meta.get(current_list_key), list):
                meta[current_list_key].append(item_val)
            continue

        if ":" not in raw_line:
            errors.append(f"잘못된 Front Matter 라인 형식: {raw_line}")
            continue

        key, val_str = raw_line.split(":", 1)
        key = key.strip()
        val_str = val_str.strip()
        current_list_key = None

        if val_str == "":
            meta[key] = []
            current_list_key = key
        elif val_str.startswith("[") and val_str.endswith("]"):
            inner = val_str[1:-1].strip()
            if not inner:
                meta[key] = []
            else:
                items = [_parse_scalar(part.strip()) for part in inner.split(",") if part.strip()]
                meta[key] = items
        else:
            meta[key] = _parse_scalar(val_str)

    return meta, body, errors


def _parse_scalar(val: str) -> Any:
    # Strip trailing inline YAML comments outside quotes (e.g. `"user"  # comment`)
    val = re.sub(r'^(".*?"|\'.*?\'|[^#]*?)\s+#.*$', r"\1", val).strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1].replace('\\"', '"')
    low = val.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if re.fullmatch(r"-?\d+", val):
        try:
            return int(val)
        except ValueError:
            return val
    return val


def format_front_matter(meta: Dict[str, Any]) -> str:
    """Serialize front matter dict into clean Hugo YAML front matter."""
    ordered_keys = ["title", "date", "draft", "description", "tags", "categories", "slug"]
    extra_keys = [k for k in meta.keys() if k not in ordered_keys]
    lines = ["---"]
    for key in ordered_keys + extra_keys:
        if key not in meta:
            continue
        val = meta[key]
        if isinstance(val, bool):
            lines.append(f"{key}: {'true' if val else 'false'}")
        elif isinstance(val, list):
            escaped_items = [json.dumps(str(x), ensure_ascii=False) for x in val]
            lines.append(f"{key}: [{', '.join(escaped_items)}]")
        elif isinstance(val, (int, float)):
            lines.append(f"{key}: {val}")
        else:
            s_val = str(val)
            # Dates like 2026-11-06T00:00:00+09:00 can remain unquoted in YAML
            if key == "date" and re.match(r"^\d{4}-\d{2}-\d{2}", s_val):
                lines.append(f"{key}: {s_val}")
            else:
                lines.append(f"{key}: {json.dumps(s_val, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def build_markdown_post(meta: Dict[str, Any], body: str) -> str:
    fm = format_front_matter(meta)
    clean_body = body.strip()
    return f"{fm}\n\n{clean_body}\n"


def load_publishing_config() -> Dict[str, Any]:
    """Load config/publishing.yaml if present, falling back to config/publishing.example.yaml."""
    ensure_directories()
    custom_path = CONFIG_DIR / "publishing.yaml"
    example_path = CONFIG_DIR / "publishing.example.yaml"
    defaults: Dict[str, Any] = {
        "site_title": "My Story & Tech Blog",
        "site_description": "자유 형식 메모와 경험을 기록하는 로컬 우선 블로그",
        "author_name": "",
        "language_code": "ko-kr",
        "github_owner": "",
        "github_repo": "",
        "repo_type": "user",
        "base_url": "http://localhost:1313/",
        "branch": "main",
        "default_dry_run": True,
        "approval_mode": "cli_or_dashboard_explicit",
        "allowlist_dirs": ["content/posts", "static/images"],
    }
    target = custom_path if custom_path.exists() else example_path
    if not target.exists():
        return defaults

    raw = target.read_text(encoding="utf-8")
    wrapped = f"---\n{raw}\n---\n"
    parsed, _, _ = parse_front_matter(wrapped)
    merged = {**defaults, **parsed}
    return merged


def save_publishing_config(data: Dict[str, Any]) -> Path:
    """Save user publishing configuration to config/publishing.yaml."""
    ensure_directories()
    custom_path = CONFIG_DIR / "publishing.yaml"
    current = load_publishing_config()
    current.update(data)
    lines = ["# Local Publishing Configuration (Managed by Dashboard / CLI)"]
    for k, v in current.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {json.dumps(str(item), ensure_ascii=False)}")
        else:
            lines.append(f"{k}: {json.dumps(str(v), ensure_ascii=False)}")
    custom_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return custom_path


def load_publications_registry() -> Dict[str, Any]:
    ensure_directories()
    if not PUBLICATIONS_FILE.exists():
        return {"version": "1.0", "items": {}}
    try:
        return json.loads(PUBLICATIONS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": "1.0", "items": {}}


def save_publications_registry(registry: Dict[str, Any]) -> None:
    ensure_directories()
    PUBLICATIONS_FILE.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
