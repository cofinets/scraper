from dataclasses import dataclass

from sources.daroohome import DaroohomeAdapter
from sources.mofidteb import MofidTebAdapter
from sources.wordpress import WordPressAdapter

@dataclass(frozen=True)
class Source:
    name: str
    base_url: str
    search_url: str
    address: str
    phone: str
    enabled: bool = True

SOURCES = [
    Source("مثبت سبز", "https://mosbatesabz.com", "https://mosbatesabz.com/?s={query}&post_type=product", "تهران، ایران", ""),
    Source("داروکالا", "https://darukala.ir", "https://darukala.ir/?s={query}&post_type=product", "تهرانپارس، تهران، ایران", "021-77703234"),
    Source("دارولاین", "https://darooline.com", "https://darooline.com/?s={query}", "ایران", ""),
]

ADAPTERS = [
    WordPressAdapter("مثبت سبز", "https://mosbatesabz.com", "تهران، ایران", ""),
    WordPressAdapter("داروکالا", "https://darukala.ir", "تهرانپارس، تهران، ایران", "021-77703234"),
    WordPressAdapter("دارولاین", "https://darooline.com", "ایران", ""),
    MofidTebAdapter(),
    DaroohomeAdapter(),
]

USER_AGENT = "IranMedicineScraper/1.1 (+https://github.com/cofinets/scraper)"
REQUEST_TIMEOUT = 20.0
MAX_SEARCH_RESULTS_PER_SOURCE = 8
MAX_CONCURRENT_REQUESTS = 6
