# Planning

## Project Goal

Build a small bot that can answer question base on scraped article

The Project has three main parts

1. Scrape articles, clean and parse them in to markdown
2. Upload the markdown files to an AI vector store using API scripts
3. Run the scraper/uploader once per day and only upload new or changed files

## MVP feature / Must finish

- Scrape at least 30 articles
- Convert article content into markdown
- Keep article links, headings, code blocks and useful content
- Remove navigation, footer, ads and unrelated things
- Upload files through API, not manual upload through UI
- Log how many files/chunks are uploaded
- Add a daily job that detects added, updated and skipped articles
- Add a simple README file contain setup, local run steps and sample screenshot

## Workplan 

### 1. Scrapper

* Fetch article list using API
* Fetch article full content including body, title, ...

### 2. Markdown cleanup

* Convert HTML body to Markdown.
* Keep headings, lists, tables, links, images, and code blocks where possible.

### 3. Change tracking

* Store article's metadata like ID, URL, updated date, and content hash.
* Compare the latest scrape with the metadata on each run.
* Mark each article as added, updated, or skipped.

### 4. Vector upload

* Upload only new or changed Markdown files.
* Attach uploaded files to the assistant/vector store.
* Log file count and chunk count if the API returns it.

### 5. Daily job

* Wrap everything in `main.py`.
* Add a Dockerfile.
* Make the container run once and exit.
* Deploy the job to a simple scheduler.