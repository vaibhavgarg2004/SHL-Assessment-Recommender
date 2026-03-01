import os
import json
import requests
import re
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.shl.com/"
}


def extract_sections(soup):
    data = {
        "description": "",
        "job_levels": "",
        "languages": "",
        "assessment_length": "",
        "duration": None,
        "test_type": []
    }

    # -------- Extract main sections --------
    rows = soup.find_all("div", class_="product-catalogue-training-calendar__row")

    for row in rows:
        heading = row.find("h4")
        paragraph = row.find("p")

        if heading and paragraph:
            title = heading.get_text(strip=True)
            value = paragraph.get_text(strip=True)

            if "Description" in title:
                data["description"] = value
            elif "Job levels" in title:
                data["job_levels"] = value
            elif "Languages" in title:
                data["languages"] = value
            elif "Assessment length" in title:
                data["assessment_length"] = value

                # Extract numeric duration
                match = re.search(r"(\d+)", value)
                if match:
                    data["duration"] = int(match.group(1))

    # -------- Extract Test Type (Correct Way) --------
    test_type = []

    small_text_ps = soup.find_all("p", class_="product-catalogue__small-text")

    for p in small_text_ps:
        text = p.get_text(strip=True)

        if "Test Type" in text:
            keys = p.find_all("span", class_="product-catalogue__key")
            test_type = [k.get_text(strip=True) for k in keys]
            break

    data["test_type"] = test_type

    return data


def enrich_assessments():
    with open("data/shl_catalog_basic.json", "r", encoding="utf-8") as f:
        assessments = json.load(f)

    enriched = []

    # Limit to first 2 for testing
    for i, item in enumerate(assessments):
        print(f"Enriching {i+1}/377: {item['name']}")

        response = requests.get(item["url"], headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        sections = extract_sections(soup)

        enriched.append({
            "name": item["name"],
            "url": item["url"],
            "description": sections["description"],
            "job_levels": sections["job_levels"],
            "languages": sections["languages"],
            "assessment_length": sections["assessment_length"],
            "duration": sections["duration"],
            "test_type": sections["test_type"],
        })

    os.makedirs("data", exist_ok=True)

    with open("data/shl_catalog_enriched.json", "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=4)

    print("\nEnriched dataset saved to data/shl_catalog_enriched.json")


if __name__ == "__main__":
    enrich_assessments()