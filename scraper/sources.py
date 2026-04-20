"""
AgentDB Knowledge Scraper — Source Definitions

Focus: Startups/IPO, alternative markets, emerging markets (Africa/Asia),
AI/tech (non-legacy), contrarian macro. No legacy wire services.

YouTube RSS feeds yield video title + description only (no transcripts —
Railway IPs are blocked from YouTube transcript APIs).
"""

YOUTUBE_SOURCES = []  # transcript scraping blocked on Railway — use YouTube RSS below

PODCAST_SOURCES = [
    # ── Technology / AI ──────────────────────────────────────────────────────
    {
        "name": "Lex Fridman Podcast",
        "rss_url": "https://lexfridman.com/feed/podcast/",
        "category": "technology_ai",
        "hosts": ["Lex Fridman"],
        "transcript_selectors": [
            "div.transcript",
            "div.entry-content",
            "article .post-content",
        ],
    },
    {
        "name": "Dwarkesh Podcast",
        "rss_url": "https://api.substack.com/feed/podcast/69345.rss",
        "category": "technology_ai",
        "hosts": ["Dwarkesh Patel"],
        "transcript_selectors": [
            "div.body.markup",
            "div.available-content",
            "article",
        ],
    },
    {
        "name": "Hard Fork",
        "rss_url": "https://feeds.simplecast.com/l2i9YnTd",
        "category": "technology_ai",
        "hosts": ["Kevin Roose", "Casey Newton"],
        "transcript_selectors": [],
    },
    {
        "name": "This Week in Tech",
        "rss_url": "https://feeds.twit.tv/twit.xml",
        "category": "technology_ai",
        "hosts": ["Leo Laporte"],
        "transcript_selectors": [
            "div.show-notes",
            "div.episode-notes",
            "article",
        ],
    },
    # ── Startups / IPO ───────────────────────────────────────────────────────
    {
        "name": "Acquired",
        "rss_url": "https://feeds.transistor.fm/acquired",
        "category": "startups_ipo",
        "hosts": ["Ben Gilbert", "David Rosenthal"],
        "transcript_selectors": [
            "div.show-notes",
            "div.episode-notes",
            "article .content",
            "div.post-content",
        ],
    },
    {
        "name": "How I Built This",
        "rss_url": "https://feeds.npr.org/510313/podcast.xml",
        "category": "startups_ipo",
        "hosts": ["Guy Raz"],
        "transcript_selectors": [
            "div.transcript",
            "article",
            "div.storytext",
        ],
    },
    # ── Markets / Finance ────────────────────────────────────────────────────
    {
        "name": "All-In Podcast",
        "rss_url": "https://allinchamathjason.libsyn.com/rss",
        "category": "market_news_alternative",
        "hosts": ["Chamath Palihapitiya", "Jason Calacanis", "David Sacks", "David Friedberg"],
        "transcript_selectors": [],
    },
    {
        "name": "Prof G Markets Podcast",
        "rss_url": "https://feeds.megaphone.fm/profgmarkets",
        "category": "market_news_alternative",
        "hosts": ["Scott Galloway", "Ed Elson"],
        "transcript_selectors": [
            "div.show-notes",
            "article",
            "div.entry-content",
        ],
    },
]

BLOG_SOURCES = [
    # ── Technology / AI (non-legacy) ─────────────────────────────────────────
    {
        "name": "MIT Technology Review",
        "rss_url": "https://www.technologyreview.com/feed/",
        "category": "technology_ai",
    },
    {
        "name": "Ars Technica",
        "rss_url": "https://feeds.arstechnica.com/arstechnica/index",
        "category": "technology_ai",
    },
    {
        "name": "Hacker News",
        "rss_url": "https://hnrss.org/frontpage?link=comments",
        "category": "startups_ipo",
    },
    # ── Startups / IPO ───────────────────────────────────────────────────────
    {
        "name": "Y Combinator Blog",
        "rss_url": "https://www.ycombinator.com/blog/rss.xml",
        "category": "startups_ipo",
    },
    {
        "name": "The Verge",
        "rss_url": "https://www.theverge.com/rss/index.xml",
        "category": "startups_ipo",
    },
    {
        "name": "Wired",
        "rss_url": "https://www.wired.com/feed/rss",
        "category": "technology_ai",
    },
    {
        "name": "Entrepreneur",
        "rss_url": "https://www.entrepreneur.com/latest.rss",
        "category": "startups_ipo",
    },
    {
        "name": "Tech Wire Asia",
        "rss_url": "https://techwireasia.com/feed/",
        "category": "emerging_markets_asia",
    },
    # ── Alternative Markets / Macro ──────────────────────────────────────────
    {
        "name": "Zero Hedge",
        "rss_url": "https://feeds.feedburner.com/zerohedge/feed",
        "category": "market_news_alternative",
    },
    {
        "name": "Wolf Street",
        "rss_url": "https://wolfstreet.com/feed/",
        "category": "market_news_alternative",
    },
    {
        "name": "Econbrowser",
        "rss_url": "https://econbrowser.com/feed",
        "category": "market_news_alternative",
    },
    {
        "name": "A Wealth of Common Sense",
        "rss_url": "https://awealthofcommonsense.com/feed/",
        "category": "market_news_alternative",
    },
    {
        "name": "The Big Picture",
        "rss_url": "https://ritholtz.com/feed/",
        "category": "market_news_alternative",
    },
    {
        "name": "The Daily Upside",
        "rss_url": "https://www.thedailyupside.com/feed/",
        "category": "market_news",
    },
    # ── Emerging Markets ─────────────────────────────────────────────────────
    {
        "name": "Rest of World",
        "rss_url": "https://restofworld.org/feed/latest/",
        "category": "emerging_markets",
    },
    {
        "name": "TechCabal",
        "rss_url": "https://techcabal.com/feed/",
        "category": "emerging_markets_africa",
    },
    {
        "name": "Techpoint Africa",
        "rss_url": "https://techpoint.africa/feed/",
        "category": "emerging_markets_africa",
    },
]

# YouTube RSS — video title + description from RSS entry (no transcript).
YOUTUBE_RSS_SOURCES = [
    {
        "name": "Y Combinator",
        "rss_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCcefcZRL2oaA_uBNeo5UOWg",
        "category": "startups_ipo",
    },
]
