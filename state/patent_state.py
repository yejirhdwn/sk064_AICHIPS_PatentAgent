from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class PatentState(TypedDict, total=False):
    # inputs
    tech_name: str
    num: int
    page: int
    country: str
    language: str
    status: str
    ptype: str
    enrich_first: bool
    enrich_all: bool

    # outputs from search
    query: str
    serpapi_url: str
    count: int
    items: List[Dict[str, Any]]
    first_item: Dict[str, Any]
    search_output_path: str
    error: str