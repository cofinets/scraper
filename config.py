from dataclasses import dataclass

from sources.daroohome import DaroohomeAdapter
from sources.wordpress import WordPressAdapter as WPAdapter
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
    WordPressAdapter("داروکالا", "https://darukala.ir", "تهرانپارس، تهران، ایران", "021-77703234", "https://darukala.ir/index.php?route=product/search&search={query}"),
    WordPressAdapter("دارولاین", "https://darooline.com", "ایران", ""),
    MofidTebAdapter(),
    DaroohomeAdapter(),
    # داروکده در حال حاضر به عنوان منبع آزمایشی اضافه شده؛ endpoint جست‌وجوی
    # آن ممکن است با تغییر سایت عوض شود و وضعیتش در source_status مشخص می‌شود.
    WPAdapter("داروکده", "https://www.darukade.com", "تهران، خیابان جمالزاده شمالی، پلاک 251", "021-62747000", "https://www.darukade.com/search?q={query}"),
]

USER_AGENT = "IranMedicineScraper/1.1 (+https://github.com/cofinets/scraper)"
REQUEST_TIMEOUT = 20.0
MAX_SEARCH_RESULTS_PER_SOURCE = 8
MAX_CONCURRENT_REQUESTS = 6
