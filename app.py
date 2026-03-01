import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

# SQLite patch (important for deployment)
try:
    import pysqlite3
    sys.modules["sqlite3"] = sys.modules["pysqlite3"]
except ImportError:
    pass

# Load environment variables
load_dotenv()

from retriever import recommend

# TEST TYPE MAPPING (Code → Full Name)

TEST_TYPE_MAP = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competencies",
    "D": "Development & 360",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills",
    "P": "Personality & Behaviour",
    "S": "Simulations"
}


# FASTAPI INIT

app = FastAPI(
    title="SHL Assessment Recommendation API",
    version="1.0"
)

# REQUEST MODEL

class RecommendRequest(BaseModel):
    query: str


# HEALTH ENDPOINT

@app.get("/health")
def health():
    return {"status": "healthy"}

# RECOMMEND ENDPOINT

@app.post("/recommend")
def recommend_assessments(request: RecommendRequest):

    query = request.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        results = recommend(query, n_results=10)

        recommended = []

        for meta in results["metadatas"][0]:

            # Convert Test Type Codes
            raw_types = meta.get("test_type", "")

            if isinstance(raw_types, str):
                codes = [t.strip() for t in raw_types.split(",") if t.strip()]
            elif isinstance(raw_types, list):
                codes = raw_types
            else:
                codes = []

            readable_types = [
                TEST_TYPE_MAP.get(code, code)
                for code in codes
            ]

            # Normalize Yes/No Fields

            adaptive_support = meta.get("adaptive_support", "No")
            adaptive_support = "Yes" if str(adaptive_support).lower() in ["yes", "true", "1"] else "No"

            remote_support = meta.get("remote_support", "Yes")
            remote_support = "Yes" if str(remote_support).lower() in ["yes", "true", "1"] else "No"

            duration = meta.get("duration")

            if duration == -1 or duration is None:
                duration = None

            recommended.append({
                "url": meta.get("url", ""),
                "name": meta.get("name", ""),
                "adaptive_support": adaptive_support,
                "description": meta.get("description", ""),
                "duration": duration,
                "remote_support": remote_support,
                "test_type": readable_types
            })

        return {
            "recommended_assessments": recommended
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))