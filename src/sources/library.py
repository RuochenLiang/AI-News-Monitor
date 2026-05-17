from __future__ import annotations

from dataclasses import replace
from time import perf_counter
from typing import Any

import httpx

from src.diagnostics import (
    DiagnosticResult,
    classify_feed_http_error,
    diagnostic_error,
    diagnostic_ok,
    invalid_url_result,
    is_valid_http_url,
)
from src.models import CustomNewsSourceConfig, SourceLibraryItem, SourceSettings
from src.sources.rss_helpers import parse_feed
from src.utils.http_utils import request_with_retries
from src.utils.text_utils import clean_text

SOURCE_LIBRARY_CATEGORIES = [
    "Global News",
    "Finance",
    "Official/Government",
    "China",
    "Taiwan",
    "US",
    "Semiconductor/AI",
    "Company IR",
    "Custom",
]

SOURCE_PACKAGE_PRESETS = {
    "global-news-starter": {
        "name": "Global News Starter",
        "description": "Broad public English-language news coverage for general monitoring.",
        "categories": ["Global News"],
        "expected_coverage": "major international headlines and public RSS coverage",
        "recommended_use_case": "General topic discovery and cross-checking.",
        "tier_weights": {"1": 1.0, "2": 0.9, "3": 0.7, "4": 0.45},
        "suggested_refresh_interval_seconds": 300,
        "suggested_relevance_threshold": 80,
        "topic_examples": ["global technology policy", "trade policy"],
    },
    "finance-starter": {
        "name": "Finance Starter",
        "description": "Public finance and market-news feeds for business impact monitoring.",
        "categories": ["Finance"],
        "expected_coverage": "financial media and public market-news feeds",
        "recommended_use_case": "Market-sensitive news monitoring without trading automation.",
        "tier_weights": {"1": 1.0, "2": 0.85, "3": 0.65, "4": 0.4},
        "suggested_refresh_interval_seconds": 240,
        "suggested_relevance_threshold": 82,
        "topic_examples": ["semiconductor earnings", "export controls"],
    },
    "official-gov-starter": {
        "name": "Official/Government Starter",
        "description": "Official public agency and government communications.",
        "categories": ["Official/Government", "US", "Taiwan"],
        "expected_coverage": "primary policy announcements and agency releases",
        "recommended_use_case": "Confirming policy-sensitive events from primary sources.",
        "tier_weights": {"1": 1.0, "2": 0.8, "3": 0.65, "4": 0.35},
        "suggested_refresh_interval_seconds": 600,
        "suggested_relevance_threshold": 84,
        "topic_examples": ["official export control actions", "government semiconductor policy"],
    },
    "china-taiwan-starter": {
        "name": "China/Taiwan Starter",
        "description": "Public sources relevant to China, Taiwan, and cross-strait monitoring.",
        "categories": ["China", "Taiwan"],
        "expected_coverage": "regional media, public official channels, and context sources",
        "recommended_use_case": "Geopolitics and supply-chain event monitoring.",
        "tier_weights": {"1": 1.0, "2": 0.8, "3": 0.7, "4": 0.4},
        "suggested_refresh_interval_seconds": 300,
        "suggested_relevance_threshold": 82,
        "topic_examples": ["Taiwan semiconductor cooperation", "cross-strait trade"],
    },
    "us-policy-starter": {
        "name": "US Policy Starter",
        "description": "Public U.S. policy and agency announcement monitoring.",
        "categories": ["US", "Official/Government"],
        "expected_coverage": "U.S. policy releases, trade actions, and public agency updates",
        "recommended_use_case": "Policy and regulatory monitoring.",
        "tier_weights": {"1": 1.0, "2": 0.82, "3": 0.62, "4": 0.35},
        "suggested_refresh_interval_seconds": 600,
        "suggested_relevance_threshold": 84,
        "topic_examples": ["U.S. export controls", "trade office announcements"],
    },
    "semiconductor-ai-starter": {
        "name": "Semiconductor/AI Starter",
        "description": "Technology, semiconductor, and AI public feeds.",
        "categories": ["Semiconductor/AI"],
        "expected_coverage": "AI industry, semiconductor trade, and technical media",
        "recommended_use_case": "AI and chip supply-chain monitoring.",
        "tier_weights": {"1": 1.0, "2": 0.85, "3": 0.75, "4": 0.45},
        "suggested_refresh_interval_seconds": 240,
        "suggested_relevance_threshold": 80,
        "topic_examples": ["AI chips", "semiconductor supply chain"],
    },
    "company-ir-starter": {
        "name": "Company IR Starter",
        "description": "Company-owned public newsrooms and investor-style updates.",
        "categories": ["Company IR"],
        "expected_coverage": "company announcements and primary corporate context",
        "recommended_use_case": "Primary-source company signal monitoring.",
        "tier_weights": {"1": 1.0, "2": 0.75, "3": 0.6, "4": 0.35},
        "suggested_refresh_interval_seconds": 600,
        "suggested_relevance_threshold": 82,
        "topic_examples": ["NVIDIA supply announcements", "TSMC capacity news"],
    },
    "taiwan-semiconductor-official": {
        "name": "Taiwan + Semiconductor + Official Sources",
        "description": "Focused preset for Taiwan, semiconductor, and official-source confirmation.",
        "categories": ["Taiwan", "Semiconductor/AI", "Official/Government", "Company IR"],
        "expected_coverage": "policy, regional, and company-source confirmation",
        "recommended_use_case": "Taiwan semiconductor policy and supply-chain topics.",
        "tier_weights": {"1": 1.0, "2": 0.86, "3": 0.72, "4": 0.38},
        "suggested_refresh_interval_seconds": 240,
        "suggested_relevance_threshold": 84,
        "topic_examples": ["Taiwan semiconductor cooperation", "TSMC policy impact"],
    },
    "geopolitics-starter": {
        "name": "Geopolitics Starter",
        "description": "Public geopolitical monitoring from official, regional, and major-media sources.",
        "categories": ["Global News", "Official/Government", "US", "China", "Taiwan"],
        "expected_coverage": "policy, regional, and major-media public coverage",
        "recommended_use_case": "Trade, sanctions, defense, and regional policy monitoring.",
        "tier_weights": {"1": 1.0, "2": 0.85, "3": 0.7, "4": 0.35},
        "suggested_refresh_interval_seconds": 300,
        "suggested_relevance_threshold": 84,
        "topic_examples": ["trade sanctions", "regional security policy"],
    },
    "ai-industry-starter": {
        "name": "AI Industry Starter",
        "description": "AI company, research, and industry media monitoring.",
        "categories": ["Semiconductor/AI", "Company IR", "Global News"],
        "expected_coverage": "AI company announcements, research feeds, and industry coverage",
        "recommended_use_case": "AI product, model, and infrastructure monitoring.",
        "tier_weights": {"1": 1.0, "2": 0.84, "3": 0.74, "4": 0.42},
        "suggested_refresh_interval_seconds": 240,
        "suggested_relevance_threshold": 80,
        "topic_examples": ["AI infrastructure", "model releases"],
    },
}

