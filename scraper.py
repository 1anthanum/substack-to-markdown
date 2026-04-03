"""
Substack to Markdown Scraper
Scrapes articles from any Substack newsletter and converts them to clean Markdown files.

Author: Xuyang Chen
License: MIT
"""

import requests
from bs4 import BeautifulSoup
import html2text
import os
import re
import json
import time
import argparse
from urllib.parse import urljoin
from datetime import datetime


class SubstackScraper:
    """Scrapes articles from a Substack newsletter and saves them as Markdown."""

    def __init__(self, base_url: str, output_dir: str = "output", delay: float = 1.0):
        """
        Initialize the scraper.

        Args:
            base_url: The Substack newsletter URL (e.g., https://example.substack.com)
            output_dir: Directory to save Markdown files
            delay: Delay between requests in seconds (be respectful)
        """
        self.base_url = base_url.rstrip("/")
        self.output_dir = output_dir
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        })

        # Configure html2text converter
        self.converter = html2text.HTML2Text()
        self.converter.body_width = 0  # No line wrapping
        self.converter.protect_links = True
        self.converter.unicode_snob = True
        self.converter.images_to_alt = True
        self.converter.single_line_break = False

        os.makedirs(output_dir, exist_ok=True)

    def get_archive_posts(self, limit: int = None) -> list[dict]:
        """
        Fetch all posts from the Substack archive API.

        Args:
            limit: Maximum number of posts to fetch (None for all)

        Returns:
            List of post metadata dictionaries
        """
        posts = []
        offset = 0
        batch_size = 12

        print(f"Fetching archive from {self.base_url}...")

        while True:
            api_url = f"{self.base_url}/api/v1/archive?sort=new&offset={offset}&limit={batch_size}"
            try:
                response = self.session.get(api_url, timeout=15)
                response.raise_for_status()
                batch = response.json()
            except requests.RequestException as e:
                print(f"  Error fetching archive at offset {offset}: {e}")
                break
            except json.JSONDecodeError:
                print(f"  Error parsing JSON at offset {offset}")
                break

            if not batch:
                break

            posts.extend(batch)
            print(f"  Fetched {len(posts)} posts so far...")

            if limit and len(posts) >= limit:
                posts = posts[:limit]
                break

            offset += batch_size
            time.sleep(self.delay)

        print(f"Found {len(posts)} total posts.\n")
        return posts

    def fetch_article_html(self, post_url: str) -> str | None:
        """
        Fetch the full HTML content of a single article.

        Args:
            post_url: URL of the article

        Returns:
            HTML string of the article body, or None on failure
        """
        try:
            response = self.session.get(post_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Substack article content is in the .body class or .post-content
            body = soup.find("div", class_="body") or \
                   soup.find("div", class_="post-content") or \
                   soup.find("div", class_="available-content")

            if body:
                return str(body)
            return None

        except requests.RequestException as e:
            print(f"  Error fetching {post_url}: {e}")
            return None

    def html_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML content to clean Markdown.

        Args:
            html_content: Raw HTML string

        Returns:
            Cleaned Markdown string
        """
        markdown = self.converter.handle(html_content)

        # Clean up excessive whitespace
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)
        markdown = markdown.strip()

        return markdown

    @staticmethod
    def sanitize_filename(title: str, max_length: int = 80) -> str:
        """
        Create a safe filename from an article title.

        Args:
            title: Article title
            max_length: Maximum filename length

        Returns:
            Sanitized filename string
        """
        # Remove or replace unsafe characters
        safe = re.sub(r'[<>:"/\\|?*]', "", title)
        safe = re.sub(r"\s+", "-", safe)
        safe = re.sub(r"-+", "-", safe)
        safe = safe.strip("-").lower()

        if len(safe) > max_length:
            safe = safe[:max_length].rstrip("-")

        return safe or "untitled"

    def build_frontmatter(self, post: dict) -> str:
        """
        Build YAML frontmatter metadata for a post.

        Args:
            post: Post metadata from the archive API

        Returns:
            YAML frontmatter string
        """
        title = post.get("title", "Untitled")
        subtitle = post.get("subtitle", "")
        date = post.get("post_date", "")[:10]
        slug = post.get("slug", "")
        url = post.get("canonical_url", "")
        audience = post.get("audience", "everyone")

        lines = [
            "---",
            f'title: "{title}"',
        ]
        if subtitle:
            lines.append(f'subtitle: "{subtitle}"')
        if date:
            lines.append(f"date: {date}")
        if url:
            lines.append(f"url: {url}")
        lines.append(f"audience: {audience}")
        lines.append("---")

        return "\n".join(lines)

    def scrape_and_save(self, limit: int = None, include_frontmatter: bool = True) -> list[str]:
        """
        Main method: scrape all articles and save as Markdown files.

        Args:
            limit: Maximum number of articles to scrape
            include_frontmatter: Whether to include YAML frontmatter

        Returns:
            List of saved file paths
        """
        posts = self.get_archive_posts(limit=limit)
        saved_files = []

        for i, post in enumerate(posts, 1):
            title = post.get("title", "Untitled")
            post_url = post.get("canonical_url") or f"{self.base_url}/p/{post.get('slug', '')}"
            date_str = post.get("post_date", "")[:10]

            print(f"[{i}/{len(posts)}] {title}")

            # Fetch article HTML
            html_content = self.fetch_article_html(post_url)
            if not html_content:
                print(f"  Skipped (could not fetch content)")
                continue

            # Convert to Markdown
            markdown_body = self.html_to_markdown(html_content)

            # Build full document
            parts = []
            if include_frontmatter:
                parts.append(self.build_frontmatter(post))
                parts.append("")

            parts.append(f"# {title}")
            if post.get("subtitle"):
                parts.append(f"\n*{post['subtitle']}*")
            parts.append("")
            parts.append(markdown_body)

            full_markdown = "\n".join(parts)

            # Save to file
            safe_name = self.sanitize_filename(title)
            if date_str:
                filename = f"{date_str}-{safe_name}.md"
            else:
                filename = f"{safe_name}.md"

            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_markdown)

            saved_files.append(filepath)
            print(f"  Saved: {filename}")

            time.sleep(self.delay)

        return saved_files

    def export_index(self, saved_files: list[str]) -> str:
        """
        Create an index file linking to all scraped articles.

        Args:
            saved_files: List of saved Markdown file paths

        Returns:
            Path to the index file
        """
        index_path = os.path.join(self.output_dir, "INDEX.md")
        lines = [
            f"# Archive Index",
            f"\nSource: {self.base_url}",
            f"Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Total articles: {len(saved_files)}\n",
            "---\n",
        ]

        for fp in saved_files:
            basename = os.path.basename(fp)
            name_no_ext = basename.replace(".md", "").replace("-", " ").title()
            lines.append(f"- [{name_no_ext}]({basename})")

        with open(index_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return index_path


def main():
    parser = argparse.ArgumentParser(
        description="Scrape a Substack newsletter and convert articles to Markdown."
    )
    parser.add_argument(
        "url",
        help="Substack newsletter URL (e.g., https://example.substack.com)"
    )
    parser.add_argument(
        "-o", "--output",
        default="output",
        help="Output directory (default: output)"
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=None,
        help="Maximum number of articles to scrape"
    )
    parser.add_argument(
        "-d", "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--no-frontmatter",
        action="store_true",
        help="Exclude YAML frontmatter from output files"
    )

    args = parser.parse_args()

    scraper = SubstackScraper(
        base_url=args.url,
        output_dir=args.output,
        delay=args.delay,
    )

    saved = scraper.scrape_and_save(
        limit=args.limit,
        include_frontmatter=not args.no_frontmatter,
    )

    if saved:
        index = scraper.export_index(saved)
        print(f"\nDone! {len(saved)} articles saved to '{args.output}/'")
        print(f"Index file: {index}")
    else:
        print("\nNo articles were saved.")


if __name__ == "__main__":
    main()
