"""
AgentDB Knowledge Scraper — Source Definitions

Focus: Startups/IPO, alternative markets, emerging markets (Africa/Asia),
AI/tech (non-legacy), contrarian macro. No legacy wire services.

YouTube RSS feeds yield video title + description only (no transcripts —
Railway IPs are blocked from YouTube transcript APIs). Description-based
summaries still provide useful signal for channels with detailed descriptions.
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
        "name": "20VC",
        "rss_url": "https://rss.art19.com/the-twenty-minute-vc",
        "category": "startups_ipo",
        "hosts": ["Harry Stebbings"],
        "transcript_selectors": [
            "div.show-notes",
            "article",
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
        "rss_url": "https://hnrss.org/frontpage",
        "category": "startups_ipo",
    },
    # ── Startups / IPO ───────────────────────────────────────────────────────
    {
        "name": "Y Combinator Blog",
        "rss_url": "https://www.ycombinator.com/blog/rss.xml",
        "category": "startups_ipo",
    },
    {
        "name": "Not Boring",
        "rss_url": "https://www.notboring.co/feed",
        "category": "startups_ipo",
    },
    {
        "name": "The Generalist",
        "rss_url": "https://www.thegeneralist.io/feed",
        "category": "startups_ipo",
    },
    {
        "name": "Newcomer",
        "rss_url": "https://www.newcomer.co/feed",
        "category": "startups_ipo",
    },
    {
        "name": "Sifted",
        "rss_url": "https://sifted.eu/rss",
        "category": "startups_ipo",
    },
    # ── Alternative Markets / Macro ──────────────────────────────────────────
    {
        "name": "Zero Hedge",
        "rss_url": "https://feeds.feedburner.com/zerohedge/feed",
        "category": "market_news_alternative",
    },
    {
        "name": "Lyn Alden",
        "rss_url": "https://www.lynalden.com/feed/",
        "category": "market_news_alternative",
    },
    {
        "name": "Of Two Minds",
        "rss_url": "https://www.oftwominds.com/blog.rss",
        "category": "market_news_alternative",
    },
    {
        "name": "Prof G Markets",
        "rss_url": "https://profgmarkets.substack.com/feed",
        "category": "market_news_alternative",
    },
    {
        "name": "Epsilon Theory",
        "rss_url": "https://www.epsilontheory.com/?feed=rss2",
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
        "name": "e27",
        "rss_url": "https://e27.co/feed/",
        "category": "emerging_markets_asia",
    },
]

# YouTube RSS — video title + description from RSS entry (no transcript).
# Processed via blog pipeline with rss_description fallback in blog_scraper.
# Note: channel IDs must be exact — wrong IDs return malformed XML error pages.
YOUTUBE_RSS_SOURCES = [
    {
        "name": "Y Combinator",
        "rss_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCcefcZRL2oaA_uBNeo5UOWg",
        "category": "startups_ipo",
    },
]
