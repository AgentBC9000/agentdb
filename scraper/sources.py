"""
AgentDB Knowledge Scraper — Source Definitions
All blogs, podcasts to scrape on each run.
YouTube sources removed — Railway server IPs are blocked from accessing
YouTube transcripts. Replaced with RSS feeds for the same editorial sources.
"""

# YouTube transcript scraping is blocked from cloud server IPs.
# Keeping the list empty — YouTube channels are replaced by RSS equivalents below.
YOUTUBE_SOURCES = []

# Former YouTube sources now ingested via RSS article feeds
_FORMER_YOUTUBE_AS_RSS = [
    {
        "name": "MarketWatch",
        "rss_url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "category": "market_news",
    },
    {
        "name": "Reuters Business",
        "rss_url": "https://feeds.reuters.com/reuters/businessNews",
        "category": "market_news",
    },
    {
        "name": "CNBC",
        "rss_url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        "category": "market_news",
    },
    {
        "name": "Prof G Markets",
        "rss_url": "https://rss.substack.com/feed/profgmarkets",
        "category": "market_news",
    },
    {
        "name": "Rebel Capitalist",
        "rss_url": "https://rebelcapitalist.com/feed/",
        "category": "market_news_alternative",
    },
    {
        "name": "Y Combinator Blog",
        "rss_url": "https://www.ycombinator.com/blog/rss.xml",
        "category": "startups_technology",
    },
]

PODCAST_SOURCES = [
    {
        "name": "Lex Fridman Podcast",
        "rss_url": "https://lexfridman.com/feed/podcast/",
        "category": "technology_ai",
        "hosts": ["Lex Fridman"],
        # Lex posts full transcripts on his site
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
        # Dwarkesh posts transcripts on Substack (dwarkesh.com)
        "transcript_selectors": [
            "div.body.markup",
            "div.available-content",
            "article",
        ],
    },
    {
        "name": "Acquired",
        "rss_url": "https://feeds.transistor.fm/acquired",
        "category": "startups_technology",
        "hosts": ["Ben Gilbert", "David Rosenthal"],
        # Acquired posts detailed show notes
        "transcript_selectors": [
            "div.show-notes",
            "div.episode-notes",
            "article .content",
            "div.post-content",
        ],
    },
    {
        "name": "Sean Carroll's Mindscape",
        "rss_url": "https://rss.art19.com/sean-carrolls-mindscape",
        "category": "philosophy_science",
        "hosts": ["Sean Carroll"],
        # Sean posts blog posts with show notes for each episode
        "transcript_selectors": [
            "div.entry-content",
            "article .post-content",
        ],
    },
    {
        "name": "Hard Fork",
        "rss_url": "https://feeds.simplecast.com/l2i9YnTd",
        "category": "technology_science",
        "hosts": ["Kevin Roose", "Casey Newton"],
        # NYT — show notes only, no transcript
        "transcript_selectors": [],
    },
    {
        "name": "All-In Podcast",
        "rss_url": "https://allinchamathjason.libsyn.com/rss",
        "category": "market_news",
        "hosts": ["Chamath Palihapitiya", "Jason Calacanis", "David Sacks", "David Friedberg"],
        "transcript_selectors": [],
    },
]

BLOG_SOURCES = [
    {
        "name": "Zero Hedge",
        "rss_url": "https://feeds.feedburner.com/zerohedge/feed",
        "category": "market_news_alternative",
    },
    {
        "name": "Marginal Revolution",
        "rss_url": "https://marginalrevolution.com/feed",
        "category": "economics_policy",
    },
    {
        "name": "Quanta Magazine",
        "rss_url": "https://www.quantamagazine.org/feed/",
        "category": "science_research",
    },
    {
        "name": "Ars Technica",
        "rss_url": "https://feeds.arstechnica.com/arstechnica/index",
        "category": "technology_science",
    },
    {
        "name": "Hacker News",
        "rss_url": "https://hnrss.org/frontpage",
        "category": "technology_startups",
    },
    # Former YouTube sources — replaced with RSS article feeds (YouTube transcripts
    # are blocked from Railway server IPs)
    {
        "name": "MarketWatch",
        "rss_url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "category": "market_news",
    },
    {
        "name": "Reuters Business",
        "rss_url": "https://feeds.reuters.com/reuters/businessNews",
        "category": "market_news",
    },
    {
        "name": "CNBC",
        "rss_url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        "category": "market_news",
    },
    {
        "name": "Prof G Markets",
        "rss_url": "https://rss.substack.com/feed/profgmarkets",
        "category": "market_news",
    },
    {
        "name": "Rebel Capitalist",
        "rss_url": "https://rebelcapitalist.com/feed/",
        "category": "market_news_alternative",
    },
    {
        "name": "Y Combinator Blog",
        "rss_url": "https://www.ycombinator.com/blog/rss.xml",
        "category": "startups_technology",
    },
]