SOURCE_PACKAGES = {key: str(value["name"]) for key, value in SOURCE_PACKAGE_PRESETS.items()}

WEBSITE_ONLY_SOURCE_IDS = {
    "amd-news",
    "anthropic-news",
    "ap-top-news",
    "asml-news",
    "bis-news",
    "cnbc-finance",
    "commerce-news",
    "intel-news",
    "meta-ai-blog",
    "microsoft-blog",
    "nasdaq-news",
    "reuters-business",
    "semi-org",
    "semiconductor-today",
    "state-dept-press",
    "taiwan-cna",
    "taiwan-mofa",
    "taiwan-presidential-office",
    "tesla-press",
    "tsmc-news",
    "us-treasury-press",
    "ustr-press",
    "white-house",
    "xinhua-business",
    "xinhua-world",
    "yahoo-finance",
}


DEFAULT_SOURCE_LIBRARY = [
    SourceLibraryItem(
        "arxiv-cs-ai",
        "arXiv cs.AI",
        "https://export.arxiv.org/rss/cs.AI",
        enabled=True,
        category="Semiconductor/AI",
        language="en",
        reliability_score=0.82,
        ownership="Cornell University",
        bias_hint="Preprint research feed; not peer-reviewed.",
        website_url="https://arxiv.org/list/cs.AI/recent",
    ),
    SourceLibraryItem(
        "openai-news",
        "OpenAI News",
        "https://openai.com/news/rss.xml",
        enabled=True,
        category="Company IR",
        language="en",
        reliability_score=0.92,
        ownership="OpenAI",
        bias_hint="Company-owned primary source.",
        website_url="https://openai.com/news/",
    ),
    SourceLibraryItem(
        "google-ai-blog",
        "Google AI Blog",
        "https://blog.google/technology/ai/rss/",
        enabled=True,
        category="Semiconductor/AI",
        language="en",
        reliability_score=0.88,
        ownership="Google",
        bias_hint="Company-owned primary source.",
        website_url="https://blog.google/technology/ai/",
    ),
    SourceLibraryItem(
        "bbc-world",
        "BBC World",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        category="Global News",
        language="en",
        reliability_score=0.78,
        ownership="BBC",
        website_url="https://www.bbc.com/news/world",
    ),
    SourceLibraryItem(
        "npr-news",
        "NPR News",
        "https://feeds.npr.org/1001/rss.xml",
        category="Global News",
        language="en",
        reliability_score=0.78,
        ownership="NPR",
        website_url="https://www.npr.org/sections/news/",
    ),
    SourceLibraryItem(
        "the-verge",
        "The Verge",
        "https://www.theverge.com/rss/index.xml",
        category="Global News",
        language="en",
        reliability_score=0.68,
        ownership="Vox Media",
        bias_hint="Technology-focused editorial source.",
        website_url="https://www.theverge.com/",
    ),
    SourceLibraryItem(
        "ars-technica",
        "Ars Technica",
        "https://feeds.arstechnica.com/arstechnica/index",
        category="Global News",
        language="en",
        reliability_score=0.72,
        ownership="Conde Nast",
        website_url="https://arstechnica.com/",
    ),
    SourceLibraryItem(
        "techcrunch-ai",
        "TechCrunch AI",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        category="Semiconductor/AI",
        language="en",
        reliability_score=0.66,
        ownership="Yahoo",
        bias_hint="Startup and venture coverage.",
        website_url="https://techcrunch.com/category/artificial-intelligence/",
    ),
    SourceLibraryItem(
        "mit-tech-review-ai",
        "MIT Technology Review AI",
        "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
        category="Semiconductor/AI",
        language="en",
        reliability_score=0.76,
        ownership="MIT Technology Review",
        website_url="https://www.technologyreview.com/topic/artificial-intelligence/",
    ),
    SourceLibraryItem(
        "venturebeat-ai",
        "VentureBeat AI",
        "https://venturebeat.com/category/ai/feed/",
        category="Semiconductor/AI",
        language="en",
        reliability_score=0.62,
        ownership="VentureBeat",
        bias_hint="Industry and startup coverage.",
        website_url="https://venturebeat.com/category/ai/",
    ),
    SourceLibraryItem(
        "nvidia-blog",
        "NVIDIA Blog",
        "https://blogs.nvidia.com/feed/",
        category="Company IR",
        language="en",
        reliability_score=0.86,
        ownership="NVIDIA",
        bias_hint="Company-owned primary source.",
        website_url="https://blogs.nvidia.com/",
    ),
    SourceLibraryItem(
        "microsoft-blog",
        "Microsoft Blog",
        "https://blogs.microsoft.com/feed/",
        category="Company IR",
        language="en",
        reliability_score=0.84,
        ownership="Microsoft",
        bias_hint="Company-owned primary source.",
        website_url="https://blogs.microsoft.com/",
    ),
    SourceLibraryItem(
        "meta-ai-blog",
        "Meta AI Blog",
        "https://ai.meta.com/blog/rss/",
        category="Company IR",
        language="en",
        reliability_score=0.84,
        ownership="Meta",
        bias_hint="Company-owned primary source.",
        website_url="https://ai.meta.com/blog/",
    ),
    SourceLibraryItem(
        "anthropic-news",
        "Anthropic News",
        "https://www.anthropic.com/news/rss.xml",
        category="Company IR",
        language="en",
        reliability_score=0.84,
        ownership="Anthropic",
        bias_hint="Company-owned primary source.",
        website_url="https://www.anthropic.com/news",
    ),
    SourceLibraryItem(
        "sec-press",
        "SEC Press Releases",
        "https://www.sec.gov/news/pressreleases.rss",
        category="Official/Government",
        language="en",
        reliability_score=0.94,
        ownership="U.S. Securities and Exchange Commission",
        bias_hint="Official government source.",
        website_url="https://www.sec.gov/news/pressreleases",
    ),
    SourceLibraryItem(
        "federal-reserve",
        "Federal Reserve Press Releases",
        "https://www.federalreserve.gov/feeds/press_all.xml",
        category="Official/Government",
        language="en",
        reliability_score=0.94,
        ownership="Federal Reserve",
        bias_hint="Official government source.",
        website_url="https://www.federalreserve.gov/newsevents/pressreleases.htm",
    ),
    SourceLibraryItem(
        "white-house",
        "White House Briefing Room",
        "https://www.whitehouse.gov/briefing-room/feed/",
        category="Official/Government",
        language="en",
        reliability_score=0.9,
        ownership="The White House",
        bias_hint="Official government communications.",
        website_url="https://www.whitehouse.gov/briefing-room/",
    ),
    SourceLibraryItem(
        "cnbc-finance",
        "CNBC Finance",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        category="Finance",
        language="en",
        reliability_score=0.68,
        ownership="NBCUniversal",
        website_url="https://www.cnbc.com/finance/",
    ),
    SourceLibraryItem(
        "marketwatch-top",
        "MarketWatch Top Stories",
        "https://feeds.marketwatch.com/marketwatch/topstories/",
        category="Finance",
        language="en",
        reliability_score=0.66,
        ownership="Dow Jones",
        website_url="https://www.marketwatch.com/",
    ),
    SourceLibraryItem(
        "yahoo-finance",
        "Yahoo Finance",
        "https://finance.yahoo.com/news/rssindex",
        category="Finance",
        language="en",
        reliability_score=0.62,
        ownership="Yahoo",
        website_url="https://finance.yahoo.com/news/",
    ),
    SourceLibraryItem(
        "nasdaq-news",
        "Nasdaq News",
        "https://www.nasdaq.com/feed/rssoutbound",
        category="Finance",
        language="en",
        reliability_score=0.66,
        ownership="Nasdaq",
        website_url="https://www.nasdaq.com/news-and-insights",
    ),
    SourceLibraryItem(
        "xinhua-world",
        "Xinhua World",
        "https://english.news.cn/rss/world.xml",
        category="China",
        language="en",
        reliability_score=0.58,
        ownership="Xinhua",
        bias_hint="Chinese state media; use with context.",
        website_url="https://english.news.cn/world/",
    ),
    SourceLibraryItem(
        "xinhua-business",
        "Xinhua Business",
        "https://english.news.cn/rss/business.xml",
        category="China",
        language="en",
        reliability_score=0.58,
        ownership="Xinhua",
        bias_hint="Chinese state media; use with context.",
        website_url="https://english.news.cn/business/",
    ),
    SourceLibraryItem(
        "taiwan-cna",
        "Taiwan CNA English",
        "https://focustaiwan.tw/rss",
        category="Taiwan",
        language="en",
        reliability_score=0.72,
        ownership="Central News Agency",
        website_url="https://focustaiwan.tw/",
    ),
    SourceLibraryItem(
        "taiwan-mofa",
        "Taiwan MOFA News",
        "https://en.mofa.gov.tw/Rss.aspx?n=1328",
        category="Taiwan",
        language="en",
        reliability_score=0.9,
        ownership="Taiwan Ministry of Foreign Affairs",
        bias_hint="Official government source.",
        website_url="https://en.mofa.gov.tw/",
    ),
    SourceLibraryItem(
        "ustr-press",
        "USTR Press Releases",
        "https://ustr.gov/about-us/policy-offices/press-office/press-releases/feed",
        category="US",
        language="en",
        reliability_score=0.9,
        ownership="Office of the U.S. Trade Representative",
        bias_hint="Official government source.",
        website_url="https://ustr.gov/about-us/policy-offices/press-office/press-releases",
    ),
    SourceLibraryItem(
        "commerce-news",
        "U.S. Commerce News",
        "https://www.commerce.gov/news/rss.xml",
        category="US",
        language="en",
        reliability_score=0.9,
        ownership="U.S. Department of Commerce",
        bias_hint="Official government source.",
        website_url="https://www.commerce.gov/news",
    ),
    SourceLibraryItem(
        "nist-news",
        "NIST News",
        "https://www.nist.gov/news-events/news/rss.xml",
        category="US",
        language="en",
        reliability_score=0.9,
        ownership="NIST",
        bias_hint="Official government source.",
        website_url="https://www.nist.gov/news-events/news",
    ),
    SourceLibraryItem(
        "semiengineering",
        "Semiconductor Engineering",
        "https://semiengineering.com/feed/",
        category="Semiconductor/AI",
        language="en",
        reliability_score=0.7,
        ownership="Semiconductor Engineering",
        website_url="https://semiengineering.com/",
    ),
    SourceLibraryItem(
        "semi-org",
        "SEMI News",
        "https://www.semi.org/en/rss.xml",
        category="Semiconductor/AI",
        language="en",
        reliability_score=0.72,
        ownership="SEMI",
        website_url="https://www.semi.org/en/news-resources",
    ),
    SourceLibraryItem(
        "tsmc-news",
        "TSMC Newsroom",
        "https://pr.tsmc.com/english/rss",
        category="Company IR",
        language="en",
        reliability_score=0.88,
        ownership="TSMC",
        bias_hint="Company-owned primary source.",
        website_url="https://pr.tsmc.com/english/news",
    ),
    SourceLibraryItem(
        "intel-news",
        "Intel Newsroom",
        "https://www.intel.com/content/www/us/en/newsroom/rss.xml",
        category="Company IR",
        language="en",
        reliability_score=0.86,
        ownership="Intel",
        bias_hint="Company-owned primary source.",
        website_url="https://www.intel.com/content/www/us/en/newsroom/home.html",
    ),
    SourceLibraryItem(
        "amd-news",
        "AMD Newsroom",
        "https://www.amd.com/en/newsroom/rss.xml",
        category="Company IR",
        language="en",
        reliability_score=0.86,
        ownership="AMD",
        bias_hint="Company-owned primary source.",
        website_url="https://www.amd.com/en/newsroom.html",
    ),
    SourceLibraryItem(
        "reuters-business",
        "Reuters Business",
        "https://feeds.reuters.com/reuters/businessNews",
        category="Global News",
        language="en",
        reliability_score=0.8,
        ownership="Thomson Reuters",
        website_url="https://www.reuters.com/business/",
    ),
    SourceLibraryItem(
        "ap-top-news",
        "Associated Press Top News",
        "https://feeds.apnews.com/rss/apf-topnews",
        category="Global News",
        language="en",
        reliability_score=0.8,
        ownership="Associated Press",
        website_url="https://apnews.com/",
    ),
    SourceLibraryItem(
        "dw-top-stories",
        "DW Top Stories",
        "https://rss.dw.com/xml/rss-en-top",
        category="Global News",
        language="en",
        reliability_score=0.74,
        ownership="Deutsche Welle",
        website_url="https://www.dw.com/",
    ),
    SourceLibraryItem(
        "guardian-world",
        "The Guardian World",
        "https://www.theguardian.com/world/rss",
        category="Global News",
        language="en",
        reliability_score=0.72,
        ownership="Guardian Media Group",
        website_url="https://www.theguardian.com/world",
    ),
    SourceLibraryItem(
        "ft-markets",
        "Financial Times Markets",
        "https://www.ft.com/markets?format=rss",
        category="Finance",
        language="en",
        reliability_score=0.78,
        ownership="Financial Times",
        website_url="https://www.ft.com/markets",
    ),
    SourceLibraryItem(
        "investing-news",
        "Investing.com News",
        "https://www.investing.com/rss/news.rss",
        category="Finance",
        language="en",
        reliability_score=0.62,
        ownership="Investing.com",
        website_url="https://www.investing.com/news/",
    ),
    SourceLibraryItem(
        "us-treasury-press",
        "U.S. Treasury Press Releases",
        "https://home.treasury.gov/news/press-releases/rss",
        category="Official/Government",
        language="en",
        reliability_score=0.94,
        ownership="U.S. Department of the Treasury",
        bias_hint="Official government source.",
        website_url="https://home.treasury.gov/news/press-releases",
    ),
    SourceLibraryItem(
        "state-dept-press",
        "U.S. State Department Press Releases",
        "https://www.state.gov/rss-feed/press-releases/feed/",
        category="US",
        language="en",
        reliability_score=0.9,
        ownership="U.S. Department of State",
        bias_hint="Official government source.",
        website_url="https://www.state.gov/press-releases/",
    ),
    SourceLibraryItem(
        "bis-news",
        "BIS Press Releases",
        "https://www.bis.doc.gov/index.php/newsroom/press-releases?format=feed&type=rss",
        category="US",
        language="en",
        reliability_score=0.9,
        ownership="U.S. Bureau of Industry and Security",
        bias_hint="Official government source.",
        website_url="https://www.bis.doc.gov/index.php/newsroom/press-releases",
    ),
    SourceLibraryItem(
        "taiwan-presidential-office",
        "Taiwan Presidential Office News",
        "https://english.president.gov.tw/RSS/News",
        category="Taiwan",
        language="en",
        reliability_score=0.9,
        ownership="Taiwan Presidential Office",
        bias_hint="Official government source.",
        website_url="https://english.president.gov.tw/News",
    ),
    SourceLibraryItem(
        "scmp-tech",
        "SCMP Tech",
        "https://www.scmp.com/rss/36/feed",
        category="China",
        language="en",
        reliability_score=0.66,
        ownership="South China Morning Post",
        website_url="https://www.scmp.com/tech",
    ),
    SourceLibraryItem(
        "nikkei-asia",
        "Nikkei Asia",
        "https://asia.nikkei.com/rss/feed/nar",
        category="Global News",
        language="en",
        reliability_score=0.74,
        ownership="Nikkei",
        website_url="https://asia.nikkei.com/",
    ),
    SourceLibraryItem(
        "ieee-spectrum-ai",
        "IEEE Spectrum AI",
        "https://spectrum.ieee.org/feeds/topic/artificial-intelligence.rss",
        category="Semiconductor/AI",
        language="en",
        reliability_score=0.76,
        ownership="IEEE",
        website_url="https://spectrum.ieee.org/artificial-intelligence",
    ),
    SourceLibraryItem(
        "semiconductor-today",
        "Semiconductor Today",
        "https://www.semiconductor-today.com/news_items/rss.xml",
        category="Semiconductor/AI",
        language="en",
        reliability_score=0.68,
        ownership="Semiconductor Today",
        website_url="https://www.semiconductor-today.com/",
    ),
    SourceLibraryItem(
        "asml-news",
        "ASML News",
        "https://www.asml.com/en/news/rss",
        category="Company IR",
        language="en",
        reliability_score=0.86,
        ownership="ASML",
        bias_hint="Company-owned primary source.",
        website_url="https://www.asml.com/en/news",
    ),
    SourceLibraryItem(
        "apple-newsroom",
        "Apple Newsroom",
        "https://www.apple.com/newsroom/rss-feed.rss",
        category="Company IR",
        language="en",
        reliability_score=0.86,
        ownership="Apple",
        bias_hint="Company-owned primary source.",
        website_url="https://www.apple.com/newsroom/",
    ),
    SourceLibraryItem(
        "amazon-news",
        "Amazon News",
        "https://www.aboutamazon.com/news/rss",
        category="Company IR",
        language="en",
        reliability_score=0.84,
        ownership="Amazon",
        bias_hint="Company-owned primary source.",
        website_url="https://www.aboutamazon.com/news",
    ),
    SourceLibraryItem(
        "tesla-press",
        "Tesla Press Releases",
        "https://www.tesla.com/blog/rss",
        category="Company IR",
        language="en",
        reliability_score=0.78,
        ownership="Tesla",
        bias_hint="Company-owned primary source.",
        website_url="https://www.tesla.com/blog",
    ),
]


