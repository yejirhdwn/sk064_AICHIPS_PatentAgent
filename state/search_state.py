"""
SearchState - Patent Search Agent 전용 State
"""
from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class SearchState(TypedDict, total=False):
    """Patent Search Agent에서 사용하는 State"""
    
    # Input Parameters
    tech_name: str
    num: int
    page: int
    country: str
    language: str
    status: str
    ptype: str
    enrich_first: bool
    enrich_all: bool
    
    # Output
    query: str
    serpapi_url: str
    count: int
    items: List[Dict[str, Any]]
    first_item: Dict[str, Any]
    search_output_path: str
    error: str


# Alias for backward compatibility
PatentState = SearchState


__all__ = ["SearchState", "PatentState"]