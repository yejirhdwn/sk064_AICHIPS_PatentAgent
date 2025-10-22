from __future__ import annotations

import os
import json
import requests
from typing import Any, Dict, List, Optional, TypedDict
from dotenv import load_dotenv

# Local state models (kept lightweight)
try:
    from state.patent_state import PatentState  # type: ignore
except Exception:
    # Fallback TypedDict if import path resolution varies
    class PatentState(TypedDict, total=False):
        tech_name: str
        num: int
        page: int
        country: str
        language: str
        status: str
        ptype: str
        enrich_first: bool
        enrich_all: bool

        # outputs
        query: str
        serpapi_url: str
        count: int
        items: List[Dict[str, Any]]
        first_item: Dict[str, Any]
        error: str


load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
BASE_URL = "https://serpapi.com/search.json"


def _clamp_num(n: int) -> int:
    return max(10, min(int(n), 100))


def _clamp_page(p: int) -> int:
    return max(1, int(p))


def _prepared_url(params: Dict[str, Any], hide_key: bool = True) -> str:
    from requests import Request
    p = dict(params)
    if hide_key:
        p.pop("api_key", None)
    return Request("GET", BASE_URL, params=p).prepare().url


def _normalize_item(it: Dict[str, Any]) -> Dict[str, Any]:
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


def _fetch_details_abstract_full(patent_id: Optional[str]) -> Optional[str]:
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
        return det.get("abstract") or det.get("description")
    except Exception:
        return None


def _build_query(tech_name: str) -> str:
    tech = (tech_name or "HBM").strip()
    return f'({tech} OR "{tech}") (AI OR accelerator OR processor) 2024'


def patent_search_node(state: PatentState) -> PatentState:
    """LangGraph node: search Google Patents and enrich the first item."""
    if not SERPAPI_KEY:
        out = dict(state)
        out["error"] = "SERPAPI_KEY not set"
        return out  # type: ignore

    tech_name = state.get("tech_name") or "HBM"
    query = _build_query(tech_name)

    params: Dict[str, Any] = {
        "engine": "google_patents",
        "q": query,
        "num": _clamp_num(state.get("num", 10)),
        "page": _clamp_page(state.get("page", 1)),
        "api_key": SERPAPI_KEY,
    }
    if state.get("country"):
        params["country"] = state["country"]
    if state.get("language"):
        params["language"] = state["language"]
    if state.get("status"):
        params["status"] = state["status"]
    if state.get("ptype", "PATENT"):
        params["type"] = state.get("ptype", "PATENT")

    safe_url = _prepared_url(params, hide_key=True)

    try:
        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        out = dict(state)
        out.update({"error": f"SerpAPI request failed: {e}", "serpapi_url": safe_url, "query": query})
        return out  # type: ignore

    data = resp.json()
    items_raw = data.get("organic_results", []) or []
    rows: List[Dict[str, Any]] = [_normalize_item(it) for it in items_raw]

    first_item: Dict[str, Any] = {}
    if rows:
        first_item = dict(rows[0])
        abstract_full = _fetch_details_abstract_full(first_item.get("patent_id"))
        if abstract_full:
            first_item["abstract_full"] = abstract_full

    out: PatentState = dict(state)
    out.update(
        {
            "query": query,
            "serpapi_url": safe_url,
            "count": len(rows),
            "items": rows,
            "first_item": first_item,
        }
    )

    # Persist JSON to /output/patent_search/
    try:
        base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "patent_search")
        os.makedirs(base_dir, exist_ok=True)
        out_path = os.path.join(base_dir, f"{tech_name}_result.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "tech_name": tech_name,
                    "query": out.get("query"),
                    "serpapi_url": out.get("serpapi_url"),
                    "count": out.get("count"),
                    "items": out.get("items", []),
                    "first_item": out.get("first_item", {}),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        out["search_output_path"] = out_path  # type: ignore
    except Exception as e:
        out["error"] = f"Failed to write search JSON: {e}"  # type: ignore

    return out


__all__ = ["patent_search_node", "PatentState"]

