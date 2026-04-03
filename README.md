# Substack to Markdown

A Python CLI tool that scrapes articles from any Substack newsletter and converts them to clean Markdown files with YAML frontmatter.

## Features

- Fetches all articles from a Substack newsletter's archive
- Converts HTML content to clean, readable Markdown
- Adds YAML frontmatter with metadata (title, date, URL, audience)
- Generates an index file linking all scraped articles
- Rate-limited requests to be respectful to servers
- Configurable output directory, article limit, and request delay

## Installation

```bash
git clone https://github.com/1anthanum/substack-to-markdown.git
cd substack-to-markdown
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# Scrape all articles from a newsletter
python scraper.py https://example.substack.com

# Scrape with custom output directory
python scraper.py https://example.substack.com -o my_articles

# Limit to 10 most recent articles
python scraper.py https://example.substack.com -n 10

# Adjust delay between requests (default 1s)
python scraper.py https://example.substack.com -d 2.0

# Skip YAML frontmatter
python scraper.py https://example.substack.com --no-frontmatter
```

### Python API

```python
from scraper import SubstackScraper

scraper = SubstackScraper(
    base_url="https://example.substack.com",
    output_dir="articles",
    delay=1.5
)

# Scrape and save all articles
saved_files = scraper.scrape_and_save(limit=20)

# Generate index
scraper.export_index(saved_files)
```

### Output Format

Each article is saved as a Markdown file with the naming convention `YYYY-MM-DD-article-title.md`:

```markdown
---
title: "Article Title"
subtitle: "Optional subtitle"
date: 2024-03-15
url: https://example.substack.com/p/article-slug
audience: everyone
---

# Article Title

*Optional subtitle*

Article content converted to clean Markdown...
```

An `INDEX.md` file is also generated, listing all scraped articles with links.

## Project Structure

```
substack-to-markdown/
├── scraper.py          # Main scraper module
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── output/             # Default output directory (created on run)
```

## How It Works

1. **Archive Discovery**: Uses Substack's `/api/v1/archive` endpoint to discover all published posts
2. **Content Extraction**: Fetches each article's HTML and extracts the body content using BeautifulSoup
3. **Markdown Conversion**: Converts HTML to Markdown using `html2text` with optimized settings
4. **File Output**: Saves each article with date-prefixed filenames and YAML frontmatter

## Tech Stack

- **Python 3.10+**
- **requests** — HTTP client
- **BeautifulSoup4** — HTML parsing
- **html2text** — HTML to Markdown conversion

## License

MIT
