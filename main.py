"""
Patent Analysis Pipeline - Full Integration (FIXED)
특허 검색 → 독창성 분석 → 시장성 평가 → 지속가능성 평가
"""

from __future__ import annotations

import os
import json
from typing import Any, Dict
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

try:
    from langgraph.graph import StateGraph, END
    _HAS_LANGGRAPH = True
except Exception:
    _HAS_LANGGRAPH = False

from state.workflow_state import WorkflowState
from agents.patent_search_agent import patent_search_node
from agents.patent_originality_agent import patent_originality_node
from agents.market_size_growth_agent import MarketSizeGrowthAgent
from agents.suitability_agent import SustainabilityScoreAgent


# ===== Market Evaluation Node =====
def market_evaluation_node(state: WorkflowState) -> WorkflowState:
    """시장성 평가 노드"""
    print("\n" + "="*80)
    print("📊 Step 3: Market Evaluation")
    print("="*80)
    
    if state.get("error"):
        print(f"⚠️ Skipping due to previous error: {state['error']}")
        return state
    
    tech_name = state.get("tech_name", "Unknown")
    first_item = state.get("first_item", {})
    
    # Patent 정보 확인
    patent_id = first_item.get("patent_id")
    patent_abstract = first_item.get("abstract") or first_item.get("abstract_full")
    
    if not patent_id or not patent_abstract:
        state["error"] = "No patent information for market evaluation"
        return state
    
    try:
        # Market Agent 실행 (✅ 파라미터 수정)
        agent = MarketSizeGrowthAgent(
            tech_name=tech_name,
            patent_info=first_item,  # ✅ patent_json_or_dict → patent_info
            output_dir="./output/market_evaluation"  # ✅ 기본값이지만 명시
        )
        
        market_result = agent.evaluate_market()
        
        # State 업데이트
        state.update({
            "market_size_score": market_result["market_size_score"],
            "growth_potential_score": market_result["growth_potential_score"],
            "commercialization_readiness": market_result["commercialization_readiness"],
            "market_score": market_result["market_score"],
            "application_domains": market_result.get("application_domains", []),
            "commercialization_potential": market_result.get("commercialization_potential", ""),
            "market_rationale": market_result.get("market_rationale", ""),
            "demand_signals": market_result.get("demand_signals", []),
            "sources": market_result.get("sources", []),
            "market_output_path": market_result.get("output_path", "")
        })
        
        print(f"✅ Market Score: {market_result['market_score']:.4f}")
        print(f"   - Market Size: {market_result['market_size_score']:.2f}")
        print(f"   - Growth Potential: {market_result['growth_potential_score']:.2f}")
        print(f"   - Commercialization: {market_result['commercialization_readiness']:.2f}")
        
    except Exception as e:
        print(f"❌ Market evaluation failed: {e}")
        state["error"] = f"Market evaluation error: {e}"
    
    return state


# ===== Sustainability Scoring Node =====
def sustainability_scoring_node(state: WorkflowState) -> WorkflowState:
    """지속가능성 평가 노드"""
    print("\n" + "="*80)
    print("🌱 Step 4: Sustainability Scoring")
    print("="*80)
    
    if state.get("error"):
        print(f"⚠️ Skipping due to previous error: {state['error']}")
        return state
    
    # 필수 점수 확인
    originality_score = state.get("originality_score")
    market_score = state.get("market_score")
    
    if originality_score is None or market_score is None:
        state["error"] = "Missing originality or market score"
        return state
    
    tech_name = state.get("tech_name", "Unknown")
    
    try:
        # Sustainability Agent 실행
        agent = SustainabilityScoreAgent(
            tech_name=tech_name,
            use_llm_judge=True  # LLM Judge 활성화
        )
        
        result = agent.calculate_sustainability(
            originality_score=originality_score,
            market_score=market_score,
            market_size_score=state.get("market_size_score"),
            growth_potential_score=state.get("growth_potential_score"),
            commercialization_readiness=state.get("commercialization_readiness")
        )
        
        # State 업데이트
        state.update({
            "calculated_score": result["calculated_score"],
            "calculated_grade": result["calculated_grade"],
            "sustainability_score": result["sustainability_score"],
            "sustainability_grade": result["sustainability_grade"],
            "final_grade": result["final_grade"],
            "score_breakdown": result["score_breakdown"],
            "llm_evaluation": result.get("llm_evaluation"),
            "evaluation_summary": result["evaluation_summary"],
            "sustainability_output_path": result["sustainability_output_path"]
        })
        
        print(f"✅ Final Grade: {result['final_grade']}")
        print(f"   - Calculated: {result['calculated_grade']} ({result['calculated_score']:.4f})")
        
        if result.get("llm_evaluation"):
            llm_eval = result["llm_evaluation"]
            print(f"   - LLM Assessment: {result['final_grade']}")
            print(f"   - Investment: {llm_eval.get('investment_recommendation', 'N/A')}")
            print(f"   - Risk: {llm_eval.get('risk_level', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Sustainability scoring failed: {e}")
        state["error"] = f"Sustainability scoring error: {e}"
    
    return state


