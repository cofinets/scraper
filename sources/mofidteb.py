from .wordpress import WordPressAdapter

class MofidTebAdapter(WordPressAdapter):
    def __init__(self):
        super().__init__(
            name="مفیدطب",
            base_url="https://www.mofidteb.com",
            address="مشهد - خیابان سلمان فارسی - بین سلمان 3 و 3/1",
            phone="",
            search_template="https://www.mofidteb.com/search?q={query}",
        )
