from constant import BASE_URL, LOCALE, ARTICLE_LIST_SIZE, ARTICLE_FETCH_SIZE
from utils import get_article_filename

from pathlib import Path
import requests
import time

def fetch_articles(limit: int = ARTICLE_FETCH_SIZE) -> list[dict]:
    url = f"{BASE_URL}/api/v2/help_center/{LOCALE}/articles.json?page[size]={ARTICLE_LIST_SIZE}"
    articles: list[dict] = []

    while len(articles) < limit:
        response = requests.get(url, headers={ "Accept": "application/json" })
        response.raise_for_status()

        data = response.json()
        articles.extend(data.get("articles", []))

        meta = data.get("meta") or {}
        links = data.get("links") or {}

        if meta.get("has_more") and links.get("next"):
            url = links["next"]
        else:
            url = data.get("next_page")

    return articles[:limit]

def main() -> None:
    articles = fetch_articles()

    OUTPUT_DIR = Path("data/raw")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for article in articles:
        output_path = OUTPUT_DIR / get_article_filename(article)
        output_path.write_text(str(article), encoding="utf-8")

if __name__ == "__main__":
    main()