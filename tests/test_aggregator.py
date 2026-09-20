from aggregator import group_results

def test_groups_same_product():
    items=[
      {"title":"متفورمین 500 میلی گرم شرکت الف","stock":True,"price":100,"match_score":90},
      {"title":"متفورمین ۵۰۰ میلی‌گرم شرکت الف","stock":False,"price":110,"match_score":88},
    ]
    groups=group_results(items)
    assert len(groups)==1
    assert groups[0]["sources"]==2


def test_groups_keep_stock_summary():
    items = [
        {"title": "آموکسی سیلین 500", "stock": True, "price": 200, "match_score": 95},
        {"title": "آموکسی سیلین 500", "stock": None, "price": None, "match_score": 90},
    ]
    groups = group_results(items)
    assert groups[0]["sources"] == 2
    assert groups[0]["available_sources"] == 1
