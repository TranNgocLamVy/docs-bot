from src.constant import BASE_URL

from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from markdownify import markdownify as html_to_markdown
import re

def normalize_internal_link(href: str) -> str:
    if not href:
        return href

    if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
        return href

    if href.startswith(BASE_URL):
        parsed = urlparse(href)
        return parsed.path + (f"?{parsed.query}" if parsed.query else "") + (f"#{parsed.fragment}" if parsed.fragment else "")

    return href


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")

    for tag in soup.select("script, style, nav, footer, header, iframe"):
        tag.decompose()

    for a in soup.find_all("a"):
        href = a.get("href")
        if href:
            a["href"] = normalize_internal_link(href)

    for img in soup.find_all("img"):
        src = img.get("src")
        if src and src.startswith("/"):
            img["src"] = BASE_URL + src

    return str(soup)


def markdown_cleanup(markdown: str) -> str:
    markdown = markdown.replace("\r\n", "\n")

    markdown = re.sub(r"\n{3,}", "\n\n", markdown)

    markdown = "\n".join(line.rstrip() for line in markdown.splitlines())

    return markdown.strip() + "\n"


def article_to_markdown(article: dict) -> str:
    title = article.get("title") or "Untitled"
    body_html = article.get("body") or ""
    article_url = article.get("html_url") or ""
    article_id = article.get("id") or ""
    updated_at = article.get("updated_at") or ""

    cleaned_html = clean_html(body_html)

    body_md = html_to_markdown(
        cleaned_html,
        heading_style="ATX",
        bullets="-",
        strip=["script", "style"],
    )

    markdown = f"""# {title}

Article URL: {article_url}
Article ID: {article_id}
Updated At: {updated_at}

---

{body_md}
"""

    return markdown_cleanup(markdown)