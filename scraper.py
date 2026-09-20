from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup
from rapidfuzz.fuzz import WRatio

from config import SOURCES, USER_AGENT, REQUEST_TIMEOUT, MAX_SEARCH_RESULTS_PER_SOURCE, MAX_CONCURRENT_REQUESTS

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

def normalize_text(value: str) -> str:
    value = (value or "").translate(PERSIAN_DIGITS)
    value = value.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    return re.sub(r"\\s+", " ", value).strip().lower()

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
            return money_to_int(m.group(1)), ("تومان" if "تومان" in m.group(0) or "تومن" in m.group(0) else "ریال")
    return None, None

def detect_stock(text: str):
    t = normalize_text(text)
    negative = ["در انبار موجود نمی باشد", "در انبار موجود نیست", "ناموجود", "اتمام موجودی", "sold out", "out of stock"]
    positive = ["موجود در انبار", "در انبار موجود است", "موجود است", "افزودن به سبد خرید", "add to cart", "in stock"]
    for phrase in negative:
        if phrase in t:
            return False, phrase
    for phrase in positive:
        if phrase in t:
            return True, phrase
    return None, "نامشخص"

def extract_title(soup: BeautifulSoup) -> str:
    for selector in ["h1.product_title", "h1.entry-title", "h1", 'meta[property="og:title"]', "title"]:
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
        combined = normalize_text(f"{a.get_text(' ', strip=True)} {url}")
        score = WRatio(q, combined)
        if q in combined:
            score += 25
        if score >= 45 and url not in seen:
            seen.add(url)
            candidates.append((score, url))
    candidates.sort(reverse=True)
    return [url for _, url in candidates[:MAX_SEARCH_RESULTS_PER_SOURCE]]

async def fetch(client: httpx.AsyncClient, url: str):
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()
    return response.text, response.status_code

async def search_source(client, source, query):
    try:
        html, _ = await fetch(client, source.search_url.format(query=quote(query)))
        soup = BeautifulSoup(html, "lxml")
        links = extract_search_links(soup, source.base_url, query)
        if not links:
            links = [urljoin(source.base_url, a["href"]).split("#")[0] for a in soup.select("a[href]") if "/product/" in a.get("href", "")]
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
    score = round(WRatio(normalize_text(query), normalize_text(title)), 1)
    if score < 45:
        return None
    text = soup.get_text(" ", strip=True)
    price, currency = detect_price(soup, text)
    stock, evidence = detect_stock(text)
    description = ""
    for selector in [".woocommerce-product-details__short-description", ".short-description", ".product-short-description", "meta[name='description']"]:
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
        "source": source.name, "url": url, "title": title, "match_score": score,
        "price": price, "currency": currency, "stock": stock, "stock_evidence": evidence,
        "address": source.address, "phone": source.phone, "brand": brand,
        "description": description[:1200], "http_status": status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

async def search_medicines(query: str) -> dict:
    query = query.strip()
    if not query:
        raise ValueError("نام دارو الزامی است.")
    limits = httpx.Limits(max_connections=MAX_CONCURRENT_REQUESTS, max_keepalive_connections=MAX_CONCURRENT_REQUESTS)
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.6"}
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=headers, limits=limits) as client:
        enabled = [s for s in SOURCES if s.enabled]
        source_links = await asyncio.gather(*(search_source(client, s, query) for s in enabled))
        jobs = [parse_product(client, s, link, query) for s, links in zip(enabled, source_links) for link in links]
        products = [p for p in await asyncio.gather(*jobs) if p]
    products.sort(key=lambda x: (x["stock"] is True, x["price"] is not None, x["match_score"]), reverse=True)
    return {
        "query": query,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "result_count": len(products),
        "results": products,
        "note": "قیمت و موجودی فقط در زمان بررسی صفحه منبع گزارش شده‌اند. برای داروهای نسخه‌ای، وجود صفحه فروش اینترنتی به معنی مجاز بودن فروش بدون نسخه نیست.",
    }
