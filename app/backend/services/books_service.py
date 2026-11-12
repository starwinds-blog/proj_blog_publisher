"""Local book drafts and explicitly approved Hugo navigation snapshots."""
from __future__ import annotations

import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel, Field, field_validator

from scripts.pipeline_core import PROJECT_ROOT, parse_front_matter
from scripts.validate_post import SECRET_PATTERNS


class Book(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    chapters: list[str] = Field(default_factory=list, max_length=500)

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("책 제목을 입력하세요.")
        return value.strip()

    @field_validator("chapters")
    @classmethod
    def safe_unique_chapters(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("같은 책에 글을 중복 추가할 수 없습니다.")
        if any(not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) for slug in value):
            raise ValueError("잘못된 글 식별자입니다.")
        return value


class BooksDocument(BaseModel):
    items: list[Book] = Field(default_factory=list, max_length=100)

    @field_validator("items")
    @classmethod
    def unique_books(cls, value: list[Book]) -> list[Book]:
        if len({book.slug for book in value}) != len(value):
            raise ValueError("책 URL 식별자는 고유해야 합니다.")
        return value


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def load_books() -> BooksDocument:
    path = PROJECT_ROOT / "config/books.json"
    return BooksDocument.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else BooksDocument()


def save_books(document: BooksDocument, known_slugs: set[str]) -> dict:
    for book in document.items:
        if set(book.chapters) - known_slugs:
            raise ValueError("존재하지 않는 글이 포함되어 있습니다. 목록을 새로고침하세요.")
    data = document.model_dump()
    _write_json(PROJECT_ROOT / "config/books.json", data)
    return data


def stage_books(approve: bool = False, dry_run: bool = True) -> dict:
    document = load_books()
    public_books, excluded = [], []
    for book in document.items:
        metadata = book.title + "\n" + book.description
        patterns = [pattern for _, pattern, _, _ in SECRET_PATTERNS]
        patterns.append(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
        if any(re.search(pattern, metadata) for pattern in patterns):
            raise ValueError("책 제목/설명에서 민감정보가 감지되었습니다. 수정 후 다시 승인하세요.")
        chapters = []
        for slug in book.chapters:
            path = PROJECT_ROOT / "site/content/posts" / f"{slug}.md"
            if path.is_file():
                meta, _, errors = parse_front_matter(path.read_text(encoding="utf-8"))
                if not errors and meta.get("draft") is False:
                    chapters.append(slug)
                    continue
            excluded.append({"book": book.slug, "chapter": slug})
        # Empty books stay private until at least one chapter is staged.
        if chapters:
            public_books.append({**book.model_dump(), "chapters": chapters})
    result = {"items": public_books, "excluded": excluded, "dry_run": dry_run}
    if dry_run:
        return result
    if not approve:
        raise ValueError("Books 공개 구성 반영에는 명시적 승인이 필요합니다.")
    site = PROJECT_ROOT / "site"
    install_books_layouts(site)
    index = site / "content/books/_index.md"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text('---\ntitle: Books\n---\n', encoding="utf-8")
    _write_json(site / "data/books.json", {"items": public_books})
    base = site / "layouts/_default/baseof.html"
    if base.exists():
        text = base.read_text(encoding="utf-8")
        marker = '<!-- books-navigation -->'
        if marker not in text:
            text = text.replace('</header>', marker + '\n<nav aria-label="블로그 메뉴"><a href="{{ "books/" | relURL }}">Books</a></nav>\n</header>', 1)
            base.write_text(text, encoding="utf-8")
    return result


def install_books_layouts(site: Path) -> None:
    """Install presentation templates without changing approved book/post data."""
    for source, destination in (("list.html", "layouts/books/list.html"), ("home.html", "layouts/index.html")):
        target = site / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((PROJECT_ROOT / "deploy/hugo-books" / source).read_text(encoding="utf-8"), encoding="utf-8")
