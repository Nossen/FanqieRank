from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Book:
    title: str
    author: str
    reads: str
    intro: str
    cover: str
    url: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Book":
        return cls(
            title=str(payload.get("title") or "未知"),
            author=str(payload.get("author") or "未知"),
            reads=str(payload.get("reads") or "未知"),
            intro=str(payload.get("intro") or "暂无简介"),
            cover=str(payload.get("cover") or ""),
            url=str(payload.get("url") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "author": self.author,
            "reads": self.reads,
            "intro": self.intro,
            "cover": self.cover,
            "url": self.url,
        }


@dataclass(frozen=True)
class CategorySnapshot:
    name: str
    books: list[Book]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CategorySnapshot":
        return cls(
            name=str(payload.get("name") or "未知分类"),
            books=[Book.from_dict(item) for item in payload.get("books", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "books": [book.to_dict() for book in self.books],
        }


@dataclass(frozen=True)
class RawSnapshot:
    date: str
    timezone: str
    generated_at: str
    source: dict[str, str]
    categories: list[CategorySnapshot]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RawSnapshot":
        return cls(
            date=str(payload.get("date") or ""),
            timezone=str(payload.get("timezone") or "Asia/Shanghai"),
            generated_at=str(payload.get("generated_at") or ""),
            source={str(k): str(v) for k, v in dict(payload.get("source") or {}).items()},
            categories=[CategorySnapshot.from_dict(item) for item in payload.get("categories", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "timezone": self.timezone,
            "generated_at": self.generated_at,
            "source": self.source,
            "categories": [category.to_dict() for category in self.categories],
        }


@dataclass(frozen=True)
class CategoryAnalysis:
    name: str
    summary_markdown: str
    hot_themes: list[str] = field(default_factory=list)
    watch_books: list[str] = field(default_factory=list)
    risk_notes: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CategoryAnalysis":
        return cls(
            name=str(payload.get("name") or ""),
            summary_markdown=str(payload.get("summary_markdown") or "").strip(),
            hot_themes=[str(item).strip() for item in payload.get("hot_themes", []) if str(item).strip()],
            watch_books=[str(item).strip() for item in payload.get("watch_books", []) if str(item).strip()],
            risk_notes=str(payload.get("risk_notes") or "").strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "summary_markdown": self.summary_markdown,
            "hot_themes": self.hot_themes,
            "watch_books": self.watch_books,
            "risk_notes": self.risk_notes,
        }


@dataclass(frozen=True)
class CodexAnalysis:
    date: str
    source: str
    categories: list[CategoryAnalysis]
    market_summary: dict[str, str]
    hot_themes: list[str] = field(default_factory=list)
    watch_books: list[dict[str, str]] = field(default_factory=list)
    risk_notes: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CodexAnalysis":
        return cls(
            date=str(payload.get("date") or ""),
            source=str(payload.get("source") or "Codex scheduled automation"),
            categories=[CategoryAnalysis.from_dict(item) for item in payload.get("categories", [])],
            market_summary={str(k): str(v).strip() for k, v in dict(payload.get("market_summary") or {}).items()},
            hot_themes=[str(item).strip() for item in payload.get("hot_themes", []) if str(item).strip()],
            watch_books=[
                {str(k): str(v) for k, v in dict(item).items()}
                for item in payload.get("watch_books", [])
                if isinstance(item, dict)
            ],
            risk_notes=str(payload.get("risk_notes") or "").strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "source": self.source,
            "categories": [category.to_dict() for category in self.categories],
            "market_summary": self.market_summary,
            "hot_themes": self.hot_themes,
            "watch_books": self.watch_books,
            "risk_notes": self.risk_notes,
        }
