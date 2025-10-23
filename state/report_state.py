"""
Report Agent State
보고서 생성을 위한 Input/Output State 정의
"""
from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class ReportAgentInput(TypedDict, total=False):
    """
    Report Agent Input State
    보고서 생성에 필요한 입력 필드
    """
    # Required Fields
    tech_name: str                            # 기술명 (예: "NPU")
    all_patent_results: List[Dict[str, Any]]  # 모든 특허의 분석 결과
    
    # Optional Fields
    top_items: List[Dict[str, Any]]           # 상위 특허 원본 정보 (선택)
    output_dir: str                           # 출력 디렉토리 (기본: ./output/reports)
    use_rag: bool                             # RAG 사용 여부 (기본: True)
    
    # Error Handling
    error: str                                # 이전 단계 에러 메시지


class ReportAgentOutput(TypedDict, total=False):
    """
    Report Agent Output State
    보고서 생성 결과
    """
    # Report Files
    report_html_path: str                     # 생성된 HTML 보고서 경로
    report_json_path: str                     # 생성된 JSON 메타데이터 경로
    report_title: str                         # 보고서 제목
    report_generated_at: str                  # 보고서 생성 시각 (ISO format)
    
    # RAG Context (from AI반도체시장현황및전망.pdf)
    industry_context: str                     # 산업 현황 컨텍스트
    policy_context: str                       # 정책 현황 컨텍스트
    korea_position_context: str               # 한국 포지션 컨텍스트
    rag_sources: List[str]                    # RAG 문서 출처
    
    # Statistics
    total_patents_analyzed: int               # 분석된 특허 수
    avg_originality_score: float              # 평균 독창성 점수
    avg_market_score: float                   # 평균 시장성 점수
    grade_distribution: Dict[str, int]        # 등급 분포 {"S": 1, "A": 2, ...}
    
    # Error Handling
    error: str                                # 에러 메시지


class ReportAgentState(TypedDict, total=False):
    """
    Report Agent 통합 State (Input + Output)
    """
    # Input Fields
    tech_name: str
    all_patent_results: List[Dict[str, Any]]
    top_items: List[Dict[str, Any]]
    output_dir: str
    use_rag: bool
    
    # Output Fields
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
    
    # Error
    error: str


__all__ = [
    "ReportAgentInput",
    "ReportAgentOutput",
    "ReportAgentState"
]