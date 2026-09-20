from aggregator import group_results

def test_groups_same_product():
    items=[
      {"title":"متفورمین 500 میلی گرم شرکت الف","stock":True,"price":100,"match_score":90},
      {"title":"متفورمین ۵۰۰ میلی‌گرم شرکت الف","stock":False,"price":110,"match_score":88},
    ]
    groups=group_results(items)
    assert len(groups)==1
    assert groups[0]["sources"]==2
