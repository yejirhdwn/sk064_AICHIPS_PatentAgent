"""
OriginalityState - Patent Originality Agent 전용 State
"""
from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class OriginalityState(TypedDict, total=False):
    """Patent Originality Agent에서 사용하는 State"""
    
    # Input (from Search Agent)
    tech_name: str
    first_item: Dict[str, Any]
    items: List[Dict[str, Any]]
    
    # Output
    target_patent_id: str
    originality_score: float
    cpc_distribution: Dict[str, int]
    statistics: Dict[str, Any]
    originality_output_path: str
    error: str


__all__ = ["OriginalityState"]