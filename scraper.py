from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup
from rapidfuzz.fuzz import WRatio

from aggregator import group_results
from config import (
    SOURCES,
    ADAPTERS,
    USER_AGENT,
    REQUEST_TIMEOUT,
    MAX_SEARCH_RESULTS_PER_SOURCE,
    MAX_CONCURRENT_REQUESTS,
)

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
MIN_MATCH_SCORE = 68.0


def normalize_text(value: str) -> str:
    value = (value or "").translate(PERSIAN_DIGITS)
    value = value.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    value = re.sub(r"[\u200c\u200f\u202a-\u202e]", " ", value)
    # «گارداسیل9» و «گارداسیل ۹» را یکسان می‌کند.
    value = re.sub(r"(?<=[^\W\d_])(?=\d)", " ", value, flags=re.UNICODE)
    value = re.sub(r"(?<=\d)(?=[^\W\d_])", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip().lower()


def relevance_score(query: str, title: str) -> float:
    q = normalize_text(query)
    t = normalize_text(title)
    if not q or not t:
        return 0.0
    if q in t:
        return 100.0
    q_tokens = [x for x in q.split() if len(x) >= 2]
    if q_tokens:
        covered = sum(1 for token in q_tokens if token in t)
        coverage = covered / len(q_tokens)
        if coverage == 1.0:
            return 92.0
    return round(WRatio(q, t), 1)


def is_relevant(query: str, title: str) -> bool:
    q = normalize_text(query)
    t = normalize_text(title)
    if not q or not t:
        return False
    if q in t:
        return True
    tokens = [x for x in q.split() if len(x) >= 2]
    if len(tokens) <= 1:
        return WRatio(q, t) >= MIN_MATCH_SCORE
    covered = sum(1 for token in tokens if token in t)
    coverage = covered / len(tokens)
    return coverage >= 0.60 and WRatio(q, t) >= 55


def money_to_int(value: str | None) -> int | None:
    if not value:
        return None
    digits = re.sub(r"[^0-9]", "", value.translate(PERSIAN_DIGITS))
    return int(digits) if digits else None


def detect_price(soup: BeautifulSoup, text: str):
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text())
        except Exception:
            continue
        for obj in (data if isinstance(data, list) else [data]):
            if not isinstance(obj, dict):
                continue
            offers = obj.get("offers")
            if isinstance(offers, dict) and offers.get("price") is not None:
                p = money_to_int(str(offers["price"]))
                if p is not None:
                    return p, offers.get("priceCurrency")
    patterns = [
        r"([۰-۹0-9][۰-۹0-9,\.\s]{2,})\s*(?:تومان|تومن)",
        r"(?:قیمت(?:\s+مصرف‌کننده)?\s*:?)\s*([۰-۹0-9][۰-۹0-9,\.\s]{2,})",
        r"([۰-۹0-9][۰-۹0-9,\.\s]{2,})\s*ریال",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return money_to_int(m.group(1)), (
                "تومان"
                if "تومان" in m.group(0) or "تومن" in m.group(0)
                else "ریال"
            )
    return None, None


def detect_stock(text: str, soup: BeautifulSoup | None = None):
    """تشخیص موجودی با اولویت schema.org و کنترل فعال/غیرفعال بودن خرید."""
    t = normalize_text(text)
    if soup is not None:
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or script.get_text())
            except Exception:
                continue
            for obj in (data if isinstance(data, list) else [data]):
                if not isinstance(obj, dict):
                    continue
                offers = obj.get("offers")
                for offer in (offers if isinstance(offers, list) else [offers]):
                    if not isinstance(offer, dict):
                        continue
                    availability = normalize_text(str(offer.get("availability", "")))
                    if "outofstock" in availability or "soldout" in availability:
                        return False, "schema.org: OutOfStock"
                    if "instock" in availability or "limitedavailability" in availability:
                        return True, "schema.org: InStock"

        for node in soup.select("button, input[type='submit'], a"):
            label = normalize_text(node.get_text(" ", strip=True) or node.get("value", ""))
            classes = normalize_text(" ".join(node.get("class", [])))
            disabled = node.has_attr("disabled") or "disabled" in classes or node.get("aria-disabled") == "true"
            if any(x in label for x in ("افزودن به سبد خرید", "افزودن به سبد", "add to cart", "buy now")):
                if disabled:
                    return False, "دکمه خرید غیرفعال"
                return True, "دکمه خرید فعال"

    negative = [
        "در انبار موجود نمی باشد",
        "در انبار موجود نیست",
        "ناموجود",
        "اتمام موجودی",
        "sold out",
        "out of stock",
    ]
    positive = [
        "موجود در انبار",
        "در انبار موجود است",
        "موجود است",
        "افزودن به سبد خرید",
        "add to cart",
        "in stock",
    ]
    for phrase in negative:
        if phrase in t:
            return False, phrase
    for phrase in positive:
        if phrase in t:
            return True, phrase
    return None, "نامشخص"


