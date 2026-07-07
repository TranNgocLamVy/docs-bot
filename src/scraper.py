from src.constant import BASE_URL, ARTICLE_FETCH_SIZE

from pathlib import Path
import requests
import time

LOCALE = "en-us"

def fetch_articles(limit: int = ARTICLE_FETCH_SIZE) -> list[dict]:
    url = f"{BASE_URL}/api/v2/help_center/{LOCALE}/articles.json?page[size]={100}"
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