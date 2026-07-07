from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Literal
import hashlib
import json

ChangeStatus = Literal["added", "updated", "skipped"]

@dataclass(frozen=True)
class ArticleSnapshot:
    article_id: int
    title: str
    slug: str
    url: str
    updated_at: str
    content_hash: str
    local_path: str

    openai_file_id: str | None = None
    vector_store_file_id: str | None = None
    estimated_chunk_count: int | None = None
    uploaded_at_utc: str | None = None


@dataclass
class ChangeSet:
    added: list[ArticleSnapshot] = field(default_factory=list)
    updated: list[ArticleSnapshot] = field(default_factory=list)
    skipped: list[ArticleSnapshot] = field(default_factory=list)

    @property
    def changed(self) -> list[ArticleSnapshot]:
        return self.added + self.updated

def compute_hash(content: str) -> str:
    normalized = content.replace("\r\n", "\n").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)

def save_manifest(path: Path, manifest: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2, sort_keys=True)

def build_snapshot(article: dict[str, Any], markdown: str,output_path: Path) -> ArticleSnapshot:
    article_id = int(article["id"])

    return ArticleSnapshot(
        article_id=article_id,
        title=article.get("title") or "Untitled",
        slug=output_path.name,
        url=article.get("html_url") or "",
        updated_at=article.get("updated_at") or "",
        content_hash=compute_hash(markdown),
        local_path=str(output_path),
    )


def classify_change(previous_manifest: dict[str, dict[str, Any]], snapshot: ArticleSnapshot) -> ChangeStatus:
    article_key = str(snapshot.article_id)
    previous_snapshot = previous_manifest.get(article_key)

    if previous_snapshot is None:
        return "added"

    if previous_snapshot.get("content_hash") != snapshot.content_hash:
        return "updated"

    return "skipped"


def snapshot_with_upload_metadata(
    snapshot: ArticleSnapshot,
    *,
    openai_file_id: str,
    vector_store_file_id: str,
    estimated_chunk_count: int,
    uploaded_at_utc: str,
) -> ArticleSnapshot:
    return replace(
        snapshot,
        openai_file_id=openai_file_id,
        vector_store_file_id=vector_store_file_id,
        estimated_chunk_count=estimated_chunk_count,
        uploaded_at_utc=uploaded_at_utc,
    )


def add_snapshot_to_manifest(manifest: dict[str, dict[str, Any]], snapshot: ArticleSnapshot) -> None:
    manifest[str(snapshot.article_id)] = asdict(snapshot)


def register_change(change_set: ChangeSet, status: ChangeStatus, snapshot: ArticleSnapshot) -> None:
    if status == "added":
        change_set.added.append(snapshot)
    elif status == "updated":
        change_set.updated.append(snapshot)
    else:
        change_set.skipped.append(snapshot)