"""
WorkflowState - 전체 워크플로우에서 사용하는 통합 State
"""
from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class WorkflowState(TypedDict, total=False):
    """
    전체 워크플로우 통합 State
    모든 Agent의 Input/Output 필드를 포함
    """
    
    # ========== Common Fields ==========
    tech_name: str
    error: str
    
    # ========== Search Agent Fields ==========
    num: int
    page: int
    country: str
    language: str
    status: str
    ptype: str
    enrich_first: bool
    enrich_all: bool
    query: str
    serpapi_url: str
    count: int
    items: List[Dict[str, Any]]
    first_item: Dict[str, Any]
    search_output_path: str
    
    # ========== Originality Agent Fields ==========
    target_patent_id: str
    originality_score: float
    cpc_distribution: Dict[str, int]
    statistics: Dict[str, Any]
    originality_output_path: str
    
    # ========== Market Evaluation Agent Fields ==========
    market_score: float                   # 시장성 점수 (0.0-1.0, 정규화)
    market_size: str                      # 시장 규모 (Large/Medium/Small)
    growth_potential: str                 # 성장 가능성 (High/Medium/Low)
    market_rationale: str                 # 평가 근거 (한글)
    market_output_path: str               # 시장성 평가 결과 파일 경로


__all__ = ["WorkflowState"]