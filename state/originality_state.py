from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class OriginalityState(TypedDict, total=False):
    # inputs from previous node
    tech_name: str
    first_item: Dict[str, Any]
    items: List[Dict[str, Any]]

    # outputs
    target_patent_id: str
    originality_score: float
    cpc_distribution: Dict[str, int]
    statistics: Dict[str, Any]
    originality_output_path: str
    error: str