from pydantic import BaseModel, Field

class MedicineResult(BaseModel):
    source: str
    url: str
    title: str
    match_score: float
    price: int | None = None
    currency: str | None = None
    stock: bool | None = None
    stock_evidence: str = ""
    brand: str = ""
    description: str = ""
    address: str = ""
    phone: str = ""
    checked_at: str

class MedicineSearchResponse(BaseModel):
    query: str
    checked_at: str
    result_count: int
    sources_checked: list[str]
    results: list[MedicineResult]
    grouped: list[dict] = []
    note: str
