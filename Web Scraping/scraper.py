import os
import requests
from bs4 import BeautifulSoup
import json

BASE_URL = "https://www.shl.com/products/product-catalog/"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.shl.com/"
}

def scrape_assessments():
    all_assessments = []
    seen_urls = set()

    for start in range(0, 384, 12):
        page_url = f"{BASE_URL}?start={start}&type=1&type=1"
        print(f"Scraping start={start}")

        response = requests.get(page_url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        rows = soup.find_all("tr", attrs={"data-entity-id": True})
        print("Rows found:", len(rows))

        if len(rows) == 0:
            print("No rows found. Breaking.")
            break

        for row in rows:
            link = row.find("a", href=True)
            if link:
                name = link.text.strip()
                url = "https://www.shl.com" + link["href"]

                if url not in seen_urls:
                    seen_urls.add(url)
                    all_assessments.append({
                        "name": name,
                        "url": url
                    })

    print("\nTotal Individual Test Solutions collected:", len(all_assessments))

    os.makedirs("data", exist_ok=True)

    with open("data/shl_catalog_basic.json", "w", encoding="utf-8") as f:
        json.dump(all_assessments, f, indent=4)

    print("Saved to data/shl_catalog_basic.json")


if __name__ == "__main__":
    scrape_assessments()