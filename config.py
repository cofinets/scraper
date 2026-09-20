from dataclasses import dataclass

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

USER_AGENT = "IranMedicineScraper/1.0 (+https://github.com/cofinets/scraper)"
REQUEST_TIMEOUT = 20.0
MAX_SEARCH_RESULTS_PER_SOURCE = 8
MAX_CONCURRENT_REQUESTS = 6
