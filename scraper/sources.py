"""
AgentDB Knowledge Scraper — Source Definitions
All YouTube channels and blogs to scrape on each run.
"""

YOUTUBE_SOURCES = [
    {
        "name": "Bloomberg",
        "channel_id": "UCIALMKvObZNtJ6AmdCLP7Lg",
        "category": "market_news",
    },
    {
        "name": "CNBC",
        "channel_id": "UCrp_UI8XtuYfpiqluWLD7Lw",
        "category": "market_news",
    },
    {
        "name": "Reuters",
        "channel_id": "UChqUTb7kYRX8-EiaN3XFrSQ",
        "category": "market_news",
    },
    {
        "name": "Lex Fridman",
        "channel_id": "UCSHZKyawb77ixDdsGog4iWA",
        "category": "technology_ai",
    },
    {
        "name": "Closer To Truth",
        "channel_id": "UCl9StMQ79LtEvlrskzjoYbQ",
        "category": "philosophy_science",
    },
    {
        "name": "Y Combinator",
        "channel_id": "UCcefcZRL2oaA_uBNeo5UOWg",
        "category": "startups_technology",
    },
    {
        "name": "Rebel Capitalist",
        "channel_id": "UCNjyEXSvYUUCzagFAKmaJ1Q",
        "category": "market_news_alternative",
    },
    {
        "name": "Bernardo Kastrup",
        "channel_id": "UCeDZCa3VrRQvzBlVR-oVVmA",
        "category": "philosophy_science",
    },
]

BLOG_SOURCES = [
    {
        "name": "Zero Hedge",
        "rss_url": "https://feeds.feedburner.com/zerohedge/feed",
        "category": "market_news_alternative",
    },
    {
        "name": "Astral Codex Ten",
        "rss_url": "https://astralcodexten.substack.com/feed",
        "category": "rationalism_science",
    },
    {
        "name": "Quanta Magazine",
        "rss_url": "https://www.quantamagazine.org/feed/",
        "category": "science_research",
    },
    {
        "name": "McKinsey Insights",
        "rss_url": "https://www.mckinsey.com/feeds/rss/latest-thinking",
        "category": "business_strategy",
    },
    {
        "name": "Hacker News",
        "rss_url": "https://hnrss.org/frontpage",
        "category": "technology_startups",
    },
]