def default_source_library() -> list[SourceLibraryItem]:
    items: list[SourceLibraryItem] = []
    for item in DEFAULT_SOURCE_LIBRARY:
        packages = item.packages or _packages_for_category(item.category)
        enriched = _with_inferred_metadata(item)
        if item.id in WEBSITE_ONLY_SOURCE_IDS:
            items.append(
                replace(
                    enriched,
                    enabled=False,
                    kind="website",
                    source_type="website",
                    url=item.website_url or item.url,
                    packages=packages,
                )
            )
        else:
            items.append(replace(enriched, packages=packages))
    return items


def merge_source_library(configured: list[SourceLibraryItem]) -> list[SourceLibraryItem]:
    configured_by_id = {item.id: item for item in configured}
    merged: list[SourceLibraryItem] = []
    for default_item in default_source_library():
        configured_item = configured_by_id.get(default_item.id)
        if configured_item:
            if not configured_item.packages:
                configured_item = replace(configured_item, packages=default_item.packages)
            if configured_item.source_tier == 4 and configured_item.source_role == "custom":
                configured_item = replace(
                    configured_item,
                    source_tier=default_item.source_tier,
                    source_role=default_item.source_role,
                    state_affiliated=default_item.state_affiliated,
                    propaganda_risk=default_item.propaganda_risk,
                    editorial_context=configured_item.editorial_context or default_item.editorial_context,
                )
            merged.append(configured_item)
        else:
            merged.append(default_item)
    custom_items = [item for item in configured if item.id not in {source.id for source in DEFAULT_SOURCE_LIBRARY}]
    return merged + custom_items


