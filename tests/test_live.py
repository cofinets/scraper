import asyncio
import json
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from config import ADAPTERS, REQUEST_TIMEOUT, USER_AGENT
from scraper import MIN_MATCH_SCORE, fetch, search_medicines

QUERY = "استامینوفن"
KNOWN_PRODUCT_URL = "https://darukala.ir/arian-salamat-magniforte"
KNOWN_PRODUCT_QUERY = "کپسول مگنیفورت آرین سلامت سینا"
REPORT_PATH = Path("live_report.json")

def test_live_medicine_search_and_product_parse():
    async def run():
        result = await search_medicines(QUERY)
        adapter = next(a for a in ADAPTERS if a.name == "داروکالا")
        headers = {"User-Agent": USER_AGENT, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.6"}
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=headers) as client:
            html, status = await fetch(client, KNOWN_PRODUCT_URL)
        product = adapter.parse_product(
            BeautifulSoup(html, "lxml"),
            KNOWN_PRODUCT_URL,
            KNOWN_PRODUCT_QUERY,
        )
        return result, status, product

    result, product_http_status, product = asyncio.run(run())

    report = {
        "query": result["query"],
        "checked_at": result["checked_at"],
        "result_count": result["result_count"],
        "sources": result["source_status"],
        "results": result["results"],
        "known_product_test": {
            "query": KNOWN_PRODUCT_QUERY,
            "url": KNOWN_PRODUCT_URL,
            "http_status": product_http_status,
            "parsed": product is not None,
            "title": product.title if product else None,
            "price": product.price if product else None,
            "currency": product.currency if product else None,
            "stock": product.stock if product else None,
            "stock_evidence": product.stock_evidence if product else None,
        },
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== LIVE MEDICINE SCRAPER REPORT ===")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    assert result["query"] == QUERY
    assert len(result["source_status"]) == len(ADAPTERS)

    reachable = [s for s in result["source_status"] if s["status"] in {"ok", "partial"}]
    assert reachable, result["source_status"]
    assert all(item["match_score"] >= MIN_MATCH_SCORE for item in result["results"])

    # This is a true live product-page parse, independent of the search page.
    assert product_http_status == 200
    assert product is not None
    assert "مگنیفورت" in product.title
    assert product.price is not None
