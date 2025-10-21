# =========================================================
# patent_scraper_agent.py  (LangGraph node-ready)
# =========================================================
# (1) 풀초록(abstract_full) 보강
# - 목록 조회(google_patents) 뒤, 첫 1건 또는 상위 N건에 대해
#   google_patents_details 엔드포인트로 "풀 초록(abstract_full)"을 추가 조회합니다.
#   · 이 상세 조회는 SerpAPI 크레딧이 항목당 1회 추가 소모됩니다.
#   · 기본값: 첫 1건만 보강(enrich_first=True), 모두 보강하려면 enrich_all=True.
#
# (2) 유저 입력(기술명) 반영 계획
# - LangGraph 상태로 tech_name을 받아 쿼리를 구성하도록 설계했습니다.
# - 현재는 예시 용도로 기본값 "HBM"을 사용합니다(사용자가 입력하지 않아도 동작).
# - 추후 UI/CLI/에이전트 프롬프트에서 tech_name을 받아 state로 전달하면 됩니다.
#   예) app.invoke({"tech_name": "Processing-In-Memory"})
# =========================================================

from __future__ import annotations

import os
import json
import requests
from dotenv import load_dotenv
from typing import Dict, Any, List, TypedDict, Optional

# ---------- 환경 변수 ----------
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
BASE_URL = "https://serpapi.com/search.json"

# ---------- LangGraph용 State ----------
class PatentState(TypedDict, total=False):
    # 입력
    tech_name: str                 # 사용자가 입력할 기술 키워드(예: "HBM"). 미지정 시 "HBM".
    num: int                       # 조회 개수(10~100), 기본 10
    page: int                      # 페이지(>=1), 기본 1
    country: str                   # "US,WO,KR,JP,EP" 형태
    language: str                  # "ENGLISH,KOREAN" 등
    status: str                    # 공개/거절 등 상태 필터(옵션)
    ptype: str                     # "PATENT" | "DESIGN" 등. 기본 "PATENT"
    enrich_first: bool             # 첫 1건 보강(기본 True)
    enrich_all: bool               # 상위 N건 모두 보강(기본 False)

    # 출력
    query: str
    serpapi_url: str
    count: int
    items: List[Dict[str, Any]]
    first_item: Dict[str, Any]
    error: str

# ---------- 유틸 ----------
def clamp_num(n: int) -> int:
    """SerpAPI google_patents: num은 10~100 범위"""
    return max(10, min(int(n), 100))

def clamp_page(p: int) -> int:
    """현재 엔진은 page를 1부터 요구"""
    return max(1, int(p))

def prepared_url(params: Dict[str, Any], hide_key: bool = True) -> str:
    """
    요청 URL 생성(디버깅/저장용).
    - hide_key=True: api_key 파라미터를 URL에서 제거(보안 목적)합니다.
    """
    from requests import Request
    params_no_key = dict(params)
    if hide_key:
        params_no_key.pop("api_key", None)
    return Request("GET", BASE_URL, params=params_no_key).prepare().url

