from .wordpress import WordPressAdapter


class DaroohomeAdapter(WordPressAdapter):
    def __init__(self):
        super().__init__(
            name="داروهوم",
            base_url="https://daroohome.com",
            address="تهران، خیابان شریعتی، بالاتر از تقاطع میرداماد، کوچه آهور، پلاک 40",
            phone="02126720712",
            search_template="https://daroohome.com/?s={query}",
        )

    def search_links(self, soup, query):
        # Daroohome currently renders many product/category links on the
        # server-side search page. Do not assume a fixed /p/ product path;
        # rank only visible links whose titles actually match the query.
        from scraper import is_relevant, relevance_score
        from urllib.parse import urljoin, urlparse

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
            path = urlparse(url).path.lower()
            if any(x in path for x in ("/c/", "/blog/", "/result/", "/cart", "/checkout", "/my-account")):
                continue
            if is_relevant(query, title):
                seen.add(url)
                ranked.append((relevance_score(query, title), url))

        ranked.sort(reverse=True)
        return [url for _, url in ranked[:8]]
