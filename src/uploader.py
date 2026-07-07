from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import math
import os
import time

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from src.manifest import ArticleSnapshot

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)

DEFAULT_CHUNK_SIZE_TOKENS = 800
DEFAULT_CHUNK_OVERLAP_TOKENS = 200

@dataclass(frozen=True)
class UploadedFileRecord:
    article_id: int
    local_path: str
    openai_file_id: str
    vector_store_file_id: str
    estimated_chunk_count: int
    uploaded_at_utc: str


@dataclass
class UploadResult:
    vector_store_id: str
    uploaded: list[UploadedFileRecord] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def uploaded_count(self) -> int:
        return len(self.uploaded)

    @property
    def failed_count(self) -> int:
        return len(self.failed)

    @property
    def estimated_chunk_count(self) -> int:
        return sum(item.estimated_chunk_count for item in self.uploaded)

def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY")

    return OpenAI(api_key=api_key)

def get_or_create_vector_store(client: OpenAI) -> str:
    configured_id = (os.getenv("OPENAI_VECTOR_STORE_ID") or "").strip()

    if configured_id:
        return configured_id

    target_name = (os.getenv("OPENAI_VECTOR_STORE_NAME") or "").strip()

    if not target_name:
        raise RuntimeError("Set OPENAI_VECTOR_STORE_ID or OPENAI_VECTOR_STORE_NAME.")

    stores = client.vector_stores.list(limit=100)

    for store in stores.data:
        if store.name == target_name:
            return store.id

    vector_store = client.vector_stores.create(name=target_name)
    return vector_store.id

def estimate_chunk_count(file_path: Path, *, chunk_size_tokens: int, chunk_overlap_tokens: int) -> int:
    text = file_path.read_text(encoding="utf-8")
    token_count = max(1, math.ceil(len(text) / 4))

    effective_chunk_size = chunk_size_tokens - chunk_overlap_tokens

    if token_count <= chunk_size_tokens:
        return 1

    remaining_tokens = token_count - chunk_size_tokens

    return 1 + math.ceil(remaining_tokens / effective_chunk_size)

def delete_previous_vector_file_if_exists(client: OpenAI, *, vector_store_id: str, previous_snapshot: dict[str, Any] | None) -> None:
    if not previous_snapshot:
        return

    previous_vector_store_file_id = previous_snapshot.get("vector_store_file_id")
    previous_openai_file_id = previous_snapshot.get("openai_file_id")

    if previous_vector_store_file_id:
        try:
            client.vector_stores.files.delete(
                vector_store_id=vector_store_id,
                file_id=previous_vector_store_file_id,
            )
            print(f"Deleted previous vector-store file: {previous_vector_store_file_id}")
        except Exception as exc:
            print(
                "Warning: could not delete previous vector-store file "
                f"{previous_vector_store_file_id}: {exc}"
            )

    if previous_openai_file_id:
        try:
            client.files.delete(previous_openai_file_id)
            print(f"Deleted previous OpenAI file: {previous_openai_file_id}")
        except Exception as exc:
            print(
                "Warning: could not delete previous OpenAI file "
                f"{previous_openai_file_id}: {exc}"
            )


def wait_for_vector_store_file(client: OpenAI, *, vector_store_id: str, file_id: str, timeout_seconds: int = 180, poll_interval_seconds: float = 2.0) -> str:
    started_at = time.time()

    while True:
        vector_file = client.vector_stores.files.retrieve(
            vector_store_id=vector_store_id,
            file_id=file_id,
        )

        status = vector_file.status

        if status == "completed":
            return status

        if status in {"failed", "cancelled"}:
            raise RuntimeError(f"Vector-store file processing ended with status: {status}")

        if time.time() - started_at > timeout_seconds:
            raise TimeoutError(
                f"Timed out waiting for vector-store file {file_id}. Last status: {status}"
            )

        time.sleep(poll_interval_seconds)


def upload_one_file(client: OpenAI, *, vector_store_id: str, snapshot: ArticleSnapshot) -> UploadedFileRecord:
    file_path = Path(snapshot.local_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Markdown file does not exist: {file_path}")

    estimated_chunks = estimate_chunk_count(
        file_path,
        chunk_size_tokens=DEFAULT_CHUNK_SIZE_TOKENS,
        chunk_overlap_tokens=DEFAULT_CHUNK_OVERLAP_TOKENS,
    )

    with file_path.open("rb") as file:
        uploaded_file = client.files.create(
            file=file,
            purpose="assistants",
        )

    vector_store_file = client.vector_stores.files.create(
        vector_store_id=vector_store_id,
        file_id=uploaded_file.id,
        attributes={
            "article_id": str(snapshot.article_id),
            "article_url": snapshot.url,
            "content_hash": snapshot.content_hash,
            "slug": snapshot.slug,
        },
        chunking_strategy={
            "type": "static",
            "static": {
                "max_chunk_size_tokens": DEFAULT_CHUNK_SIZE_TOKENS,
                "chunk_overlap_tokens": DEFAULT_CHUNK_OVERLAP_TOKENS,
            },
        },
    )

    wait_for_vector_store_file(
        client,
        vector_store_id=vector_store_id,
        file_id=vector_store_file.id,
    )

    return UploadedFileRecord(
        article_id=snapshot.article_id,
        local_path=snapshot.local_path,
        openai_file_id=uploaded_file.id,
        vector_store_file_id=vector_store_file.id,
        estimated_chunk_count=estimated_chunks,
        uploaded_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def upload_changed_articles(snapshots: list[ArticleSnapshot], *, previous_manifest: dict[str, dict[str, Any]]) -> UploadResult:
    client = get_openai_client()
    vector_store_id = get_or_create_vector_store(client)

    result = UploadResult(vector_store_id=vector_store_id)

    if not snapshots:
        return result

    for snapshot in snapshots:
        try:
            previous_snapshot = previous_manifest.get(str(snapshot.article_id))

            delete_previous_vector_file_if_exists(
                client,
                vector_store_id=vector_store_id,
                previous_snapshot=previous_snapshot,
            )

            uploaded = upload_one_file(
                client,
                vector_store_id=vector_store_id,
                snapshot=snapshot,
            )

            result.uploaded.append(uploaded)

            print(
                "Uploaded "
                f"article_id={snapshot.article_id} "
                f"file={snapshot.local_path} "
                f"openai_file_id={uploaded.openai_file_id} "
                f"chunks_estimated={uploaded.estimated_chunk_count}"
            )

        except Exception as exc:
            result.failed.append((snapshot.local_path, str(exc)))
            print(f"Upload failed: {snapshot.local_path} | {exc}")

    return result