import pandas as pd
from retriever import recommend

# CONFIG

INPUT_FILE = "DATA/Gen_AI Dataset.xlsx"
SHEET_NAME = "Test-Set"
OUTPUT_FILE = "submission.csv"

TOP_K = 10  # Max 10 as per assignment
MIN_K = 5   # Minimum 5 required

# GENERATE CSV

def generate_csv():

    # Read Excel
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)
    df.columns = df.columns.str.strip()

    if "Query" not in df.columns:
        raise ValueError("Column 'Query' not found in the sheet.")

    queries = df["Query"].dropna().unique()

    rows = []

    for idx, query in enumerate(queries, 1):

        print(f"Processing Query {idx}/{len(queries)}")

        try:
            results = recommend(query, n_results=TOP_K)

            if not results or "metadatas" not in results:
                print(f"Skipping Query {idx} (no results returned)")
                continue

            predicted_urls = [
                meta.get("url")
                for meta in results["metadatas"][0]
                if meta.get("url")
            ]

            # Remove duplicates while preserving order
            predicted_urls = list(dict.fromkeys(predicted_urls))

            # Enforce limits
            predicted_urls = predicted_urls[:TOP_K]

            if len(predicted_urls) < MIN_K:
                print(f" Query {idx} returned less than {MIN_K} results")

            for url in predicted_urls:
                rows.append({
                    "Query": query,
                    "Assessment_url": url
                })

        except Exception as e:
            print(f" Error processing Query {idx}: {e}")
            continue

    # Create final DataFrame
    submission_df = pd.DataFrame(rows)

    # Save CSV (exact required format)
    submission_df.to_csv(OUTPUT_FILE, index=False)

    print("\n submission.csv generated successfully.")


if __name__ == "__main__":
    generate_csv()