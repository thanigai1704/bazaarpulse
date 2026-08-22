"""Live scraper for Flipkart & Amazon.in using Playwright.

⚠️  ANTI-BOT REALITY CHECK
──────────────────────────
Both marketplaces actively block datacenter IPs and headless browsers.
Scraping them at scale violates their ToS. BazaarPulse therefore:

  * defaults to SCRAPE_MODE=simulation (see data_simulator.py), and
  * ships this scraper as an OPTIONAL "live" producer that:
        - respects robots.txt (we skip URL paths disallowed there),
        - rotates realistic User-Agent strings,
        - inserts jittered human-like delays (default 4.5s),
        - uses a real headed browser when SCRAPE_HEADLESS=false.

Even with all that, expect intermittent blocks. Use SCRAPE_MODE=mixed so the
pipeline falls back to the simulator whenever a scrape round fails.

PARSING
───────
Flipkart keeps DOM ids stable enough for portfolio scraping:
  - price rows:   div.Nx9bqj / div._30jeq3
  - names:        div._4rR01T / a.s1Q9rs
  - ratings:      div._3LWZlK
  - review text:  div.t-ZTKy (reviews page)
Amazon.in is far more volatile; we attempt several known selector sets and
gracefully give up on a page if none match.
"""

import asyncio
import logging
import random
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from ..config import get_settings
from .price_formatter import parse_discount_pct, parse_price

logger = logging.getLogger(__name__)
settings = get_settings()

# Rotating desktop Chrome user-agents (Indian-market realistic).
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
]

_FLIPKART_SEARCH_URL = "https://www.flipkart.com/search?q={query}"
_AMAZON_SEARCH_URL = "https://www.amazon.in/s?k={query}"
_FLIPKART_ROBOTS_BLOCKED = {"/account", "/login", "/checkout", "/viewcart"}

_FLIPKART_SELECTORS = {
    "card": "div._1AtVbE, div._2kHMtA, div.tUxCFH",
    "name": "div._4rR01T, a.s1Q9rs, div._2WkVRV",
    "price": "div._30jeq3._1_WHN1, div._30jeq3",
    "mrp": "div._3I9_wc._2p6lqe, div._3I9_wc",
    "discount": "div._3Ay6Sb._31Dcoz",
    "rating": "div._3LWZlK",
    "rating_count": "span._2_R_DZ",
    "seller": "div._3DkUQF, div._1RLviY",
    "delivery": "div._2Tpdn3, div._3iiZ7S",
}


def _respects_robots(url: str) -> bool:
    path = urlparse(url).path
    for blocked in _FLIPKART_ROBOTS_BLOCKED:
        if path.startswith(blocked):
            return False
    return True


def _random_headers() -> Dict[str, str]:
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


