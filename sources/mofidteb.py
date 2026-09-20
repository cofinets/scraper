from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from .wordpress import WordPressAdapter


class MofidTebAdapter(WordPressAdapter):
    def __init__(self):
        super().__init__(
            name="مفیدطب",
            base_url="https://www.mofidteb.com",
            address="مشهد - خیابان سلمان فارسی - بین سلمان 3 و 3/1",
            phone="",
            search_template="https://www.mofidteb.com/search?search={query}",
        )

    def search_links(self, soup: BeautifulSoup, query: str) -> list[str]:
        from scraper import is_relevant, relevance_score

        candidates = []
        seen = set()
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            title = a.get_text(" ", strip=True)
            if not href or not title:
                continue
            url = urljoin(self.base_url, href).split("#")[0]
            if not url.startswith(self.base_url) or url in seen:
                continue
            path = url.lower()
            if any(x in path for x in ("/cart", "/checkout", "/account", "/login", "/category")):
                continue
            if not is_relevant(query, title):
                continue
            candidates.append((relevance_score(query, title), url))
            seen.add(url)
        candidates.sort(reverse=True)
        return [url for _, url in candidates[:8]]
