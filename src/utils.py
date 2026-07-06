from slugify import slugify

def get_article_filename(article: dict) -> str:
    title = article.get("title") or str(article.get("id"))
    article_id = article.get("id")
    return f"{slugify(title)}-{article_id}.md"