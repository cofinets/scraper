import asyncio
import json

from config import ADAPTERS
from scraper import search_medicines

def test_live_medicine_search():
    result = asyncio.run(search_medicines("استامینوفن"))
    print(json.dumps({
        "query": result["query"],
        "result_count": result["result_count"],
        "sources": result["source_status"],
        "sample_results": result["results"][:5],
    }, ensure_ascii=False, indent=2))
    assert result["query"] == "استامینوفن"
    assert len(result["sources_checked"]) == len(ADAPTERS)
    assert len(result["source_status"]) == len(ADAPTERS)

    reachable = [s for s in result["source_status"] if s["status"] in {"ok", "partial"}]
    assert reachable, f"No live source was reachable: {result['source_status']}"
    assert result["result_count"] > 0, f"Live search returned no products: {result['source_status']}"
