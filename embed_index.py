
import json
import chromadb
from chromadb.utils import embedding_functions

# Configuration

COLLECTION_NAME = "shl_assessments"
CHROMA_PATH = "./chroma_db"
DATA_PATH = "data/shl_catalog_enriched.json"

ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-base-en-v1.5"
)

# Test Type Mapping

TEST_TYPE_MAP = {
    "A": "Ability and Aptitude",
    "B": "Biodata and Situational Judgement",
    "C": "Competencies",
    "D": "Development and 360",
    "E": "Assessment Exercises",
    "K": "Knowledge and Skills",
    "P": "Personality and Behavior",
    "S": "Simulations"
}


# Create Embedding Text

def create_embedding_text(item):
    test_types = item.get("test_type", [])
    expanded_types = [TEST_TYPE_MAP.get(t, "") for t in test_types]

    return f"""
Assessment Name:
{item.get('name', '')}

Description:
{item.get('description', '')}

This assessment evaluates:
{', '.join(expanded_types)}

Job levels:
{item.get('job_levels', '')}

Languages:
{item.get('languages', '')}

Duration:
{item.get('duration', '')} minutes.
""".lower()

# Ingest

def ingest():

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Check if collection already exists
    try:
        collection = chroma_client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=ef
        )
        print("Collection already exists. Skipping ingestion.")
        return
    except:
        print("Collection not found. Creating new collection...")

    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef
    )

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    ids = []
    documents = []
    metadatas = []

    total = len(data)
    print(f"\nStarting ingestion of {total} assessments...\n")

    for i, item in enumerate(data, 1):

        print(f"[{i}/{total}] Embedding: {item['name']}")

        doc_id = item["url"].strip().lower()
        embedding_text = create_embedding_text(item)

        test_type_list = item.get("test_type") or []
        test_type_string = ",".join(test_type_list)

        duration = item.get("duration")
        duration = int(duration) if isinstance(duration, int) else -1

        metadatas.append({
            "name": str(item.get("name") or ""),
            "url": doc_id,
            "test_type": test_type_string,
            "duration": duration,
            "job_levels": str(item.get("job_levels") or ""),
            "languages": str(item.get("languages") or ""),
            "description": str(item.get("description") or "")
        })

        ids.append(doc_id)
        documents.append(embedding_text)

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    print(f"\nSuccessfully added {len(ids)} assessments to Chroma.")


if __name__ == "__main__":
    ingest()