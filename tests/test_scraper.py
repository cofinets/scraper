from bs4 import BeautifulSoup
from scraper import detect_price, detect_stock, normalize_text, money_to_int

def test_persian_normalization():
    assert normalize_text("متفورمین ۵۰۰ ك") == "متفورمین 500 ک"

def test_money_parser():
    assert money_to_int("۱۲۳,۴۵۶ تومان") == 123456

def test_structured_price():
    html='<script type="application/ld+json">{"@type":"Product","offers":{"price":"125000","priceCurrency":"IRR"}}</script>'
    price,currency=detect_price(BeautifulSoup(html,"lxml"),"")
    assert price == 125000
    assert currency == "IRR"

def test_stock_detection():
    assert detect_stock("این محصول موجود در انبار است") [0] is True
    assert detect_stock("اتمام موجودی") [0] is False


def test_stock_schema_in_stock():
    html = '<script type="application/ld+json">{"@type":"Product","offers":{"availability":"https://schema.org/InStock"}}</script>'
    assert detect_stock("", BeautifulSoup(html, "lxml")) == (True, "schema.org: InStock")


def test_stock_disabled_cart():
    html = '<button disabled>افزودن به سبد خرید</button>'
    assert detect_stock("", BeautifulSoup(html, "lxml"))[0] is False
