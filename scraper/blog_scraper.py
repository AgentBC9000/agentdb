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


def get_latest_article(
    rss_url: str,
    source_name: str,
    rss_text_mode: bool = False,
) -> Optional[dict]:
    """
    Parse an RSS/Atom feed and return metadata for the latest entry.

    Args:
        rss_url: Full URL to the RSS or Atom feed.
        source_name: Human-readable name used for logging.
        rss_text_mode: When True, extract the RSS entry summary/description
            directly instead of following the article URL.  Use this for
            sources whose article pages are blocked, JS-rendered, or
            paywalled (arXiv, Substack newsletters, TLDR-style digests, etc.)

    Returns:
        Dict with keys ``title``, ``url``, and ``rss_text``, or None on failure.
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

    # Extract RSS entry text when requested (or automatically for YouTube,
    # where transcript scraping is blocked on Railway).
    use_rss_text = rss_text_mode or "youtube.com/feeds" in rss_url
    rss_text = ""
    if use_rss_text:
        # feedparser normalises both <description> and <content:encoded> into
        # entry.summary; fall back through a chain of common field names.
        for field in ("content", "summary", "description", "summary_detail"):
            raw = entry.get(field)
            if isinstance(raw, list) and raw:
                raw = raw[0].get("value", "")
            if raw and isinstance(raw, str):
                rss_text = raw.strip()
                break

        if rss_text:
            # Strip HTML tags that sometimes appear in feed descriptions
            rss_text = BeautifulSoup(rss_text, "html.parser").get_text(
                separator="\n", strip=True
            )
            logger.info(
                "RSS text extracted for %s: %d chars", source_name, len(rss_text)
            )
        else:
            logger.warning("RSS entry for %s has no description text", source_name)

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

    def _para_text(el) -> str:
        """Extract paragraph/heading text from *el*, filtering short fragments."""
        paras = []
        for child in el.find_all(
            ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"]
        ):
            t = child.get_text(separator=" ", strip=True)
            if t and len(t) > 20:
                paras.append(t)
        return "\n\n".join(paras)

    text = _para_text(root)

    # Some pages (Tailwind SPAs, digest newsletters) put content in <div>
    # elements rather than <p> tags.  When a content-selector element was
    # matched but yields very little paragraph text, fall back to the full
    # <body> — first via paragraph extraction, then via a plain text dump.
    MIN_USEFUL = 500
    if content_el and len(text) < MIN_USEFUL:
        body = soup.find("body") or soup
        body_text = _para_text(body)
        if len(body_text) > len(text):
            text = body_text
        # Still short?  Dump all body text (catches div-only layouts).
        if len(text) < MIN_USEFUL:
            text = body.get_text(separator="\n", strip=True)

    if text:
        return text

    # Absolute last resort
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


def scrape_blog_source(
    rss_url: str,
    source_name: str,
    rss_text_mode: bool = False,
) -> Optional[dict]:
    """
    High-level helper: get the latest article URL from the feed, then scrape it.

    Args:
        rss_url: Full URL to the RSS or Atom feed.
        source_name: Human-readable source name.
        rss_text_mode: When True (or when the feed is a YouTube RSS feed),
            use the RSS entry description as the text instead of scraping
            the article page.

    Returns:
        Dict with keys ``title``, ``url``, ``text``, or None on failure.
    """
    article_meta = get_latest_article(rss_url, source_name, rss_text_mode=rss_text_mode)
    if article_meta is None:
        return None

    # RSS text mode (YouTube, arXiv, Substack newsletters, digest feeds…):
    # use the entry description directly — don't try to scrape the target page.
    if article_meta.get("rss_text"):
        if len(article_meta["rss_text"]) < 100:
            logger.warning(
                "RSS description too short for %s (%d chars) — skipping",
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