# ===== Graph Builder =====
def build_graph():
    """전체 워크플로우 그래프 구성"""
    if _HAS_LANGGRAPH:
        workflow = StateGraph(WorkflowState)
        
        # 노드 추가
        workflow.add_node("PatentSearch", patent_search_node)
        workflow.add_node("PatentOriginality", patent_originality_node)
        workflow.add_node("MarketEvaluation", market_evaluation_node)
        workflow.add_node("SustainabilityScoring", sustainability_scoring_node)
        
        # 엣지 연결
        workflow.set_entry_point("PatentSearch")
        workflow.add_edge("PatentSearch", "PatentOriginality")
        workflow.add_edge("PatentOriginality", "MarketEvaluation")
        workflow.add_edge("MarketEvaluation", "SustainabilityScoring")
        workflow.add_edge("SustainabilityScoring", END)
        
        return workflow.compile()
    else:
        # LangGraph 없을 때 fallback
        class _App:
            def invoke(self, init_state: Dict[str, Any]) -> Dict[str, Any]:
                s1 = patent_search_node(init_state)
                s2 = patent_originality_node(s1)
                s3 = market_evaluation_node(s2)
                s4 = sustainability_scoring_node(s3)
                return s4
        return _App()


# ===== Summary Writer =====
def save_comprehensive_summary(result: WorkflowState, tech_name: str):
    """종합 결과 저장"""
    try:
        base_dir = Path(__file__).parent / "output" / "summary"
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        patent_id = result.get("target_patent_id", "unknown")
        safe_patent_id = ''.join(
            ch if (ch.isalnum() or ch in ('_', '-')) else '_' 
            for ch in str(patent_id)
        )
        
        filename = f"{tech_name}_{safe_patent_id}_{timestamp}_FULL.json"
        out_path = base_dir / filename
        
        # 종합 요약 구성
        summary = {
            "tech_name": tech_name,
            "patent_id": patent_id,
            "patent_title": result.get("first_item", {}).get("title"),
            "generated_at": datetime.now().isoformat(),
            
            # 1. Patent Search
            "search": {
                "query": result.get("query"),
                "count": result.get("count"),
                "output_path": result.get("search_output_path")
            },
            
            # 2. Originality
            "originality": {
                "score": result.get("originality_score"),
                "cpc_distribution": result.get("cpc_distribution"),
                "statistics": result.get("statistics"),
                "output_path": result.get("originality_output_path")
            },
            
            # 3. Market Evaluation
            "market": {
                "total_score": result.get("market_score"),
                "market_size_score": result.get("market_size_score"),
                "growth_potential_score": result.get("growth_potential_score"),
                "commercialization_readiness": result.get("commercialization_readiness"),
                "application_domains": result.get("application_domains"),
                "commercialization_potential": result.get("commercialization_potential"),
                "market_rationale": result.get("market_rationale"),
                "demand_signals": result.get("demand_signals"),
                "sources": result.get("sources"),
                "output_path": result.get("market_output_path")
            },
            
            # 4. Sustainability
            "sustainability": {
                "calculated_score": result.get("calculated_score"),
                "calculated_grade": result.get("calculated_grade"),
                "final_score": result.get("sustainability_score"),
                "final_grade": result.get("final_grade"),
                "score_breakdown": result.get("score_breakdown"),
                "llm_evaluation": result.get("llm_evaluation"),
                "evaluation_summary": result.get("evaluation_summary"),
                "output_path": result.get("sustainability_output_path")
            },
            
            # Error (if any)
            "error": result.get("error")
        }
        
        # JSON 저장
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Comprehensive summary saved: {out_path}")
        return str(out_path)
        
    except Exception as e:
        print(f"⚠️ Failed to save comprehensive summary: {e}")
        return None


