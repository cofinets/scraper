import asyncio
import json
from pathlib import Path

from config import ADAPTERS
from scraper import MIN_MATCH_SCORE, search_medicines

QUERIES = [
    "استامینوفن",
    "قرص جویدنی ویتامین ث 250 مهر دارو",
]
REPORT_PATH = Path("live_report.json")

def test_live_medicine_search():
    reports = []
    for query in QUERIES:
        result = asyncio.run(search_medicines(query))
        reports.append({
            "query": result["query"],
            "checked_at": result["checked_at"],
            "result_count": result["result_count"],
            "sources": result["source_status"],
            "results": result["results"],
        })

    REPORT_PATH.write_text(
        json.dumps({"queries": reports}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== LIVE MEDICINE SCRAPER REPORT ===")
    print(json.dumps({"queries": reports}, ensure_ascii=False, indent=2))

    assert all(len(r["sources"]) == len(ADAPTERS) for r in reports)

    for report in reports:
        reachable = [s for s in report["sources"] if s["status"] in {"ok", "partial"}]
        assert reachable, f"No live source was reachable for {report['query']}: {report['sources']}"
        assert all(
            item["match_score"] >= MIN_MATCH_SCORE for item in report["results"]
        )

    # The second query is a concrete product known to be indexed by an
    # active source, so this verifies that the scraper can return real data,
    # not merely a reachable website.
    assert reports[1]["result_count"] > 0, reports[1]["sources"]
