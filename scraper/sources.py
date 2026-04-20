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
        "name": "TWiT Intelligent Machines",
        "rss_url": "https://feeds.twit.tv/intelligentmachines.xml",
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
        "name": "My First Million",
        "rss_url": "https://feeds.megaphone.fm/MFM4954199243",
        "category": "startups_ipo",
        "hosts": ["Sam Parr", "Shaan Puri"],
        "transcript_selectors": [
            "div.show-notes",
            "article",
        ],
    },
    {
        "name": "20VC",
        "rss_url": "https://feeds.simplecast.com/4T39_jAj",
        "category": "startups_ipo",
        "hosts": ["Harry Stebbings"],
        "transcript_selectors": [
            "div.show-notes",
            "article",
        ],
    },
    {
        "name": "Founders Podcast",
        "rss_url": "https://feeds.simplecast.com/OGETTELl",
        "category": "startups_ipo",
        "hosts": ["David Senra"],
        "transcript_selectors": [
            "div.show-notes",
            "article",
            "div.entry-content",
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
        "name": "Invest Like the Best",
        "rss_url": "https://feeds.joincolossus.com/invest_like_the_best",
        "category": "market_news",
        "hosts": ["Patrick O'Shaughnessy"],
        "transcript_selectors": [
            "div.show-notes",
            "article",
        ],
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
        "name": "Wired AI",
        "rss_url": "https://www.wired.com/feed/tag/artificial-intelligence/latest/rss",
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
        "name": "Crunchbase News",
        "rss_url": "https://news.crunchbase.com/feed/",
        "category": "startups_ipo",
    },
    # ── Alternative Markets / Macro ──────────────────────────────────────────
    {
        "name": "Zero Hedge",
        "rss_url": "https://feeds.feedburner.com/zerohedge/feed",
        "category": "market_news_alternative",
    },
    {
        "name": "Rebel Capitalist",
        "rss_url": "https://rebelcapitalist.com/feed/",
        "category": "market_news_alternative",
    },
    {
        "name": "Prof G Markets",
        "rss_url": "https://rss.substack.com/feed/profgmarkets",
        "category": "market_news_alternative",
    },
    {
        "name": "The Macro Compass",
        "rss_url": "https://themacrocompass.substack.com/feed",
        "category": "market_news_alternative",
    },
    {
        "name": "Epsilon Theory",
        "rss_url": "https://www.epsilontheory.com/feed/",
        "category": "market_news_alternative",
    },
    {
        "name": "MarketWatch",
        "rss_url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
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
        "name": "KrASIA",
        "rss_url": "https://kr-asia.com/feed",
        "category": "emerging_markets_asia",
    },
]

# YouTube RSS — video title + description scraped from RSS entry (no transcript).
# Processed via blog pipeline with rss_description fallback in blog_scraper.
YOUTUBE_RSS_SOURCES = [
    {
        "name": "Patrick Boyle",
        "rss_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCASM3r88ZDqAEXi6PH-GZGA",
        "category": "market_news_alternative",
    },
    {
        "name": "George Gammon",
        "rss_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCivbtfXQOkLGOZKdKgfRiNw",
        "category": "market_news_alternative",
    },
    {
        "name": "Y Combinator",
        "rss_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCcefcZRL2oaA_uBNeo5UOWg",
        "category": "startups_ipo",
    },
]