# ===== Display Results =====
def display_final_results(result: WorkflowState):
    """최종 결과 출력"""
    print("\n" + "="*80)
    print("🎯 FINAL RESULTS - COMPREHENSIVE ANALYSIS")
    print("="*80)
    
    tech_name = result.get("tech_name", "N/A")
    patent_id = result.get("target_patent_id", "N/A")
    
    print(f"\n📌 Basic Information:")
    print(f"   Technology: {tech_name}")
    print(f"   Patent ID: {patent_id}")
    
    # Originality
    orig_score = result.get("originality_score")
    if orig_score is not None:
        if orig_score >= 0.8:
            interpretation = "🔥 Highly Original"
        elif orig_score >= 0.6:
            interpretation = "✅ Original"
        else:
            interpretation = "➖ Moderate"
        print(f"\n🔬 Originality Analysis:")
        print(f"   Score: {orig_score:.4f} ({interpretation})")
        
        if result.get("statistics"):
            stats = result["statistics"]
            print(f"   • Total CPC: {stats.get('total_cpc_count', 0)}")
            print(f"   • Unique CPC: {stats.get('unique_cpc_count', 0)}")
    
    # Market
    market_score = result.get("market_score")
    if market_score is not None:
        print(f"\n📊 Market Evaluation:")
        print(f"   Total Score: {market_score:.4f}")
        print(f"   • Market Size: {result.get('market_size_score', 0):.2f}/0.4")
        print(f"   • Growth Potential: {result.get('growth_potential_score', 0):.2f}/0.3")
        print(f"   • Commercialization: {result.get('commercialization_readiness', 0):.2f}/0.3")
        
        domains = result.get("application_domains", [])
        if domains:
            print(f"   • Domains: {', '.join(domains[:3])}")
    
    # Sustainability
    final_grade = result.get("final_grade")
    if final_grade:
        print(f"\n🌱 Sustainability Assessment:")
        print(f"   Final Grade: {final_grade}")
        print(f"   • Calculated: {result.get('calculated_grade', 'N/A')} ({result.get('calculated_score', 0):.4f})")
        
        llm_eval = result.get("llm_evaluation")
        if llm_eval:
            print(f"   • LLM Assessment: {final_grade}")
            print(f"   • Investment: {llm_eval.get('investment_recommendation', 'N/A')}")
            print(f"   • Risk Level: {llm_eval.get('risk_level', 'N/A')}")
            print(f"   • Confidence: {llm_eval.get('confidence_score', 0):.2f}")
            
            print(f"\n   💡 Key Strengths:")
            for strength in llm_eval.get("key_strengths", [])[:3]:
                print(f"      • {strength}")
            
            if llm_eval.get("key_weaknesses"):
                print(f"\n   ⚠️ Key Weaknesses:")
                for weakness in llm_eval.get("key_weaknesses", [])[:2]:
                    print(f"      • {weakness}")
    
    # Output Files
    print(f"\n📁 Output Files:")
    if result.get("search_output_path"):
        print(f"   • Search: {result['search_output_path']}")
    if result.get("originality_output_path"):
        print(f"   • Originality: {result['originality_output_path']}")
    if result.get("market_output_path"):
        print(f"   • Market: {result['market_output_path']}")
    if result.get("sustainability_output_path"):
        print(f"   • Sustainability: {result['sustainability_output_path']}")
    
    # Error
    if result.get("error"):
        print(f"\n   ❌ Error: {result['error']}")
    
    print("="*80 + "\n")


# ===== Main =====
def main():
    load_dotenv()
    
    # 기술명 설정
    tech_name = os.environ.get("TECH_NAME", "NPU")
    
    print("\n" + "="*80)
    print("🚀 Patent Analysis Pipeline - Full Integration (FIXED)")
    print("="*80)
    print(f"   Technology: {tech_name}")
    print(f"   Using LangGraph: {_HAS_LANGGRAPH}")
    print(f"\n   Pipeline:")
    print(f"   1. Patent Search (US patents only)")
    print(f"   2. Originality Analysis")
    print(f"   3. Market Evaluation")
    print(f"   4. Sustainability Scoring")
    print("="*80)
    
    # 워크플로우 실행
    app = build_graph()
    
    # ✅ FIX: country="US" 추가
    init_state: WorkflowState = {
        "tech_name": tech_name,
        "num": 10,
        "page": 1,
        "ptype": "PATENT",
        "country": "US"  # ✅ 미국 특허만 검색
    }
    
    result: WorkflowState = app.invoke(init_state)
    
    # 종합 요약 저장
    save_comprehensive_summary(result, tech_name)
    
    # 최종 결과 출력
    display_final_results(result)


if __name__ == "__main__":
    main()