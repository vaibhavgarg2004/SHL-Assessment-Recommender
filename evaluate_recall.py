import pandas as pd
from retriever import recommend

TRAIN_DATA_PATH = "DATA/Gen_AI Dataset.xlsx"

# Normalize URLs
def normalize_url(url):
    if not isinstance(url, str):
        return ""

    url = url.strip().lower()
    url = url.replace("/solutions", "")
    url = url.rstrip("/")

    return url

# Recall@K

def recall_at_k(predicted_urls, relevant_urls, k=10):
    predicted_top_k = [normalize_url(u) for u in predicted_urls[:k]]
    relevant_set = set(normalize_url(u) for u in relevant_urls)

    retrieved_relevant = [
        url for url in predicted_top_k if url in relevant_set
    ]

    if len(relevant_set) == 0:
        return 0.0, []

    recall = len(retrieved_relevant) / len(relevant_set)

    return recall, retrieved_relevant

# Evaluation with Debug Prints

def evaluate_mean_recall(k=10):

    df = pd.read_excel(TRAIN_DATA_PATH)
    df.columns = df.columns.str.strip()

    grouped = (
        df.groupby("Query")["Assessment_url"]
        .apply(list)
        .reset_index()
    )

    recalls = []

    for i, row in grouped.iterrows():
        query = row["Query"]
        relevant_urls = row["Assessment_url"]

        results = recommend(query, n_results=k)

        predicted_urls = [
            meta.get("url", "")
            for meta in results["metadatas"][0]
        ]

        recall, _ = recall_at_k(predicted_urls, relevant_urls, k)
        recalls.append(recall)

        print(f"Query {i+1} Recall@{k} = {recall:.4f}")

    mean_recall = sum(recalls) / len(recalls)

    print("\n=================================")
    print(f"Mean Recall@{k} = {mean_recall:.4f}")
    print("=================================")

    return mean_recall


if __name__ == "__main__":
    evaluate_mean_recall(k=10)