import chromadb
from chromadb.utils import embedding_functions
import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

COLLECTION_NAME = "shl_assessments"

chroma_client = chromadb.PersistentClient(path="./chroma_db")

ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-base-en-v1.5"
)

groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])


def extract_skill_query(query):
    """Extract relevant skill terms from query."""
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
    return " ".join(extracted) if extracted else " ".join(query.split()[:50])


def detect_required_types(query):
    """Detect assessment types needed based on query."""
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

    if any(word in query for word in ["manager", "director", "executive"]):
        required.update(["A", "P", "C"])

    if "consultant" in query:
        required.update(["C", "P", "A"])

    return list(required) if required else ["K"]


def balanced_retrieval(query, target_pool=20):
    """Retrieve and balance assessments by type."""
    focused_query = extract_skill_query(query)
    required_types = detect_required_types(query)

    collection = chroma_client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=ef
    )

    results = collection.query(query_texts=[focused_query], n_results=40)
    metadatas = results["metadatas"][0]

    balanced = []
    for ttype in required_types:
        for meta in metadatas:
            if meta not in balanced and ttype in meta.get("test_type", ""):
                balanced.append(meta)
                break

    for meta in metadatas:
        if len(balanced) >= target_pool:
            break
        if meta not in balanced:
            balanced.append(meta)

    return balanced[:target_pool]


def rerank_with_llm(query, candidates, final_k=10):
    """Rerank candidates using LLM."""
    formatted = "\n\n".join([
        f"URL: {c.get('url', 'N/A')}\n"
        f"Name: {c.get('name', 'N/A')}\n"
        f"Test Type: {c.get('test_type', 'N/A')}\n"
        f"Duration: {c.get('duration', 'N/A')}\n"
        f"Description: {c.get('description', 'N/A')[:250] if c.get('description') else 'N/A'}"
        for c in candidates
    ])

    prompt = f"""You are an expert HR assessment recommendation system.
Given a job description and {len(candidates)} candidate assessments, select the TOP {final_k} most relevant.

Rules:
- Only choose from provided URLs
- Ensure relevance to skills and job level
- Maintain balance if both technical and behavioral skills appear
- Return ONLY a JSON array of URLs in ranked order
- No explanation text

JOB DESCRIPTION:
{query}

CANDIDATE ASSESSMENTS:
{formatted}"""

    completion = groq_client.chat.completions.create(
        model=os.environ["GROQ_MODEL"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    try:
        selected_urls = json.loads(completion.choices[0].message.content.strip())
    except json.JSONDecodeError:
        return candidates[:final_k]

    url_map = {c.get("url", ""): c for c in candidates if c.get("url")}
    cleaned_urls = []
    for item in selected_urls:
        if isinstance(item, dict):
            url = item.get("url")
        else:
            url = item

    if isinstance(url, str):
        cleaned_urls.append(url.strip())
    reranked = [url_map[url] for url in selected_urls if url in url_map]

    for c in candidates:
        if c not in reranked and len(reranked) < final_k:
            reranked.append(c)

    return reranked[:final_k]


def recommend(query, n_results=10):
    """Generate final assessment recommendations."""
    candidate_pool = balanced_retrieval(query, target_pool=20)
    final_results = rerank_with_llm(query, candidate_pool, final_k=n_results)
    return {"metadatas": [final_results]}