def extract_title(soup: BeautifulSoup) -> str:
    for selector in [
        "h1.product_title",
        "h1.entry-title",
        "h1",
        'meta[property="og:title"]',
        "title",
    ]:
        node = soup.select_one(selector)
        if node:
            value = node.get("content") if node.name == "meta" else node.get_text(" ", strip=True)
            if value:
                return value.strip()
    return ""


def extract_search_links(soup: BeautifulSoup, base_url: str, query: str):
    q = normalize_text(query)
    candidates = []
    seen = set()
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if not href:
            continue
        url = urljoin(base_url, href).split("#")[0]
        if not url.startswith(base_url):
            continue
        if any(x in url.lower() for x in ["/cart", "/checkout", "/my-account", "/category/"]):
            continue
        anchor_text = a.get_text(" ", strip=True)
        combined = normalize_text(f"{anchor_text} {url}")
        score = relevance_score(q, combined)
        if is_relevant(query, combined) and url not in seen:
            seen.add(url)
            candidates.append((score, url))
    candidates.sort(reverse=True)
    return [url for _, url in candidates[:MAX_SEARCH_RESULTS_PER_SOURCE]]


async def fetch(client: httpx.AsyncClient, url: str):
    browser_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.7,en;q=0.5",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }

    last_exc = None
    for attempt in range(2):
        try:
            response = await client.get(
                url,
                follow_redirects=True,
                headers=browser_headers if attempt else None,
            )
            if attempt == 0 and response.status_code in {403, 429, 500, 502, 503, 504}:
                await asyncio.sleep(0.4)
                continue
            response.raise_for_status()
            return response.text, response.status_code
        except (httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            last_exc = exc
            if attempt == 0:
                await asyncio.sleep(0.25)
                continue
            raise
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if attempt == 0 and exc.response.status_code in {403, 429, 500, 502, 503, 504}:
                await asyncio.sleep(0.4)
                continue
            raise

    if last_exc:
        raise last_exc
    raise RuntimeError("HTTP fetch failed")


async def search_source(client, source, query):
    try:
        html, _ = await fetch(client, source.search_url.format(query=quote(query)))
        soup = BeautifulSoup(html, "lxml")
        links = extract_search_links(soup, source.base_url, query)
        if not links:
            links = [
                urljoin(source.base_url, a["href"]).split("#")[0]
                for a in soup.select("a[href]")
                if "/product/" in a.get("href", "")
            ]
        return list(dict.fromkeys(links))[:MAX_SEARCH_RESULTS_PER_SOURCE]
    except Exception:
        return []


async def parse_product(client, source, url, query):
    try:
        html, status = await fetch(client, url)
    except Exception:
        return None
    soup = BeautifulSoup(html, "lxml")
    title = extract_title(soup)
    if not title:
        return None
    score = relevance_score(query, title)
    if score < MIN_MATCH_SCORE:
        return None
    text = soup.get_text(" ", strip=True)
    price, currency = detect_price(soup, text)
    stock, evidence = detect_stock(text, soup)
    description = ""
    for selector in [
        ".woocommerce-product-details__short-description",
        ".short-description",
        ".product-short-description",
        "meta[name='description']",
    ]:
        node = soup.select_one(selector)
        if node:
            description = node.get("content", "") if node.name == "meta" else node.get_text(" ", strip=True)
            if description:
                break
    brand = ""
    for selector in [".brand", ".product-brand", "[itemprop='brand']"]:
        node = soup.select_one(selector)
        if node:
            brand = node.get_text(" ", strip=True)
            break
    return {
        "source": source.name,
        "url": url,
        "title": title,
        "match_score": score,
        "price": price,
        "currency": currency,
        "stock": stock,
        "stock_evidence": evidence,
        "address": source.address,
        "phone": source.phone,
        "brand": brand,
        "description": description[:1200],
        "http_status": status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


async def search_medicines_legacy(query: str) -> dict:
    query = query.strip()
    if not query:
        raise ValueError("نام دارو الزامی است.")
    limits = httpx.Limits(
        max_connections=MAX_CONCURRENT_REQUESTS,
        max_keepalive_connections=MAX_CONCURRENT_REQUESTS,
    )
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.6"}
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=headers, limits=limits) as client:
        enabled = [s for s in SOURCES if s.enabled]
        source_links = await asyncio.gather(*(search_source(client, s, query) for s in enabled))
        jobs = [
            parse_product(client, s, link, query)
            for s, links in zip(enabled, source_links)
            for link in links
        ]
        products = [p for p in await asyncio.gather(*jobs) if p]
    products.sort(
        key=lambda x: (x["stock"] is True, x["price"] is not None, x["match_score"]),
        reverse=True,
    )
    return {
        "query": query,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "result_count": len(products),
        "results": products,
        "note": "قیمت و موجودی فقط در زمان بررسی صفحه منبع گزارش شده‌اند. برای داروهای نسخه‌ای، وجود صفحه فروش اینترنتی به معنی مجاز بودن فروش بدون نسخه نیست.",
    }


async def search_adapter(client, adapter, query):
    try:
        html, search_status = await fetch(client, adapter.build_search_url(query))
        soup = BeautifulSoup(html, "lxml")
        links = adapter.search_links(soup, query)
        results = []
        failed_pages = 0
        for url in links:
            try:
                page_html, page_status = await fetch(client, url)
                product = adapter.parse_product(BeautifulSoup(page_html, "lxml"), url, query)
                if product:
                    results.append(
                        {
                            "source": adapter.name,
                            "url": product.url,
                            "title": product.title,
                            "match_score": relevance_score(query, product.title),
                            "price": product.price,
                            "currency": product.currency,
                            "stock": product.stock,
                            "stock_evidence": product.stock_evidence,
                            "address": adapter.address,
                            "phone": adapter.phone,
                            "brand": product.brand,
                            "description": product.description,
                            "http_status": page_status,
                            "checked_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
            except Exception:
                failed_pages += 1
        return results, {
            "source": adapter.name,
            "status": "ok" if failed_pages == 0 else "partial",
            "search_http_status": search_status,
            "search_links": len(links),
            "parsed_products": len(results),
            "failed_pages": failed_pages,
            "error": None,
        }
    except Exception as exc:
        return [], {
            "source": adapter.name,
            "status": "error",
            "search_http_status": None,
            "search_links": 0,
            "parsed_products": 0,
            "failed_pages": 0,
            "error": f"{type(exc).__name__}: {str(exc) or 'no message'}"[:300],
        }


async def search_medicines(query: str) -> dict:
    query = query.strip()
    if not query:
        raise ValueError("نام دارو الزامی است.")
    limits = httpx.Limits(
        max_connections=MAX_CONCURRENT_REQUESTS,
        max_keepalive_connections=MAX_CONCURRENT_REQUESTS,
    )
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.6"}
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=headers, limits=limits) as client:
        batches = await asyncio.gather(*(search_adapter(client, adapter, query) for adapter in ADAPTERS))
    products = [item for batch, _status in batches for item in batch]
    source_status = [status for _batch, status in batches]
    products.sort(
        key=lambda x: (x["stock"] is True, x["price"] is not None, x["match_score"]),
        reverse=True,
    )
    return {
        "query": query,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "result_count": len(products),
        "sources_checked": [a.name for a in ADAPTERS],
        "source_status": source_status,
        "results": products,
        "note": "قیمت و موجودی فقط در زمان بررسی صفحه منبع گزارش شده‌اند. موجودی آنلاین لزوماً موجودی فیزیکی لحظه‌ای نیست. برای داروهای نسخه‌ای، وجود صفحه فروش اینترنتی به معنی مجاز بودن فروش بدون نسخه نیست.",
    }
