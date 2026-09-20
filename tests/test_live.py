import asyncio
import json
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from config import ADAPTERS, REQUEST_TIMEOUT, USER_AGENT
from scraper import MIN_MATCH_SCORE, fetch, search_medicines

QUERY = "مگنیفورت"
KNOWN_PRODUCT_URL = "https://darukala.ir/arian-salamat-magniforte"
KNOWN_PRODUCT_QUERY = "کپسول مگنیفورت آرین سلامت سینا"
REPORT_PATH = Path("live_report.json")


def diagnostic_anchors(soup, base_url):
    rows = []
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        title = a.get_text(" ", strip=True)
        if not href:
            continue
        url = urljoin(base_url, href).split("#")[0]
        if url.startswith(base_url):
            rows.append({"title": title[:180], "url": url[:300]})
        if len(rows) >= 40:
            break
    return rows


def test_live_medicine_search_and_product_parse():
    async def run():
        result = await search_medicines(QUERY)
        adapter = next(a for a in ADAPTERS if a.name == "داروکالا")
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.6",
        }
        diagnostics = []
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers=headers,
            follow_redirects=True,
        ) as client:
            for source in ADAPTERS:
                try:
                    search_url = source.build_search_url(QUERY)
                    response = await client.get(search_url)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, "lxml")
                    diagnostics.append({
                        "source": source.name,
                        "search_url": search_url,
                        "http_status": response.status_code,
                        "final_url": str(response.url),
                        "page_title": soup.title.get_text(" ", strip=True)[:300] if soup.title else "",
                        "anchor_count": len(soup.select("a[href]")),
                        "sample_anchors": diagnostic_anchors(soup, source.base_url),
                        "forms": [
                            {
                                "action": urljoin(str(response.url), form.get("action", "")),
                                "method": form.get("method", "get").lower(),
                                "inputs": [
                                    {
                                        "name": node.get("name", ""),
                                        "type": node.get("type", ""),
                                        "value": node.get("value", ""),
                                    }
                                    for node in form.select("input[name]")
                                ][:12],
                            }
                            for form in soup.select("form")
                        ][:10],
                    })
                except Exception as exc:
                    diagnostics.append({
                        "source": source.name,
                        "search_url": getattr(source, "build_search_url", lambda q: "")(QUERY),
                        "error": f"{type(exc).__name__}: {exc}",
                    })

            html, status = await fetch(client, KNOWN_PRODUCT_URL)
        product = adapter.parse_product(
            BeautifulSoup(html, "lxml"),
            KNOWN_PRODUCT_URL,
            KNOWN_PRODUCT_QUERY,
        )
        return result, status, product, diagnostics

    result, product_http_status, product, diagnostics = asyncio.run(run())

    report = {
        "query": result["query"],
        "checked_at": result["checked_at"],
        "result_count": result["result_count"],
        "sources": result["source_status"],
        "results": result["results"],
        "search_diagnostics": diagnostics,
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

    assert product_http_status == 200
    assert product is not None
    assert "مگنیفورت" in product.title
    assert product.price is not None
