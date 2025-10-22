"""
Sustainability State Definition
지속가능성 평가를 위한 State 타입 정의
"""

from typing import TypedDict, Dict, Any, Optional


class SustainabilityState(TypedDict, total=False):
    """
    지속가능성 평가 State
    
    Inputs (from other agents):
        originality_score: 독창성 점수 (0~1)
        market_score: 시장성 점수 (0~1)
        market_size_score: 시장 규모 세부 점수
        growth_potential_score: 성장 잠재력 세부 점수
        commercialization_readiness: 상업화 준비도 세부 점수
    
    Outputs:
        sustainability_score: 최종 지속가능성 점수 (0~1)
        sustainability_grade: 등급 (S/A/B/C/D)
        calculated_score: 수식 기반 계산 점수
        calculated_grade: 수식 기반 계산 등급
        final_grade: LLM Judge 최종 등급
        score_breakdown: 점수 분해 정보
        llm_evaluation: LLM Judge 평가 결과
        evaluation_summary: 종합 평가 요약
        sustainability_output_path: 결과 저장 경로
    """
    
    # ========== Common Fields ==========
    tech_name: str
    error: str
    
    # ========== Input Scores (from other agents) ==========
    originality_score: float              # Patent Originality Agent
    market_score: float                   # Market Size Growth Agent
    
    # Optional detailed scores
    market_size_score: float              # 시장 규모 (0~0.4)
    growth_potential_score: float         # 성장 잠재력 (0~0.3)
    commercialization_readiness: float    # 상업화 준비도 (0~0.3)
    
    # ========== Calculation Results ==========
    calculated_score: float               # 수식 기반 계산 점수 (0~1)
    calculated_grade: str                 # 수식 기반 등급 (S/A/B/C/D)
    
    # ========== Final Results ==========
    sustainability_score: float           # 최종 지속가능성 점수 (0~1)
    sustainability_grade: str             # 최종 등급 (S/A/B/C/D)
    final_grade: str                      # LLM Judge 최종 등급
    
    # ========== Detailed Information ==========
    score_breakdown: Dict[str, float]     # 점수 분해
    # {
    #   "originality_raw": 0.92,
    #   "originality_normalized": 0.68,
    #   "originality_weighted": 0.374,
    #   "market_score": 0.88,
    #   "market_weighted": 0.396,
    #   "calculated_score": 0.77
    # }
    
    llm_evaluation: Optional[Dict[str, Any]]  # LLM Judge 평가 결과
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
    sustainability_output_path: str       # 결과 저장 경로


__all__ = ["SustainabilityState"]