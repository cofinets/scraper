from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from scraper import search_medicines

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(
    title="Iran Medicine Scraper",
    version="1.1.0",
    description="جست‌وجوی چندمنبعی اطلاعات دارو و محصولات دارویی/سلامتی"
)

# فایل‌های PWA از /app سرو می‌شوند و صفحه اصلی / نیز همان رابط را نمایش می‌دهد.
app.mount("/app", StaticFiles(directory=WEB_DIR, html=True), name="pwa")


@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "iran-medicine-scraper", "version": app.version}


@app.get("/api/search")
async def api_search(q: str = Query(..., min_length=2, max_length=120)):
    q = q.strip()
    if not q:
        raise HTTPException(status_code=400, detail="نام دارو الزامی است.")
    try:
        return await search_medicines(q)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"خطا در بررسی منابع: {type(exc).__name__}: {exc}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
