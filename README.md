# DocBot

A small support-document bot.

## Project description

This project scrapes support articles, converts them into markdown, uploads them to a vector store through API, and runs as a scheduled daily sync job.

## Project structure

```text
docs/
	planning.md     # work plan for the project
data/
src/
  scraper.py      # fetch article list + article HTML/content
  markdown.py     # clean HTML -> Markdown
  storage.py      # local manifest/hash tracking
  uploader.py     # upload files to OpenAI/Gemini
  main.py         # orchestrates scrape -> diff -> upload -> log
.env.sample
Dockerfile
README.md
```