"""
AgentDB Knowledge Scraper — Blog Scraper
Fetches the latest article from an RSS feed and scrapes its full text.
"""

import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup, Comment

logger = logging.getLogger(__name__)

# Tags that are unlikely to contain main article content
_NOISE_TAGS = {
    "script", "style", "noscript", "nav", "header", "footer",
    "aside", "form", "iframe", "button", "svg", "figure",
    "advertisement", "ads",
}

# CSS class/id patterns that typically indicate non-content regions
_NOISE_PATTERNS = re.compile(
    r"(nav|navbar|sidebar|footer|header|cookie|banner|popup|modal|"
    r"social|share|comment|related|recommend|subscribe|newsletter|"
    r"advert|sponsor|promo|widget|menu|breadcrumb)",
    re.IGNORECASE,
)

# Candidate selectors tried in order for main content extraction
_CONTENT_SELECTORS = [
    "article",
    "main",
    '[role="main"]',
    ".post-content",
    ".article-content",
    ".article-body",
    ".entry-content",
    ".post-body",
    ".story-body",
    ".content-body",
    "#content",
    ".content",
]

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AgentDB-Scraper/1.0; "
        "+https://agentdb.dev/scraper)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_latest_article(rss_url: str, source_name: str) -> Optional[dict]:
    """
    Parse an RSS/Atom feed and return metadata for the latest entry.

    Args:
        rss_url: Full URL to the RSS or Atom feed.
        source_name: Human-readable name used for logging.

    Returns:
        Dict with keys ``title`` and ``url``, or None on failure.
    """
    logger.info("Fetching RSS feed for %s: %s", source_name, rss_url)
    try:
        feed = feedparser.parse(rss_url)
    except Exception as exc:
        logger.error("Error parsing RSS feed for %s: %s", source_name, exc)
        return None

    if feed.bozo and not feed.entries:
        logger.warning(
            "RSS feed for %s returned a bozo error and no entries: %s",
            source_name,
            getattr(feed, "bozo_exception", "unknown"),
        )
        return None

    if not feed.entries:
        logger.warning("No entries found in RSS feed for %s", source_name)
        return None

    entry = feed.entries[0]
    title = (entry.get("title") or "").strip() or "Untitled"
    url = (entry.get("link") or entry.get("url") or "").strip()

    if not url:
        logger.warning("Latest entry for %s has no URL", source_name)
        return None

    logger.info("Latest article for %s: '%s' (%s)", source_name, title, url)

    # For YouTube RSS feeds, extract the video description from the entry
    # (transcript scraping is blocked on Railway — description is the best we can do)
    rss_text = ""
    if "youtube.com/feeds" in rss_url:
        rss_text = (
            entry.get("summary")
            or entry.get("description")
            or ""
        ).strip()
        if rss_text:
            logger.info("YouTube RSS description for %s: %d chars", source_name, len(rss_text))
        else:
            logger.warning("YouTube RSS entry for %s has no description", source_name)

    return {"title": title, "url": url, "rss_text": rss_text}


def _is_noise_element(tag) -> bool:
    """Return True if a BS4 tag looks like navigation, ads, or other non-content."""
    try:
        tag_name = tag.name or ""
        if tag_name.lower() in _NOISE_TAGS:
            return True

        for attr in ("class", "id", "role"):
            values = tag.get(attr) or []
            if isinstance(values, str):
                values = [values]
            for val in values:
                if val and _NOISE_PATTERNS.search(val):
                    return True
    except Exception:
        pass
    return False


def _extract_text(soup: BeautifulSoup) -> str:
    """
    Extract clean body text from a BeautifulSoup document.
    Tries known content selectors before falling back to <body>.
    """
    # Remove HTML comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # Remove noise tags up-front
    for tag in soup.find_all(True):
        if _is_noise_element(tag):
            tag.decompose()

    # Try candidate content selectors
    content_el = None
    for selector in _CONTENT_SELECTORS:
        content_el = soup.select_one(selector)
        if content_el:
            break

    root = content_el or soup.find("body") or soup

    # Extract paragraphs / headings in reading order
    paragraphs = []
    for el in root.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"]):
        text = el.get_text(separator=" ", strip=True)
        if text and len(text) > 20:  # skip trivially short fragments
            paragraphs.append(text)

    if paragraphs:
        return "\n\n".join(paragraphs)

    # Last resort: dump all text
    return root.get_text(separator="\n", strip=True)


def scrape_article(url: str) -> Optional[dict]:
    """
    Download and extract the main text content of an article URL.

    Args:
        url: Full URL of the article to scrape.

    Returns:
        Dict with keys ``title``, ``url``, ``text``, or None on failure.
    """
    logger.info("Scraping article: %s", url)
    try:
        with httpx.Client(
            headers=HTTP_HEADERS,
            timeout=20,
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP %s error scraping %s", exc.response.status_code, url)
        return None
    except httpx.HTTPError as exc:
        logger.error("HTTP error scraping %s: %s", url, exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error scraping %s: %s", url, exc)
        return None

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and "xml" not in content_type:
        logger.warning("Non-HTML content type for %s: %s", url, content_type)
        return None

    try:
        soup = BeautifulSoup(response.text, "lxml")
    except Exception:
        soup = BeautifulSoup(response.text, "html.parser")

    # Extract page title from <title> tag as fallback
    page_title = ""
    title_tag = soup.find("title")
    if title_tag:
        page_title = title_tag.get_text(strip=True)

    # Also check og:title / meta title
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        page_title = og_title["content"].strip()

    text = _extract_text(soup)

    if not text or len(text) < 100:
        logger.warning("Extracted text too short for %s (%d chars)", url, len(text))
        return None

    logger.info("Scraped %d chars from %s", len(text), url)
    return {
        "title": page_title,
        "url": url,
        "text": text,
    }


def scrape_blog_source(rss_url: str, source_name: str) -> Optional[dict]:
    """
    High-level helper: get the latest article URL from the feed, then scrape it.

    Args:
        rss_url: Full URL to the RSS or Atom feed.
        source_name: Human-readable source name.

    Returns:
        Dict with keys ``title``, ``url``, ``text``, or None on failure.
    """
    article_meta = get_latest_article(rss_url, source_name)
    if article_meta is None:
        return None

    # YouTube RSS: use the video description directly — don't scrape the video page
    if article_meta.get("rss_text"):
        if len(article_meta["rss_text"]) < 100:
            logger.warning(
                "YouTube description too short for %s (%d chars) — skipping",
                source_name, len(article_meta["rss_text"])
            )
            return None
        return {
            "title": article_meta["title"],
            "url": article_meta["url"],
            "text": article_meta["rss_text"],
        }

    scraped = scrape_article(article_meta["url"])
    if scraped is None:
        return None

    # Prefer RSS title over scraped page title (usually cleaner)
    scraped["title"] = article_meta["title"] or scraped["title"]
    return scraped