def library_item_to_custom_source(item: SourceLibraryItem) -> CustomNewsSourceConfig:
    return CustomNewsSourceConfig(
        name=item.name,
        url=item.url,
        enabled=item.enabled,
        kind=item.kind,
        category=item.category,
        reliability_score=item.reliability_score,
        source_tier=item.source_tier,
        source_role=item.source_role,
        state_affiliated=item.state_affiliated,
        propaganda_risk=item.propaganda_risk,
        editorial_context=item.editorial_context,
        ownership=item.ownership,
        bias_hint=item.bias_hint,
        default_language=item.language,
        website_url=item.website_url,
        help_url=item.help_url,
    )


def enabled_library_sources(settings: SourceSettings) -> list[CustomNewsSourceConfig]:
    enabled_packages = set(settings.enabled_packages)
    return [
        library_item_to_custom_source(item)
        for item in settings.library
        if item.kind == "rss" and (item.enabled or enabled_packages.intersection(item.packages))
    ]


def _packages_for_category(category: str) -> list[str]:
    if category == "Global News":
        return ["global-news-starter", "geopolitics-starter"]
    if category == "Finance":
        return ["finance-starter"]
    if category == "Official/Government":
        return ["official-gov-starter", "geopolitics-starter", "taiwan-semiconductor-official"]
    if category in {"China", "Taiwan"}:
        return ["china-taiwan-starter", "geopolitics-starter", "taiwan-semiconductor-official"]
    if category == "US":
        return ["us-policy-starter", "official-gov-starter", "geopolitics-starter"]
    if category == "Semiconductor/AI":
        return ["semiconductor-ai-starter", "ai-industry-starter", "taiwan-semiconductor-official"]
    if category == "Company IR":
        return ["company-ir-starter", "ai-industry-starter", "taiwan-semiconductor-official"]
    return []


