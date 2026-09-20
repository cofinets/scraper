import asyncio
import json
from pathlib import Path

from config import ADAPTERS
from scraper import search_medicines

QUERY = "استامینوفن"
REPORT_PATH = Path("live_report.json")

def test_live_medicine_search():
    result = asyncio.run(search_medicines(QUERY))

    report = {
        "query": result["query"],
        "checked_at": result["checked_at"],
        "result_count": result["result_count"],
        "sources": result["source_status"],
        "results": result["results"],
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== LIVE MEDICINE SCRAPER REPORT ===")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    assert result["query"] == QUERY
    assert len(result["sources_checked"]) == len(ADAPTERS)
    assert len(result["source_status"]) == len(ADAPTERS)

    reachable = [
        s for s in result["source_status"]
        if s["status"] in {"ok", "partial"}
    ]
    assert reachable, f"No live source was reachable: {result['source_status']}"
    assert result["result_count"] > 0, (
        f"Live search returned no products: {result['source_status']}"
    )

    # A successful source should expose enough telemetry to distinguish
    # "website reachable" from "product actually parsed".
    for status in result["source_status"]:
        assert "search_http_status" in status
        assert "search_links" in status
        assert "parsed_products" in status
