import os
import json
import re
from google import genai
from opensearchpy import OpenSearch
from dotenv import load_dotenv

# 1. Setup
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", 9200))
INDEX_NAME = "resume-index-v2"

client = genai.Client(api_key=GEMINI_API_KEY)
os_client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False
)

# --- HELPER: Fixes "Markdown JSON" errors ---
def clean_json(text):
    """
    Strips ```json ... ``` markdown formatting if Gemini adds it.
    """
    text = text.strip()
    if text.startswith("```"):
        # Remove first line (```json) and last line (```)
        text = re.sub(r"^```\w*\n", "", text)
        text = re.sub(r"\n```$", "", text)
    return json.loads(text)

def get_embedding(text):
    try:
        result = client.models.embed_content(
            model="models/text-embedding-004",
            contents=text
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"Embedding error: {e}")
        return []

def extract_jd_criteria(jd_text):
    prompt = f"""
    You are an expert Technical Recruiter. Analyze this Job Description.
    JOB DESCRIPTION: {jd_text[:15000]}
    
    Output purely JSON with this structure:
    {{
        "job_title": "string",
        "must_have_skills": ["skill1", "skill2"],
        "nice_to_have_skills": ["skill3"],
        "min_years_experience": int,
        "domain_keywords": ["finance", "cloud", "etc"]
    }}
    """
    try:
        response = client.models.generate_content(
            model="gemini-robotics-er-1.5-preview",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return clean_json(response.text) # <--- USING CLEAN_JSON
    except Exception as e:
        print(f"Error extracting criteria: {e}")
        return {}

def search_candidates(criteria, top_k=50):
    semantic_string = f"{criteria.get('job_title', '')} {' '.join(criteria.get('must_have_skills', []))} {' '.join(criteria.get('domain_keywords', []))}"
    query_vector = get_embedding(semantic_string)

    if not query_vector: return []

    # 1. Fetch 3x more candidates than needed (to account for duplicates/chunks)
    query_body = {
        "size": top_k * 3,
        "query": {
            "hybrid": {
                "queries": [
                    {"knn": {"embedding": {"vector": query_vector, "k": top_k}}},
                    {"bool": {"should": [{"match": {"text": {"query": skill, "boost": 2.0}}} for skill in criteria.get('must_have_skills', [])]}}
                ]
            }
        }
    }
    
    raw_hits = os_client.search(index=INDEX_NAME, body=query_body)['hits']['hits']
    
    # --- 2. Deduplication Logic ---
    seen_filenames = set()
    unique_results = []
    
    for hit in raw_hits:
        filename = hit['_source']['filename']
        
        # Only add the candidate if we haven't seen this filename before
        # This keeps the highest-scored chunk and ignores the rest
        if filename not in seen_filenames:
            unique_results.append(hit)
            seen_filenames.add(filename)
    
    # 3. Return only the top unique candidates up to the requested limit
    return unique_results[:top_k]

def analyze_candidate(resume_text, criteria, blind_mode=False):
    prompt = f"""
    Evaluate candidate. 
    CRITERIA: {json.dumps(criteria)}
    RESUME: {resume_text[:12000]}
    BLIND_MODE: {blind_mode}
    
    Tasks:
    1. Fit Score (0-100).
    2. Seniority (Junior/Mid/Senior).
    3. 2 Strengths, 2 Weaknesses.
    4. 2 Interview Questions.
    5. If BLIND_MODE is True, redact names/PII.
    
    Output JSON:
    {{
        "candidate_name": "Name",
        "fit_score": int,
        "seniority_level": "string",
        "strengths": ["s1"],
        "weaknesses": ["w1"],
        "interview_questions": ["q1"],
        "rejection_reason": "string"
    }}
    """
    try:
        response = client.models.generate_content(
            model="gemini-robotics-er-1.5-preview",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return clean_json(response.text) # <--- USING CLEAN_JSON
    except Exception as e:
        return {"candidate_name": "Error", "fit_score": 0, "strengths": [], "weaknesses": []}

def compare_candidates_side_by_side(candidates_data, criteria):
    prompt = f"""
    Compare Candidate A and Candidate B for role: {criteria.get('job_title')}.
    
    Candidate A: {json.dumps(candidates_data[0])}
    Candidate B: {json.dumps(candidates_data[1])}
    
    Output JSON:
    {{
        "rows": [
            {{"feature": "Years Experience", "cand_a": "val", "cand_b": "val"}},
            {{"feature": "Technical Skills", "cand_a": "val", "cand_b": "val"}},
            {{"feature": "Cultural Fit", "cand_a": "val", "cand_b": "val"}},
            {{"feature": "Verdict", "cand_a": "short verdict", "cand_b": "short verdict"}}
        ]
    }}
    """
    try:
        response = client.models.generate_content(
            model="gemini-robotics-er-1.5-preview", 
            contents=prompt, 
            config={'response_mime_type': 'application/json'}
        )
        return clean_json(response.text) # <--- USING CLEAN_JSON
    except Exception as e:
        print(f"Compare Error: {e}")
        return {"rows": []}

def generate_rejection_email(candidate_name, reason):
    prompt = f"Write a polite rejection email for {candidate_name}. Reason: {reason}. Max 100 words."
    response = client.models.generate_content(model="gemini-robotics-er-1.5-preview", contents=prompt)
    return response.text