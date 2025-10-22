"""MarketState - 시장성 평가 Agent용 State 정의"""
from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class MarketState(TypedDict, total=False):
    # Common
    tech_name: str
    error: str

    # Inputs (from previous nodes)
    target_patent_id: str              # 평가 대상 특허 ID (없으면 first_item.patent_id 사용)
    first_item: Dict[str, Any]         # patent_search_agent 출력의 첫 결과(제목/초록 포함)

    # Optional search context (not strictly required but helpful)
    query: str
    items: List[Dict[str, Any]]

    # Outputs (produced by market_size_growth_node / agent)
    market_score: float                # 0.0-1.0 정규화 점수
    market_size: str                   # Large/Medium/Small
    growth_potential: str              # High/Medium/Low
    market_rationale: str              # 한글 근거 요약
    market_output_path: str            # 결과 JSON 저장 경로


__all__ = ["MarketState"]
