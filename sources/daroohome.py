from .wordpress import WordPressAdapter

class DaroohomeAdapter(WordPressAdapter):
    def __init__(self):
        super().__init__(
            name="داروهوم",
            base_url="https://daroohome.com",
            address="ایران",
            phone="",
            search_template="https://daroohome.com/?s={query}",
        )

    def search_links(self, soup, query):
        links = super().search_links(soup, query)
        # Daroohome uses /c/ for category pages and /p/ for product pages.
        # Only product pages should become medicine offers.
        return [url for url in links if "/p/" in url.lower()][:8]