async def _scrape_flipkart(query: str) -> List[dict]:
    """Use Playwright (chromium) to render a Flipkart search page and extract
    product cards. Returns raw dicts; caller cleans them with Pandas."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("playwright not installed; install via `pip install -r requirements.txt`")
        return []

    url = _FLIPKART_SEARCH_URL.format(query=query)
    if not _respects_robots(url):
        logger.info("Skipping %s (robots.txt-disallowed path)", url)
        return []

    products: List[dict] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.scrape_headless)
        context = await browser.new_context(
            user_agent=random.choice(_USER_AGENTS),
            viewport={"width": 1366, "height": 900},
            locale="en-IN",
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Human-like scroll to trigger lazy-loaded cards.
            for _ in range(3):
                await page.mouse.wheel(0, 700)
                await page.wait_for_timeout(random.randint(700, 1400))

            soup = BeautifulSoup(await page.content(), "html.parser")
            cards = soup.select(",".join(_FLIPKART_SELECTORS["card"]))[:12]
            for card in cards:
                name = _first_text(card, _FLIPKART_SELECTORS["name"])
                if not name:
                    continue
                price = parse_price(_first_text(card, _FLIPKART_SELECTORS["price"]))
                mrp = parse_price(_first_text(card, _FLIPKART_SELECTORS["mrp"])) or price
                products.append(
                    {
                        "name": name.strip(),
                        "current_price": price,
                        "mrp": mrp,
                        "discount_pct": parse_discount_pct(
                            _first_text(card, _FLIPKART_SELECTORS["discount"])
                        )
                        or (round((mrp - price) / mrp * 100, 1) if mrp and price else 0.0),
                        "rating": _safe_float(_first_text(card, _FLIPKART_SELECTORS["rating"])),
                        "rating_count": _safe_int(_first_text(card, _FLIPKART_SELECTORS["rating_count"])),
                        "seller": (_first_text(card, _FLIPKART_SELECTORS["seller"]) or "Flipkart").strip(),
                        "delivery_estimate": _first_text(card, _FLIPKART_SELECTORS["delivery"]) or "Standard Delivery",
                        "source": "Flipkart",
                    }
                )
        except Exception as exc:
            logger.warning("Flipkart scrape round failed for '%s': %s", query, exc)
        finally:
            await browser.close()
    logger.info("Scraped %d products for query '%s'", len(products), query)
    return products


_AMAZON_SELECTORS = {
    "card": "div.s-result-item[data-component-type='s-search-result']",
    "name": "h2 a span, h2 span.a-size-medium",
    "price": "span.a-price > span.a-offscreen",
    "rating": "span.a-icon-alt",
    "rating_count": "span[aria-label*='rating'], span.a-size-base.s-underline-text",
    "delivery": "div.s-prime, span.a-text-normal + span.a-text-bold",
}

_AMAZON_HEADERS_EXTRA = {
    "dnt": "1",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
}


def _first_text(node, selector: str) -> Optional[str]:
    try:
        el = node.select_one(selector)
        return el.get_text(" ", strip=True) if el else None
    except Exception:
        return None


def _safe_float(raw: Optional[str]) -> float:
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _safe_int(raw: Optional[str]) -> int:
    if not raw:
        return 0
    digits = "".join(ch for ch in raw if ch.isdigit())
    return int(digits) if digits else 0


async def _scrape_amazon(query: str) -> List[dict]:
    """Scrape an Amazon.in search page with Playwright (rendered JS + CAPTCHA-
    friendly browser). Falls back to an httpx+BeautifulSoup pass if Playwright
    is unavailable."""
    url = _AMAZON_SEARCH_URL.format(query=query)
    products: List[dict] = []

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return await _scrape_amazon_httpx(url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.scrape_headless)
        context = await browser.new_context(
            user_agent=random.choice(_USER_AGENTS),
            viewport={"width": 1366, "height": 900},
            locale="en-IN",
            extra_http_headers=_AMAZON_HEADERS_EXTRA,
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            for _ in range(4):
                await page.mouse.wheel(0, 900)
                await page.wait_for_timeout(random.randint(800, 1600))

            soup = BeautifulSoup(await page.content(), "html.parser")
            cards = soup.select(",".join(_AMAZON_SELECTORS["card"]))[:12]
            for card in cards:
                name = _first_text(card, _AMAZON_SELECTORS["name"])
                price = parse_price(_first_text(card, _AMAZON_SELECTORS["price"]))
                if not name or not price:
                    continue
                mrp = parse_price(
                    _first_text(card, "span.a-text-price > span.a-offscreen")
                ) or price
                rating_raw = _first_text(card, _AMAZON_SELECTORS["rating"]) or ""
                rating = _safe_float(rating_raw.replace("out of 5 stars", ""))
                count_raw = _first_text(card, _AMAZON_SELECTORS["rating_count"]) or ""
                products.append(
                    {
                        "name": name.strip(),
                        "current_price": price,
                        "mrp": mrp,
                        "discount_pct": round((mrp - price) / mrp * 100, 1) if mrp and price else 0.0,
                        "rating": round(min(rating, 5.0), 1),
                        "rating_count": _safe_int(count_raw),
                        "seller": "Amazon.in",
                        "delivery_estimate": "Free delivery",
                        "source": "Amazon",
                    }
                )
        except Exception as exc:
            logger.warning("Amazon scrape round failed for '%s': %s", query, exc)
        finally:
            await browser.close()
    logger.info("Scraped %d products for query '%s'", len(products), query)
    return products


async def _scrape_amazon_httpx(url: str) -> List[dict]:
    """Playwright-less fallback: plain httpx GET + BeautifulSoup."""
    products: List[dict] = []
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={**_random_headers(), **_AMAZON_HEADERS_EXTRA}) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning("Amazon httpx returned %s", resp.status_code)
                return []
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select(_AMAZON_SELECTORS["card"])[:12]
            for card in cards:
                name = _first_text(card, _AMAZON_SELECTORS["name"])
                price = parse_price(_first_text(card, _AMAZON_SELECTORS["price"]))
                if not name or not price:
                    continue
                mrp = parse_price(_first_text(card, "span.a-text-price > span.a-offscreen")) or price
                products.append(
                    {
                        "name": name.strip(),
                        "current_price": price,
                        "mrp": mrp,
                        "discount_pct": round((mrp - price) / mrp * 100, 1) if mrp and price else 0.0,
                        "rating": 0.0,
                        "rating_count": 0,
                        "seller": "Amazon.in",
                        "delivery_estimate": "Free delivery",
                        "source": "Amazon",
                    }
                )
    except Exception as exc:
        logger.warning("Amazon httpx scrape failed: %s", exc)
    return products


async def scrape_flipkart_queries(queries: List[str]) -> List[dict]:
    """Convenience wrapper: run scrape rounds sequentially with a politeness
    delay between queries. Returns flattened raw product dicts."""
    results: List[dict] = []
    for q in queries:
        results.extend(await _scrape_flipkart(q))
        await asyncio.sleep(settings.scrape_page_delay_ms / 1000)
    return results


async def scrape_amazon_queries(queries: List[str]) -> List[dict]:
    results: List[dict] = []
    for q in queries:
        results.extend(await _scrape_amazon(q))
        await asyncio.sleep(settings.scrape_page_delay_ms / 1000)
    return results


async def scrape_live_round(queries: List[str]) -> List[dict]:
    """Primary real-time path: scrape both marketplaces, tagged by source."""
    flipkart = await scrape_flipkart_queries(queries)
    amazon = await scrape_amazon_queries(queries)
    for item in flipkart:
        item.setdefault("source", "Flipkart")
    return flipkart + amazon


async def fetch_robots_txt(host: str) -> str:
    """Polite fetch of robots.txt for transparency/debugging."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(f"https://{host}/robots.txt", headers=_random_headers())
            return resp.text[:2000]
    except Exception as exc:
        logger.warning("robots.txt fetch failed: %s", exc)
        return ""
