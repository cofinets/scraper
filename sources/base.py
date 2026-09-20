from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import quote
from bs4 import BeautifulSoup

@dataclass(frozen=True)
class ProductCandidate:
    url: str
    title: str
    price: int | None
    currency: str | None
    stock: bool | None
    stock_evidence: str
    brand: str
    description: str

class BaseAdapter:
    name = "base"
    base_url = ""
    address = ""
    phone = ""

    def build_search_url(self, query: str) -> str:
        raise NotImplementedError

    def search_links(self, soup: BeautifulSoup, query: str) -> list[str]:
        raise NotImplementedError

    def parse_product(self, soup: BeautifulSoup, url: str, query: str) -> ProductCandidate | None:
        raise NotImplementedError

    def source_meta(self) -> dict:
        return {"source": self.name, "address": self.address, "phone": self.phone}