def normalize_item(it: Dict[str, Any]) -> Dict[str, Any]:
    """organic_results를 표준 필드로 변환 (목록의 snippet은 짧은 미리보기)"""
    return {
        "title": it.get("title"),
        "abstract": it.get("snippet"),  # 짧은 요약(미리보기). 풀초록은 details 보강에서 추가.
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

def fetch_details_abstract_full(patent_id: Optional[str]) -> Optional[str]:
    """
    google_patents_details로 풀 초록을 조회합니다.
    ⚠️ 참고: 상세 조회 1건당 SerpAPI 크레딧 1회 추가 소모.
    """
    if not SERPAPI_KEY or not patent_id:
        return None
    try:
        r = requests.get(
            BASE_URL,
            params={
                "engine": "google_patents_details",
                "patent_id": patent_id,
                "api_key": SERPAPI_KEY,
            },
            timeout=30,
        )
        r.raise_for_status()
        det = r.json()
        # 엔드포인트마다 풀 텍스트가 'abstract' 또는 'description' 중 하나로 제공될 수 있음
        return det.get("abstract") or det.get("description")
    except Exception:
        return None

# ---------- 쿼리 빌더 ----------
DEFAULT_QUERY_TEMPLATE = '({tech} OR "{tech_expanded}") (AI OR accelerator OR processor) 2024'

def build_query(tech_name: str) -> str:
    """
    간단한 쿼리 템플릿:
    - 기술명이 공백/하이픈 포함일 수 있어, 큰따옴표 버전도 함께 사용
    - 필요 시 템플릿을 교체/확장하면 됨
    """
    tech = tech_name.strip()
    return DEFAULT_QUERY_TEMPLATE.format(tech=tech, tech_expanded=tech)

# ---------- 메인 검색 ----------
def search_google_patents(
    query: str,
    num: int = 10,
    page: int = 1,
    country: Optional[str] = None,
    language: Optional[str] = None,
    status: Optional[str] = None,
    ptype: Optional[str] = "PATENT",
    enrich_first: bool = True,   # ✅ 첫 1건만 풀 초록 보강 (기본 True)
    enrich_all: bool = False,    # ⚠️ 상위 N개 모두 보강 (N회 추가 크레딧) - 기본 False
) -> Dict[str, Any]:
    """Google Patents에서 특허 검색 + (선택) 풀초록 보강"""
    if not SERPAPI_KEY:
        return {"error": "SERPAPI_KEY not set."}

    params: Dict[str, Any] = {
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

    # 디버깅/저장용 URL은 KEY 제거본 사용
    safe_url = prepared_url(params, hide_key=True)

    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"SerpAPI request failed: {e}", "serpapi_url": safe_url}

    data = r.json()
    items = data.get("organic_results", [])
    if not items:
        return {"error": "No patents found.", "serpapi_url": safe_url}

    rows: List[Dict[str, Any]] = [normalize_item(it) for it in items]

    # --- (선택) 풀초록 보강 ---
    if enrich_all:
        for row in rows:
            abs_full = fetch_details_abstract_full(row.get("patent_id"))
            if abs_full:
                row["abstract_full"] = abs_full
    elif enrich_first and rows:
        # 첫 1건만 보강 → 추가 1회 크레딧
        abs_full = fetch_details_abstract_full(rows[0].get("patent_id"))
        if abs_full:
            rows[0]["abstract_full"] = abs_full

    return {
        "query": query,
        "serpapi_url": safe_url,
        "count": len(rows),
        "items": rows,
        "first_item": rows[0] if rows else {},
    }

# ---------- LangGraph 노드 ----------
def patent_search_node(state: PatentState) -> PatentState:
    """
    LangGraph 노드로 사용:
    - 입력: state["tech_name"] (옵션, 기본 "HBM")
            + 필요한 경우 num/page/country/language/status/ptype/enrich_* 등
    - 출력: query, serpapi_url, count, items, first_item, error 등을 state에 병합
    """
    tech_name = state.get("tech_name") or "HBM"  # ✅ 현재는 예시: HBM 기본값
    query = build_query(tech_name)

    result = search_google_patents(
        query=query,
        num=state.get("num", 10),
        page=state.get("page", 1),
        country=state.get("country"),
        language=state.get("language"),
        status=state.get("status"),
        ptype=state.get("ptype", "PATENT"),
        enrich_first=state.get("enrich_first", True),
        enrich_all=state.get("enrich_all", False),
    )

    # 기존 state를 보존하면서 검색 결과 병합
    new_state: PatentState = dict(state)
    new_state.update(result)
    return new_state

# ---------- (선택) 간단 실행 ----------
if __name__ == "__main__":
    # 예시: 현재는 유저 입력 없이 HBM 기본값으로 동작
    init_state: PatentState = {
        "tech_name": "HBM",                     # ← 추후 UI/프롬프트 입력으로 대체
        "num": 10,
        "page": 1,
        "country": "US,WO,KR,JP,EP",
        "language": "ENGLISH,KOREAN",
        "ptype": "PATENT",
        "enrich_first": True,                   # 첫 1건만 보강(추가 1크레딧)
        "enrich_all": False,                    # 상위 N건 모두 보강 시 True
    }

    print(f"🔍 Searching Google Patents (tech): {init_state['tech_name']}")
    out_state = patent_search_node(init_state)

    if out_state.get("error"):
        print("❌ Error:", out_state["error"])
        if out_state.get("serpapi_url"):
            print("Request URL:", out_state["serpapi_url"])
        raise SystemExit(1)

    print("✅ Found:", out_state["count"], "patents")
    print("Request URL (safe):", out_state["serpapi_url"])

    # 결과 저장
    out_path = "hbm_search_output.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "query": out_state.get("query"),
                "serpapi_url": out_state.get("serpapi_url"),
                "count": out_state.get("count"),
                "items": out_state.get("items"),
                "first_item": out_state.get("first_item"),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\n📁 Saved results to: {out_path}")
    print("\n===== [Top Result] =====")
    print(json.dumps(out_state.get("first_item", {}), ensure_ascii=False, indent=2))

"""
# ── LangGraph 연결 예시 ─────────────────────────────────────────
from langgraph.graph import StateGraph, END

graph = StateGraph(PatentState)
graph.add_node("PatentSearch", patent_search_node)
graph.set_entry_point("PatentSearch")
graph.add_edge("PatentSearch", END)

app = graph.compile()

# 유저 입력: tech_name만 전달(나머지는 기본값)
result_state = app.invoke({"tech_name": "Processing-In-Memory"})
print(result_state["first_item"])
# ───────────────────────────────────────────────────────────────
"""
