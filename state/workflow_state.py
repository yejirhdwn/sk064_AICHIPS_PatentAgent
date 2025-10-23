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
    top_items: List[Dict[str, Any]]
    
    # ========== Originality Agent Fields ==========
    target_patent_id: str
    originality_score: float
    cpc_distribution: Dict[str, int]
    statistics: Dict[str, Any]
    originality_output_path: str
    
    # ========== Market Evaluation Agent Fields ==========
    market_size_score: float
    growth_potential_score: float
    commercialization_readiness: float
    market_score: float
    application_domains: List[str]
    commercialization_potential: str
    market_rationale: str
    demand_signals: List[str]
    keyterms: List[str]
    retrieved_docs: List[Any]
    web_search_results: List[Dict[str, Any]]
    sources: List[str]
    market_output_path: str
    
    # ========== Suitability Score Agent Fields =========
    calculated_score: float
    calculated_grade: str
    suitability_score: float
    suitability_grade: str
    final_grade: str
    score_breakdown: Dict[str, float]
    llm_evaluation: Dict[str, Any]
    evaluation_summary: str
    suitability_output_path: str
    
    # ========== Report Agent Fields ==========
    all_patent_results: List[Dict[str, Any]]
    report_html_path: str
    report_json_path: str
    report_title: str
    report_generated_at: str
    industry_context: str
    policy_context: str
    korea_position_context: str
    rag_sources: List[str]
    total_patents_analyzed: int
    avg_originality_score: float
    avg_market_score: float
    grade_distribution: Dict[str, int]


__all__ = ["WorkflowState"]