def source_package_snapshots() -> list[dict[str, Any]]:
    return [
        {
            "id": package_id,
            "name": preset["name"],
            "description": preset["description"],
            "categories": preset["categories"],
            "expected_coverage": preset["expected_coverage"],
            "recommended_use_case": preset["recommended_use_case"],
            "tier_weights": preset["tier_weights"],
            "suggested_refresh_interval_seconds": preset["suggested_refresh_interval_seconds"],
            "suggested_relevance_threshold": preset["suggested_relevance_threshold"],
            "topic_examples": preset["topic_examples"],
        }
        for package_id, preset in SOURCE_PACKAGE_PRESETS.items()
    ]


def apply_source_package_presets(settings: SourceSettings, preset_ids: list[str]) -> SourceSettings:
    selected = [preset_id for preset_id in preset_ids if preset_id in SOURCE_PACKAGE_PRESETS]
    merged = sorted(set(settings.enabled_packages).union(selected))
    return replace(settings, enabled_packages=merged)


def _with_inferred_metadata(item: SourceLibraryItem) -> SourceLibraryItem:
    text = " ".join([item.name, item.category, item.ownership or "", item.bias_hint or "", item.source_type]).casefold()
    if "official" in text or "government" in text or "ministry" in text or "department" in text:
        return replace(
            item,
            source_tier=1,
            source_role="official",
            state_affiliated=True,
            propaganda_risk="low",
            editorial_context=item.editorial_context or "Official or primary institutional source.",
        )
    if item.category == "Company IR" or "company-owned" in text or "newsroom" in text:
        return replace(
            item,
            source_tier=1,
            source_role="company_ir",
            propaganda_risk="low",
            editorial_context=item.editorial_context or "Company-owned primary source.",
        )
    if "xinhua" in text or "state media" in text:
        return replace(
            item,
            source_tier=2,
            source_role="major_media",
            state_affiliated=True,
            propaganda_risk="medium",
            editorial_context=item.editorial_context or "State-affiliated media; compare with independent sources.",
        )
    if "aggregator" in text or "google news" in text or "yahoo finance" in text:
        return replace(
            item,
            source_tier=4,
            source_role="aggregator",
            propaganda_risk="unknown",
            editorial_context=item.editorial_context
            or "Aggregator or index source; verify original publisher context.",
        )
    if item.category in {"Global News", "Finance"}:
        return replace(
            item,
            source_tier=2,
            source_role="major_media",
            propaganda_risk="low",
            editorial_context=item.editorial_context or "Established public news or financial media source.",
        )
    return replace(
        item,
        source_tier=3,
        source_role="niche_media",
        editorial_context=item.editorial_context or "Specialist or domain-specific source.",
    )


