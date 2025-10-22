"""
MarketState - Tavily Web Search 통합 시장성 평가용 State
- RAG + Tavily 하이브리드 검색
- SAM 기반 시장 규모 평가
- 구체적 성장 수치 (억/조 단위, CAGR) 활용
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TypedDict


class MarketState(TypedDict, total=False):
    """특허 시장성 평가 State (Tavily 통합)"""
    
    # ── Common ────────────────────────────────────────────────────────────────
    tech_name: str                     # 앵커 키워드 (예: "NPU", "AI accelerator")
    error: str                         # 노드 실행 중 오류 메시지 (옵션)

    # ── Inputs ────────────────────────────────────────────────────────────────
    first_item: Dict[str, Any]         # {"title": str, "abstract": str, "publication_number": str, ...}
    target_patent_id: str              # 평가 대상 특허 ID (없으면 first_item에서 추출)
    query: str                         # RAG 검색 쿼리 (내부 생성)

    # ── Internals ─────────────────────────────────────────────────────────────
    keyterms: List[str]                # Abstract에서 추출한 핵심 기술 키워드
    retrieved_docs: List[Dict[str, Any]]  # RAG에서 검색된 로컬 문서 목록
    web_search_results: List[Dict[str, Any]]  # Tavily에서 검색된 웹 문서 목록

    # ── Quantitative Scores ───────────────────────────────────────────────────
    market_size_score: float           # 시장 규모 점수 (0~0.4) - SAM 기반
    growth_potential_score: float      # 성장 잠재력 점수 (0~0.3) - CAGR/구체적 수치
    commercialization_readiness: float # 상업화 준비도 (0~0.3)
    market_score: float                # 총 시장성 점수 (0~1.0)

    # ── Qualitative Outputs ───────────────────────────────────────────────────
    patent_id: str                     # 평가된 특허 ID
    patent_title: str                  # 특허 제목
    application_domains: List[str]     # 적용 가능한 산업/제품군 (최대 5개)
    commercialization_potential: str   # High / Medium / Low
    market_rationale: str              # "이 특허(patent_id)는 ..." 형식, 5~7문장
    demand_signals: List[str]          # 시장 수요 신호 bullet (최대 5개)
    
    # ── Evidence & Sources ────────────────────────────────────────────────────
    sources: List[str]                 # RAG + Tavily 참고 문서 출처 (자동 수집)
    market_output_path: str            # 결과 JSON 파일 저장 경로


# 점수 기준 상수
class MarketScoreGuidelines:
    """시장성 점수 평가 가이드라인 (v3.0 - Tavily 통합)"""
    
    MARKET_SIZE = {
        "EXCELLENT": (0.35, 0.4, "$10B+ SAM - 여러 주요 제품군에 필수", 
                      "예: LLM 훈련 인프라 $12B, 자율주행 센서 $15B"),
        "GOOD": (0.25, 0.35, "$3B~$10B SAM - 특정 주요 제품군의 핵심",
                 "예: 추천시스템 임베딩 $5B, 음성인식 가속 $6B"),
        "MODERATE": (0.15, 0.25, "$1B~$3B SAM - 특정 Use Case 집중",
                     "예: 특정 모델 최적화 $1.5B"),
        "LOW": (0.1, 0.15, "$300M~$1B SAM - 틈새 응용",
                "예: 의료 영상 전용 NPU $800M"),
        "MINIMAL": (0.0, 0.1, "$300M 미만 - 실험적/제한적",
                    "예: 초기 POC, 연구 단계")
    }
    
    GROWTH_POTENTIAL = {
        "EXPLOSIVE": (0.25, 0.3, "CAGR 25%+ 또는 5년간 2배+ 성장",
                      "예: 2025년 310억 → 2029년 602억 달러"),
        "HIGH": (0.2, 0.25, "CAGR 20~25%",
                 "예: CAGR 23%, 5년간 1.8배 성장"),
        "MODERATE": (0.15, 0.2, "CAGR 15~20%",
                     "예: 연 17% 성장 지속"),
        "LOW": (0.1, 0.15, "CAGR 10~15%",
                "예: CAGR 11%"),
        "STAGNANT": (0.0, 0.1, "CAGR <10% 또는 정체",
                     "예: 단일 자릿수 성장률")
    }
    
    COMMERCIALIZATION = {
        "READY": (0.25, 0.3, "즉시~1년 내, 명확한 고객",
                  "예: 기존 제품 개선, API 통합"),
        "NEAR_TERM": (0.2, 0.25, "1~2년, 프로토타입 검증 완료",
                      "예: 베타 테스트 중"),
        "MID_TERM": (0.15, 0.2, "2~3년, 파일럿 단계",
                     "예: 시범 사업 진행"),
        "LONG_TERM": (0.1, 0.15, "3~5년, 초기 R&D",
                      "예: 표준화 작업 필요"),
        "UNCLEAR": (0.0, 0.1, "5년+, 상업화 경로 불명확",
                    "예: 기초 연구")
    }


class SearchMetrics(TypedDict, total=False):
    """검색 성능 메트릭 (옵션)"""
    rag_docs_count: int                # RAG 검색 문서 수
    web_results_count: int             # Tavily 검색 결과 수
    total_sources: int                 # 총 출처 수
    tavily_queries: List[str]          # 사용된 Tavily 쿼리 목록
    search_time_seconds: float         # 검색 소요 시간


__all__ = ["MarketState", "MarketScoreGuidelines", "SearchMetrics"]