# =========================================================
# Patent_Scrapper_agent.py
# =========================================================

import os
import json
import requests
from dotenv import load_dotenv

# ---------- 환경 변수 ----------
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
BASE_URL = "https://serpapi.com/search.json"


# ---------- 유틸 ----------
def clamp_num(n: int) -> int:
    """SerpAPI google_patents: num은 10~100 범위"""
    return max(10, min(int(n), 100))

def clamp_page(p: int) -> int:
    """현재 엔진은 page를 1부터 요구"""
    return max(1, int(p))

def prepared_url(params):
    """요청 URL 디버깅용"""
    from requests import Request
    return Request("GET", BASE_URL, params=params).prepare().url

def normalize_item(it):
    """organic_results를 표준 필드로 변환"""
    return {
        "title": it.get("title"),
        "abstract": it.get("snippet"),
        "patent_id": it.get("patent_id"),
        "publication_number": it.get("publication_number"),
        "publication_date": it.get("publication_date"),
        "filing_date": it.get("filing_date"),
        "priority_date": it.get("priority_date"),
        "assignee": it.get("assignee"),
        "inventor": it.get("inventor"),
        "link": it.get("patent_link"),
        "pdf": it.get("pdf"),
    }


# ---------- 메인 함수 ----------
def search_google_patents(
    query: str,
    num: int = 10,
    page: int = 1,
    country: str | None = None,
    language: str | None = None,
    status: str | None = None,
    ptype: str | None = "PATENT",
):
    """Google Patents에서 특허 검색"""
    if not SERPAPI_KEY:
        return {"error": "SERPAPI_KEY not set."}

    params = {
        "engine": "google_patents",
        "q": query,
        "num": clamp_num(num),
        "page": clamp_page(page),
        "api_key": SERPAPI_KEY,
    }
    if country:  params["country"]  = country
    if language: params["language"] = language
    if status:   params["status"]   = status
    if ptype:    params["type"]     = ptype

    url = prepared_url(params)
    r = requests.get(BASE_URL, params=params, timeout=30)
    if r.status_code != 200:
        return {"error": f"SerpAPI {r.status_code}: {r.text}", "serpapi_url": url}

    data = r.json()
    items = data.get("organic_results", [])
    if not items:
        return {"error": "No patents found.", "serpapi_url": url}

    rows = [normalize_item(it) for it in items]
    return {
        "query": query,
        "serpapi_url": url,
        "count": len(rows),
        "items": rows,
        "first_item": rows[0] if rows else {},
    }


# ---------- 실행 ----------
if __name__ == "__main__":
    query = '(HBM OR "High Bandwidth Memory") (AI OR accelerator OR processor) 2024'
    num = 10
    page = 1
    country = "US,WO,KR,JP,EP"
    language = "ENGLISH,KOREAN"
    status = None
    ptype = "PATENT"

    print(f"🔍 Searching Google Patents for: {query}")

    result = search_google_patents(
        query=query,
        num=num,
        page=page,
        country=country,
        language=language,
        status=status,
        ptype=ptype,
    )

    if result.get("error"):
        print("❌ Error:", result["error"])
        if result.get("serpapi_url"):
            print("Request URL:", result["serpapi_url"])
        raise SystemExit(1)

    print("✅ Found:", result["count"], "patents")
    print("Request URL:", result["serpapi_url"])

    # 결과 저장
    out_path = "hbm_search_output.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n📁 Saved results to: {out_path}")
    print("\n===== [Top Result] =====")
    print(json.dumps(result["first_item"], ensure_ascii=False, indent=2))
