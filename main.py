from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from scraper import search_medicines

app = FastAPI(title="Iran Medicine Availability Scraper", version="1.0.0")

@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>جستجوی دارو</title>
<style>
body{font-family:Tahoma,Arial,sans-serif;background:#f4f7fb;margin:0;color:#172033}
main{max-width:1100px;margin:40px auto;padding:24px}.card{background:white;border-radius:18px;padding:24px;box-shadow:0 8px 30px #0001}
input,button{font:inherit;padding:12px;border-radius:10px;border:1px solid #ccd3df}input{width:65%}button{cursor:pointer;background:#172033;color:white}
table{width:100%;border-collapse:collapse;margin-top:18px}th,td{padding:12px;border-bottom:1px solid #e8ecf2;text-align:right}.ok{color:#087443;font-weight:bold}.no{color:#b42318;font-weight:bold}.unknown{color:#667085}a{color:#175cd3}
</style></head><body><main><div class="card"><h1>جستجوی دارو در ایران</h1>
<p>نام دارو را وارد کنید؛ قیمت، موجودی، منبع و مشخصات صفحه نمایش داده می‌شود.</p>
<input id="q" placeholder="مثلاً: متفورمین ۵۰۰"><button onclick="go()">جستجو</button><div id="status"></div><div id="out"></div>
</div></main><script>
async function go(){const q=document.getElementById('q').value.trim();if(!q)return;
document.getElementById('status').innerText='در حال بررسی منابع...';document.getElementById('out').innerHTML='';
const r=await fetch('/api/search?q='+encodeURIComponent(q));const d=await r.json();
if(!r.ok){document.getElementById('status').innerText=d.detail||'خطا';return}
document.getElementById('status').innerText='تعداد نتایج: '+d.result_count;
let html='<table><tr><th>دارو</th><th>منبع</th><th>قیمت</th><th>موجودی</th><th>آدرس</th><th>صفحه</th></tr>';
for(const x of d.results){const stock=x.stock===true?'<span class="ok">موجود</span>':x.stock===false?'<span class="no">ناموجود</span>':'<span class="unknown">نامشخص</span>';
const price=x.price==null?'—':new Intl.NumberFormat('fa-IR').format(x.price)+' '+(x.currency||'');
html+=`<tr><td>${esc(x.title)}</td><td>${esc(x.source)}</td><td>${price}</td><td>${stock}</td><td>${esc(x.address||'')}</td><td><a href="${x.url}" target="_blank" rel="noopener">مشاهده</a></td></tr>`;}
document.getElementById('out').innerHTML=html+'</table>'}
function esc(s){return String(s||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]))}
</script></body></html>"""

@app.get("/api/search")
async def api_search(q: str = Query(..., min_length=2)):
    try:
        return await search_medicines(q)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"خطا در بررسی منابع: {exc}")
