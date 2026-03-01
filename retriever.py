import chromadb
from chromadb.utils import embedding_functions
import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

COLLECTION_NAME = "shl_assessments"

# Chroma + Embedding Setup

chroma_client = chromadb.PersistentClient(path="./chroma_db")

ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Extract Skill Query

def extract_skill_query(query: str) -> str:
    query = query.lower()

    skill_terms = [
        "java", "javascript", "python", "sql", "excel",
        "selenium", "manual testing", "testing",
        "html", "css", "automation", "developer",
        "data", "analysis", "analyst",
        "sales", "marketing", "communication",
        "personality", "leadership", "collaboration",
        "team", "stakeholder", "cultural fit",
        "people management",
        "cognitive", "reasoning", "aptitude",
        "numerical", "verbal",
        "graduate", "entry level",
        "bank", "admin",
        "manager", "director", "executive",
        "consultant", "professional"
    ]

    extracted = [term for term in skill_terms if term in query]

    if extracted:
        return " ".join(extracted)

    # fallback for long JDs
    return " ".join(query.split()[:50])

# Detect Required Test Types

def detect_required_types(query: str):
    query = query.lower()

    type_map = {
        "K": ["java", "python", "sql", "developer", "technical",
              "coding", "data", "excel", "marketing", "bank", "admin"],
        "P": ["personality", "cultural", "collaboration",
              "leadership", "team", "stakeholder", "fit"],
        "A": ["cognitive", "reasoning", "aptitude",
              "numerical", "verbal"],
        "B": ["situational", "judgement"],
        "S": ["simulation", "role play"],
        "D": ["development", "360"],
        "C": ["manager", "competency", "professional", "consultant"],
        "E": ["assessment center", "exercise", "executive", "scenario"]
    }

    required = set()

    for ttype, keywords in type_map.items():
        if any(word in query for word in keywords):
            required.add(ttype)

    # Role-based adjustments
    if any(word in query for word in ["manager", "director", "executive"]):
        required.update(["A", "P", "C"])

    if "consultant" in query:
        required.update(["C", "P", "A"])

    return list(required) if required else ["K"]

# Balanced Retrieval

def balanced_retrieval(query: str, target_pool: int = 20):

    focused_query = extract_skill_query(query)
    required_types = detect_required_types(query)

    collection = chroma_client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=ef
    )

    results = collection.query(
        query_texts=[focused_query],
        n_results=40
    )

    metadatas = results["metadatas"][0]

    balanced = []

    # Ensure coverage of required types
    for ttype in required_types:
        for meta in metadatas:
            if meta not in balanced and ttype in meta.get("test_type", ""):
                balanced.append(meta)
                break

    # Fill remaining semantically
    for meta in metadatas:
        if len(balanced) >= target_pool:
            break
        if meta not in balanced:
            balanced.append(meta)

    return balanced[:target_pool]

# LLM Reranking

def rerank_with_llm(query: str, candidates: list, final_k: int = 10):

    formatted_candidates = "\n\n".join([
        f"URL: {c.get('url')}\n"
        f"Name: {c.get('name')}\n"
        f"Test Type: {c.get('test_type')}\n"
        f"Duration: {c.get('duration')}\n"
        f"Description: {(c.get('description') or '')[:250]}"
        for c in candidates
    ])

    prompt = f"""
You are an expert HR assessment recommendation system.

Select the TOP {final_k} most relevant assessments from the list.

Rules:
- Only choose from provided URLs
- Ensure skill and job level relevance
- Maintain balance between technical and behavioral tests if applicable
- Return ONLY a JSON array of URLs (no explanation)

JOB DESCRIPTION:
{query}

CANDIDATE ASSESSMENTS:
{formatted_candidates}
"""

    try:
        completion = groq_client.chat.completions.create(
            model=os.environ.get("GROQ_MODEL"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        response_text = completion.choices[0].message.content.strip()
        selected = json.loads(response_text)

    except Exception:
        # Safe fallback
        return candidates[:final_k]

    #  Normalize LLM output safely
    cleaned_urls = []

    for item in selected:
        if isinstance(item, dict):
            url = item.get("url")
            if isinstance(url, str):
                cleaned_urls.append(url.strip())
        elif isinstance(item, str):
            cleaned_urls.append(item.strip())

    url_map = {c.get("url"): c for c in candidates if c.get("url")}

    reranked = []
    for url in cleaned_urls:
        if url in url_map:
            reranked.append(url_map[url])

    # Fill if LLM returns fewer than needed
    for c in candidates:
        if c not in reranked and len(reranked) < final_k:
            reranked.append(c)

    return reranked[:final_k]


# Public Recommend Function

def recommend(query: str, n_results: int = 10):

    candidate_pool = balanced_retrieval(query, target_pool=20)
    final_results = rerank_with_llm(query, candidate_pool, final_k=n_results)

    return {"metadatas": [final_results]}