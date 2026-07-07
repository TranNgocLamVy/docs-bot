from __future__ import annotations

from pathlib import Path

from tqdm import tqdm

from src.manifest import (
    ChangeSet,
    add_snapshot_to_manifest,
    build_snapshot,
    classify_change,
    load_manifest,
    register_change,
    save_manifest,
    snapshot_with_upload_metadata
)
from src.constant import ARTICLE_FETCH_SIZE
from src.md_parser import article_to_markdown
from src.scraper import fetch_articles
from src.uploader import upload_changed_articles

OUTPUT_DIR = Path("data/articles")
MANIFEST_PATH = Path("data/articles_manifest.json")

def get_article_filename(article: dict) -> str:
    title = article.get("title") or str(article.get("id"))
    article_id = article.get("id")
    return f"{slugify(title)}-{article_id}.md"

def run() -> ChangeSet:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    articles = fetch_articles()

    previous_manifest = load_manifest(MANIFEST_PATH)
    next_manifest = dict(previous_manifest)

    change_set = ChangeSet()

    for article in tqdm(articles, desc="Processing articles"):
        markdown = article_to_markdown(article)
        output_path = OUTPUT_DIR / get_article_filename(article)

        snapshot = build_snapshot(
            article=article,
            markdown=markdown,
            output_path=output_path,
        )

        status = classify_change(
            previous_manifest=previous_manifest,
            snapshot=snapshot,
        )

        if status in {"added", "updated"}:
            output_path.write_text(markdown, encoding="utf-8")

        register_change(change_set, status, snapshot)

    upload_result = upload_changed_articles(
        change_set.changed,
        previous_manifest=previous_manifest,
    )

    uploaded_by_article_id = {
        record.article_id: record
        for record in upload_result.uploaded
    }

    for snapshot in change_set.changed:
        uploaded = uploaded_by_article_id.get(snapshot.article_id)

        if not uploaded:
            continue

        snapshot_with_upload = snapshot_with_upload_metadata(
            snapshot,
            openai_file_id=uploaded.openai_file_id,
            vector_store_file_id=uploaded.vector_store_file_id,
            estimated_chunk_count=uploaded.estimated_chunk_count,
            uploaded_at_utc=uploaded.uploaded_at_utc,
        )

        add_snapshot_to_manifest(next_manifest, snapshot_with_upload)

    save_manifest(MANIFEST_PATH, next_manifest)

    print("")
    print("Scrape/upload completed")
    print(f"added={len(change_set.added)}")
    print(f"updated={len(change_set.updated)}")
    print(f"skipped={len(change_set.skipped)}")
    print(f"uploaded_files={upload_result.uploaded_count}")
    print(f"failed_uploads={upload_result.failed_count}")
    print(f"estimated_uploaded_chunks={upload_result.estimated_chunk_count}")
    print(f"vector_store_id={upload_result.vector_store_id}")

    if upload_result.failed:
        print("")
        print("Failed uploads:")
        for file_path, error in upload_result.failed:
            print(f"- {file_path}: {error}")

    return change_set


def main() -> None:
    run()


if __name__ == "__main__":
    main()