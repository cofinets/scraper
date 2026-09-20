import asyncio

import pytest

from config import ADAPTERS, REQUEST_TIMEOUT, USER_AGENT
from scraper import search_medicines

@pytest.mark.integration
def test_live_medicine_search():
    result = asyncio.run(search_medicines("استامینوفن"))
    assert result["query"] == "استامینوفن"
    assert len(result["sources_checked"]) == len(ADAPTERS)
    assert len(result["source_status"]) == len(ADAPTERS)
    assert all("status" in item and "source" in item for item in result["source_status"])
    assert result["result_count"] >= 0
