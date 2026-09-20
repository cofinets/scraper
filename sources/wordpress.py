from __future__ import annotations
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from .base import BaseAdapter, ProductCandidate

class WordPressAdapter(BaseAdapter):
    def __init__(self, name, base_url, address="", phone="", search_template=None):
        self.name=name
        self.base_url=base_url.rstrip("/")
        self.address=address
        self.phone=phone
        self.search_template=search_template or self.base_url + "/?s={query}&post_type=product"

    def build_search_url(self, query):
        return self.search_template.format(query=quote(query))

    def search_links(self, soup, query):
        from scraper import relevance_score, MIN_MATCH_SCORE, normalize_text
        out=[]; seen=set()
        for a in soup.select("a[href]"):
            href=a.get("href","")
            title=a.get_text(" ",strip=True)
            url=urljoin(self.base_url,href).split("#")[0]
            if not url.startswith(self.base_url) or url in seen:
                continue
            if any(x in url.lower() for x in ("/cart","/checkout","/my-account","/category/")):
                continue
            score=relevance_score(query, normalize_text(title))
            if score >= MIN_MATCH_SCORE:
                seen.add(url); out.append((score,url))
        return [u for _,u in sorted(out,reverse=True)[:8]]

    def parse_product(self, soup, url, query):
        from scraper import extract_title, detect_price, detect_stock, relevance_score, MIN_MATCH_SCORE
        title=extract_title(soup)
        score=relevance_score(query,title)
        if not title or score < MIN_MATCH_SCORE:
            return None
        text=soup.get_text(" ",strip=True)
        price,currency=detect_price(soup,text)
        stock,evidence=detect_stock(text)
        brand=""
        for selector in (".brand",".product-brand","[itemprop='brand']"):
            node=soup.select_one(selector)
            if node: brand=node.get_text(" ",strip=True); break
        description=""
        for selector in (".woocommerce-product-details__short-description",".short-description",".product-short-description","meta[name='description']"):
            node=soup.select_one(selector)
            if node:
                description=node.get("content","") if node.name=="meta" else node.get_text(" ",strip=True)
                if description: break
        return ProductCandidate(url,title,price,currency,stock,evidence,brand,description[:1200])
