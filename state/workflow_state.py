"""
WorkflowState - 전체 워크플로우에서 사용하는 통합 State
v3.0: 정량적 시장성 평가 및 Tavily 웹 검색 통합
"""
from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class WorkflowState(TypedDict, total=False):
    """
    전체 워크플로우 통합 State
    모든 Agent의 Input/Output 필드를 포함
    """
    
    # ========== Common Fields ==========
    tech_name: str                        # 기술 키워드 (예: "NPU", "AI accelerator")
    error: str                            # 에러 메시지
    
    # ========== Search Agent Fields ==========
    num: int                              # 검색 결과 개수
    page: int                             # 페이지 번호
    country: str                          # 국가 코드
    language: str                         # 언어 코드
    status: str                           # 특허 상태
    ptype: str                            # 특허 타입
    enrich_first: bool                    # 첫 번째 결과 상세 정보 추가
    enrich_all: bool                      # 모든 결과 상세 정보 추가
    query: str                            # 검색 쿼리
    serpapi_url: str                      # SerpAPI URL
    count: int                            # 검색 결과 총 개수
    items: List[Dict[str, Any]]           # 검색 결과 리스트
    first_item: Dict[str, Any]            # 첫 번째 특허 정보
    search_output_path: str               # 검색 결과 저장 경로
    
    # ========== Originality Agent Fields ==========
    target_patent_id: str                 # 평가 대상 특허 ID
    originality_score: float              # 독창성 점수 (0.0-1.0)
    cpc_distribution: Dict[str, int]      # CPC 분포
    statistics: Dict[str, Any]            # 통계 정보
    originality_output_path: str          # 독창성 평가 결과 저장 경로
    
    # ========== Market Evaluation Agent Fields (v3.0) ==========
    # 정량적 점수 (세부)
    market_size_score: float              # 시장 규모 점수 (0.0-0.4) - SAM 기반
    growth_potential_score: float         # 성장 잠재력 점수 (0.0-0.3) - CAGR/구체적 수치
    commercialization_readiness: float    # 상업화 준비도 (0.0-0.3)
    market_score: float                   # 총 시장성 점수 (0.0-1.0)
    
    # 정성적 평가
    application_domains: List[str]        # 적용 가능한 산업/제품군
    commercialization_potential: str      # 상업화 가능성 (High/Medium/Low)
    market_rationale: str                 # 시장성 평가 근거 (한글, 5~7문장)
    demand_signals: List[str]             # 시장 수요 신호
    
    # 검색 관련 (내부 사용)
    keyterms: List[str]                   # Abstract에서 추출한 핵심 키워드
    retrieved_docs: List[Any]             # RAG 검색 문서
    web_search_results: List[Dict[str, Any]]  # Tavily 웹 검색 결과
    
    # 출처 및 출력
    sources: List[str]                    # 참고 문서 출처 (RAG + Tavily)
    market_output_path: str               # 시장성 평가 결과 저장 경로
    
    # ========== Deprecated Fields (Backward Compatibility) ==========
    market_size: str                      # DEPRECATED - use market_size_score
    growth_potential: str                 # DEPRECATED - use growth_potential_score
    
    # ========== Sustainability Score Agent Fields ==========
    # 계산 결과
    calculated_score: float               # 수식 기반 계산 점수 (0~1)
    calculated_grade: str                 # 수식 기반 등급 (S/A/B/C/D)
    
    # 최종 결과
    sustainability_score: float           # 최종 지속가능성 점수 (0~1)
    sustainability_grade: str             # 최종 등급 (S/A/B/C/D)
    final_grade: str                      # LLM Judge 최종 등급
    
    # 상세 정보
    score_breakdown: Dict[str, float]     # 점수 분해 정보
    llm_evaluation: Dict[str, Any]        # LLM Judge 평가 결과 (v2)
    # {
    #   "sustainability_grade": "A",
    #   "confidence_score": 0.92,
    #   "key_strengths": ["...", "..."],
    #   "key_weaknesses": ["...", "..."],
    #   "investment_recommendation": "추천/보류/비추천",
    #   "risk_level": "낮음/보통/높음",
    #   "reasoning": "...",
    #   "strategic_advice": "..."
    # }
    evaluation_summary: str               # 종합 평가 요약
    sustainability_output_path: str       # 지속가능성 평가 결과 저장 경로


__all__ = ["WorkflowState"]