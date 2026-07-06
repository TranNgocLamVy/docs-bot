import requests
import time

BASE_URL = "https://support.optisigns.com"
LOCALE = "en-us"
ARTICLE_LIST_SIZE = 100
ARTICLE_LIMIT = 30


def fetch_articles(limit: int = ARTICLE_LIMIT) -> list[dict]:
    url = f"{BASE_URL}/api/v2/help_center/{LOCALE}/articles.json?page[size]={ARTICLE_LIST_SIZE}"
    articles: list[dict] = []

    while len(articles) < limit:
        response = requests.get(
            url,
            timeout=30,
            headers={
                "Accept": "application/json",
                "User-Agent": "kb-sync-mini/1.0",
            },
        )
        response.raise_for_status()

        data = response.json()
        articles.extend(data.get("articles", []))

        meta = data.get("meta") or {}
        links = data.get("links") or {}

        if meta.get("has_more") and links.get("next"):
            url = links["next"]
        else:
            url = data.get("next_page")

        time.sleep(0.2)

    return articles[:limit]

def main() -> None:
    articles = fetch_articles()
    print(f"Fetched: {len(articles)}")


if __name__ == "__main__":
    main()