def detect_feed_metadata(url: str, content: bytes | str) -> dict[str, Any]:
    try:
        import feedparser
    except ImportError as exc:
        raise RuntimeError("feedparser is required for RSS source detection") from exc

    parsed = feedparser.parse(content)
    if getattr(parsed, "bozo", False) and not parsed.entries:
        raise ValueError(getattr(parsed, "bozo_exception", "Feed could not be parsed"))
    feed = parsed.feed
    title = clean_text(getattr(feed, "title", "") or url, max_length=120)
    language = getattr(feed, "language", None) or None
    sample_articles = parse_feed(content, title, language)[:3]
    return {
        "name": title,
        "language": language,
        "entries": len(parsed.entries),
        "sample_titles": [article.title for article in sample_articles],
    }


def test_feed_url(url: str, timeout_seconds: int = 20, client: httpx.Client | None = None) -> dict[str, Any]:
    diagnostic = diagnose_feed_url(url, timeout_seconds, client)
    if not diagnostic.ok:
        return {
            "ok": False,
            "category": diagnostic.category,
            "message": diagnostic.message,
            "suggested_fix": diagnostic.suggested_fix,
            "technical_detail": diagnostic.technical_detail,
        }
    return {"ok": True, **diagnostic.details}


def diagnose_feed_url(url: str, timeout_seconds: int = 20, client: httpx.Client | None = None) -> DiagnosticResult:
    url = str(url or "").strip()
    required_fields = ["url"]
    if not url:
        return diagnostic_error(
            "source",
            "missing_required_field",
            "Source URL is required.",
            missing_fields=["url"],
            required_fields=required_fields,
            configured=False,
        )
    if not is_valid_http_url(url):
        return invalid_url_result("source", url, required_fields=required_fields)
    started = perf_counter()
    close_client = client is None
    active_client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)
    try:
        response = request_with_retries(active_client, "GET", url)
        metadata = detect_feed_metadata(url, response.content)
        if metadata["entries"] <= 0:
            return diagnostic_error(
                "source",
                "feed_empty",
                "Feed was reachable but returned no entries.",
                required_fields=required_fields,
                latency_ms=_latency_ms(started),
                details=metadata,
            )
        return diagnostic_ok(
            "source",
            "Source test completed.",
            required_fields=required_fields,
            latency_ms=_latency_ms(started),
            details=metadata,
        )
    except httpx.HTTPError as exc:
        category = classify_feed_http_error(exc)
        return diagnostic_error(
            "source",
            category,
            _feed_error_message(category),
            technical_detail=exc,
            required_fields=required_fields,
            latency_ms=_latency_ms(started),
        )
    except ValueError as exc:
        return diagnostic_error(
            "source",
            "feed_parse_failed",
            "Feed response could not be parsed as RSS or Atom.",
            technical_detail=exc,
            required_fields=required_fields,
            latency_ms=_latency_ms(started),
        )
    finally:
        if close_client:
            active_client.close()


def _latency_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)


def _feed_error_message(category: str) -> str:
    return {
        "feed_unreachable": "Feed URL is unreachable.",
        "api_timeout": "Feed request timed out.",
        "tls_or_certificate_error": "Feed request failed because of a TLS or certificate issue.",
        "network_unreachable": "Network is unreachable for this feed.",
        "proxy_or_firewall_issue": "Proxy or firewall blocked this feed.",
    }.get(category, "Source test failed.")
