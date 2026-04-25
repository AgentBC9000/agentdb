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
        "name": "Import AI",
        "rss_url": "https://importai.substack.com/feed",
        "category": "technology_ai",
        "rss_text_mode": True,  # Substack full-post content is in the RSS entry
    },
    {
        "name": "Platformer",
        "rss_url": "https://www.platformer.news/feed",
        "category": "technology_ai",
    },
    {
        "name": "TLDR Tech",
        "rss_url": "https://tldr.tech/api/rss/tech",
        "category": "technology_ai",
        # No RSS description — article page scraped instead (Tailwind div layout
        # handled by _extract_text() body fallback in blog_scraper.py)
    },
    {
        "name": "arXiv AI",
        "rss_url": "https://export.arxiv.org/rss/cs.AI",
        "category": "research_ai",
        "rss_text_mode": True,  # Paper abstract is in the RSS entry
    },
    {
        "name": "404 Media",
        "rss_url": "https://www.404media.co/feed",
        "category": "technology_ai",
    },
    # ── Startups / IPO ───────────────────────────────────────────────────────
    {
        "name": "The Generalist",
        "rss_url": "https://www.generalist.com/feed",
        "category": "startups_ipo",
        "rss_text_mode": True,  # Paid newsletter — best content accessible via RSS entry
    },
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
        "name": "The Hindu Business Line",
        "rss_url": "https://www.thehindubusinessline.com/feeder/default.rss",
        "category": "emerging_markets_asia",
    },
    {
        "name": "TechCrunch",
        "rss_url": "https://techcrunch.com/feed/",
        "category": "startups_ipo",
    },
    # ── Alternative Markets / Macro ──────────────────────────────────────────
    {
        "name": "Zero Hedge",
        "rss_url": "https://feeds.feedburner.com/zerohedge/feed",
        "category": "market_news_alternative",
    },
    {
        "name": "Calculated Risk",
        "rss_url": "https://feeds.feedburner.com/CalculatedRisk",
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
    {
        "name": "Asymco",
        "rss_url": "https://asymco.com/feed/",
        "category": "market_news_alternative",
    },
    {
        "name": "Noahpinion",
        "rss_url": "https://www.noahpinion.blog/feed",
        "category": "market_news_alternative",
    },
    # ── Policy / Regulation ──────────────────────────────────────────────────
    {
        "name": "Politico Europe",
        "rss_url": "https://www.politico.eu/feed/",
        "category": "policy_regulation",
        "rss_text_mode": True,  # Site often blocks scrapers; RSS summary is reliable
    },
    {
        "name": "arXiv Policy",
        "rss_url": "https://export.arxiv.org/rss/cs.CY",
        "category": "policy_regulation",
        "rss_text_mode": True,  # Paper abstract is in the RSS entry
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
    {
        "name": "Disrupt Africa",
        "rss_url": "https://disrupt-africa.com/feed/",
        "category": "emerging_markets_africa",
    },
    {
        "name": "Mint (India)",
        "rss_url": "https://www.livemint.com/rss/news",
        "category": "emerging_markets_asia",
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
