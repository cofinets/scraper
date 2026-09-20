const $=s=>document.querySelector(s);
let lastData=null, deferredInstall=null, visibleResults=[];

const faNum=n=>new Intl.NumberFormat("fa-IR").format(Number(n)||0);
const money=n=>n==null?"—":faNum(n);
const esc=v=>String(v??"").replace(/[&<>"]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[m]));
const stockInfo=v=>v===true?["موجود","yes"]:v===false?["ناموجود","no"]:["نامشخص","unknown"];
function showToast(t){const x=$("#toast");x.textContent=t;x.classList.add("show");setTimeout(()=>x.classList.remove("show"),2200)}
function setLoading(v){$("#loading").classList.toggle("hidden",!v)}
function statusText(s){return s==="ok"?"فعال":s==="partial"?"ناقص":"خطا"}

async function search(q){
  q=q.trim(); if(q.length<2){showToast("حداقل ۲ کاراکتر وارد کنید");return}
  $("#query").value=q; $("#clearBtn").classList.remove("hidden"); setLoading(true);
  $("#summary").classList.add("hidden"); $("#empty").classList.add("hidden");
  try{
    const r=await fetch("/api/search?q="+encodeURIComponent(q),{headers:{"Accept":"application/json"}});
    const d=await r.json(); if(!r.ok) throw new Error(d.detail||"خطای سرور");
    lastData=d; localStorage.setItem("lastMedicineSearch",JSON.stringify(d)); render(d);
  }catch(e){
    $("#emptyText").textContent=e.message||"ارتباط با سرور برقرار نشد.";
    $("#empty").classList.remove("hidden");
  }finally{setLoading(false)}
}
function render(d){
  $("#welcome").classList.add("hidden"); $("#empty").classList.toggle("hidden",d.result_count!==0);
  $("#summary").classList.toggle("hidden",d.result_count===0);
  $("#resultTitle").textContent=d.query;
  $("#checkedAt").textContent="آخرین بررسی: "+new Date(d.checked_at).toLocaleString("fa-IR");
  const available=d.results.filter(x=>x.stock===true).length;
  const priced=d.results.filter(x=>x.price!=null).length;
  $("#stats").innerHTML=[
    ["نتیجه پیدا شده",d.result_count],["موجود آنلاین",available],["دارای قیمت",priced],["منبع بررسی‌شده",d.sources_checked.length]
  ].map(x=>'<div class="stat"><div class="label">'+x[0]+'</div><div class="value">'+faNum(x[1])+'</div></div>').join("");
  $("#sourceStatus").innerHTML=d.source_status.map(s=>'<div class="source"><div class="source-top"><strong>'+esc(s.source)+'</strong><span><i class="dot '+esc(s.status)+'"></i>'+statusText(s.status)+'</span></div><small>HTTP: '+esc(s.search_http_status??"—")+' · لینک: '+faNum(s.search_links)+' · محصول: '+faNum(s.parsed_products)+(s.error?"<br>"+esc(s.error):"")+'</small></div>').join("");
  renderResults(); renderGroups(d.grouped||[]);
  $("#note").textContent=d.note||"";
}
function renderResults(){
  const filter=$("#filter").value, sort=$("#sort").value;
  visibleResults=(lastData?.results||[]).filter(x=>filter==="all"||(filter==="available"&&x.stock===true)||(filter==="unavailable"&&x.stock===false)||(filter==="unknown"&&x.stock==null));
  visibleResults.sort((a,b)=>{
    if(sort==="price") return (a.price??Infinity)-(b.price??Infinity);
    if(sort==="stock") return Number(b.stock===true)-Number(a.stock===true)||b.match_score-a.match_score;
    if(sort==="source") return a.source.localeCompare(b.source,"fa");
    return b.match_score-a.match_score;
  });
  $("#visibleCount").textContent=faNum(visibleResults.length);
  $("#results").innerHTML=visibleResults.map((x,i)=>{
    const st=stockInfo(x.stock);
    return '<article class="result-card"><div class="result-top"><span class="source-name">'+esc(x.source)+'</span><span class="stock '+st[1]+'">'+st[0]+'</span></div><h3>'+esc(x.title)+'</h3><div class="price">'+money(x.price)+' <small>'+esc(x.currency||"واحد نامشخص")+'</small></div><div class="meta"><div>تطابق <b>'+faNum(x.match_score)+'٪</b></div><div>شواهد موجودی <b>'+esc(x.stock_evidence||"نامشخص")+'</b></div><div>برند <b>'+esc(x.brand||"ثبت نشده")+'</b></div><div>تلفن <b>'+esc(x.phone||"ثبت نشده")+'</b></div></div>'+(x.description?'<div class="description">'+esc(x.description)+'</div>':"")+'<div class="card-actions"><button onclick="detail('+i+')">جزئیات</button><a class="main" href="'+esc(x.url)+'" target="_blank" rel="noopener noreferrer">مشاهده منبع ↗</a></div></article>';
  }).join("")||'<div class="empty card" style="grid-column:1/-1"><div class="empty-icon">⌕</div><h3>برای این فیلتر نتیجه‌ای نیست</h3></div>';
}
function renderGroups(groups){
  if(!groups.length){$("#groupedSection").innerHTML="";return}
  $("#groupedSection").innerHTML='<h3>تجمیع محصولات مشابه</h3>'+groups.map(g=>'<div class="group-card"><strong>'+esc(g.name)+'</strong><span class="muted"> · '+faNum(g.sources)+' منبع · '+faNum(g.available_sources)+' منبع با موجودی</span>'+g.offers.map(x=>'<div class="offer"><span>'+esc(x.source)+' · '+stockInfo(x.stock)[0]+'</span><b>'+money(x.price)+'</b></div>').join("")+'</div>').join("");
}
function detail(i){
  const x=visibleResults[i]; if(!x)return;
  const st=stockInfo(x.stock);
  $("#modalBody").innerHTML='<div class="eyebrow">جزئیات محصول</div><h2>'+esc(x.title)+'</h2><p class="muted">'+esc(x.source)+' · وضعیت: '+st[0]+'</p><div class="detail-grid">'+
  [["قیمت",money(x.price)+" "+(x.currency||"")],["امتیاز تطابق",faNum(x.match_score)+"٪"],["برند",x.brand||"ثبت نشده"],["شواهد موجودی",x.stock_evidence||"نامشخص"],["آدرس",x.address||"ثبت نشده"],["تلفن",x.phone||"ثبت نشده"],["HTTP",x.http_status??"—"],["زمان بررسی",new Date(x.checked_at).toLocaleString("fa-IR")]].map(a=>'<div class="detail"><b>'+a[0]+'</b>'+esc(a[1])+'</div>').join("")+
  '</div><div class="note">'+esc(x.description||"توضیحات جداگانه‌ای استخراج نشده است.")+'</div><a class="primary" style="display:block;text-align:center;text-decoration:none" href="'+esc(x.url)+'" target="_blank" rel="noopener noreferrer">باز کردن صفحه اصلی محصول ↗</a>';
  $("#modal").classList.remove("hidden");
}
$("#searchForm").addEventListener("submit",e=>{e.preventDefault();search($("#query").value)});
$("#query").addEventListener("input",()=>$("#clearBtn").classList.toggle("hidden",!$("#query").value));
$("#clearBtn").onclick=()=>{$("#query").value="";$("#clearBtn").classList.add("hidden");$("#query").focus()};
$("#refreshBtn").onclick=()=>{lastData=null;localStorage.removeItem("lastMedicineSearch");$("#summary").classList.add("hidden");$("#empty").classList.add("hidden");$("#welcome").classList.remove("hidden");$("#query").value=""};
$("#newSearchBtn").onclick=()=>{window.scrollTo({top:0,behavior:"smooth"});$("#query").focus()};
$("#filter").onchange=renderResults;$("#sort").onchange=renderResults;
$("#closeModal").onclick=()=>$("#modal").classList.add("hidden");$(".modal-backdrop").onclick=()=>$("#modal").classList.add("hidden");
$("#copyBtn").onclick=async()=>{if(!lastData)return;try{await navigator.clipboard.writeText(JSON.stringify(lastData,null,2));showToast("JSON کپی شد")}catch{showToast("کپی انجام نشد")}};
$("#exportBtn").onclick=()=>{if(!lastData)return;const blob=new Blob([JSON.stringify(lastData,null,2)],{type:"application/json;charset=utf-8"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="medicine-search-"+Date.now()+".json";a.click();URL.revokeObjectURL(a.href)};
document.querySelectorAll(".chips button").forEach(b=>b.onclick=()=>search(b.dataset.q));
window.addEventListener("beforeinstallprompt",e=>{e.preventDefault();deferredInstall=e;$("#installBtn").classList.remove("hidden")});
$("#installBtn").onclick=async()=>{if(!deferredInstall)return;deferredInstall.prompt();deferredInstall=null;$("#installBtn").classList.add("hidden")};
if("serviceWorker" in navigator) navigator.serviceWorker.register("/app/sw.js").catch(()=>{});
try{const saved=JSON.parse(localStorage.getItem("lastMedicineSearch"));if(saved?.query){lastData=saved;render(saved)}}catch{}
