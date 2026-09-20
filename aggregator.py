from collections import defaultdict
from rapidfuzz.fuzz import WRatio

def normalize_name(value: str) -> str:
    import re
    value=(value or "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹","0123456789"))
    value=value.replace("ي","ی").replace("ك","ک")
    return re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE).lower()

def group_results(results: list[dict]) -> list[dict]:
    groups=[]
    for item in results:
        key=normalize_name(item["title"])
        placed=False
        for g in groups:
            if WRatio(key,g["normalized_name"]) >= 82:
                g["offers"].append(item)
                placed=True
                break
        if not placed:
            groups.append({"name":item["title"],"normalized_name":key,"offers":[item]})
    for g in groups:
        g["offers"].sort(key=lambda x:(x.get("stock") is True, x.get("price") is not None, x.get("match_score",0)), reverse=True)
        g["sources"]=len(g["offers"])
        g["available_sources"]=sum(x.get("stock") is True for x in g["offers"])
    for g in groups:
        g.pop("normalized_name",None)
    return groups
