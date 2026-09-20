import argparse
import asyncio
import json
from scraper import search_medicines

def main():
    parser = argparse.ArgumentParser(description="جستجوی قیمت و موجودی دارو در ایران")
    parser.add_argument("medicine", nargs="?", help="نام دارو")
    args = parser.parse_args()
    medicine = args.medicine or input("نام دارو: ").strip()
    print(json.dumps(asyncio.run(search_medicines(medicine)), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
