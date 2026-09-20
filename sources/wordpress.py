from __future__ import annotations

from urllib.parse import quote, urljoin, urlparse

from bs4 import BeautifulSoup

from .base import BaseAdapter, ProductCandidate


class WordPressAdapter(BaseAdapter):
    def __init__(self, name, base_url, address="", phone="", search_template=None):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.address = address
        self.phone = phone
        self.search_template = search_template or self.base_url + "/?s={query}&post_type=product"

    def build_search_url(self, query):
        return self.search_template.format(query=quote(query))

    def _looks_like_product_url(self, url):
        path = urlparse(url).path.rstrip("/")
        if not path:
            return False
        if path.startswith("/product/"):
            return True
        return path.count("/") == 1

    def _is_excluded_url(self, url):
        path = urlparse(url).path.lower()
        return any(
            x in path
            for x in (
                "/cart",
                "/checkout",
                "/my-account",
                "/category/",
                "/tag/",
                "/blog/",
                "/feed",
                "/wp-json/",
            )
        )

    def search_links(self, soup, query):
        from scraper import is_relevant, relevance_score

        ranked = []
        seen = set()
        for a in soup.select("a[href]"):
            href = a.get("href", "").strip()
            title = a.get_text(" ", strip=True)
            if not href or not title:
                continue

            url = urljoin(self.base_url, href).split("#")[0]
            if not url.startswith(self.base_url) or url in seen:
                continue
            if self._is_excluded_url(url):
                continue

            score = relevance_score(query, title)
            href_text = normalize_text(url)
            query_tokens = [x for x in normalize_text(query).split() if len(x) >= 2]
            href_match = bool(query_tokens) and (
                sum(x in href_text for x in query_tokens) / len(query_tokens) >= 0.6
            )

            # اولویت با عنوان محصول است؛ اگر متن لینک ضعیف باشد، slug آدرس
            # محصول نیز بررسی می‌شود. این مورد برای نتایجی که عنوان لینک کوتاه
            # یا تصویر است مهم است.
            if is_relevant(query, title):
                seen.add(url)
                ranked.append((score, url))
            elif href_match and score >= 45:
                seen.add(url)
                ranked.append((max(score, 70), url))
            elif self._looks_like_product_url(url) and score >= 78:
                seen.add(url)
                ranked.append((score, url))

        ranked.sort(reverse=True)
        return [url for _, url in ranked[:8]]

    def parse_product(self, soup, url, query):
        from scraper import detect_price, detect_stock, extract_title, is_relevant

        title = extract_title(soup)
        if not title or not is_relevant(query, title):
            return None

        text = soup.get_text(" ", strip=True)
        price, currency = detect_price(soup, text)
        stock, evidence = detect_stock(text)

        brand = ""
        for selector in (".brand", ".product-brand", "[itemprop='brand']"):
            node = soup.select_one(selector)
            if node:
                brand = node.get_text(" ", strip=True)
                break

        description = ""
        for selector in (
            ".woocommerce-product-details__short-description",
            ".short-description",
            ".product-short-description",
            "meta[name='description']",
        ):
            node = soup.select_one(selector)
            if node:
                description = (
                    node.get("content", "")
                    if node.name == "meta"
                    else node.get_text(" ", strip=True)
                )
                if description:
                    break

        return ProductCandidate(
            url,
            title,
            price,
            currency,
            stock,
            evidence,
            brand,
            description[:1200],
        )
