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
