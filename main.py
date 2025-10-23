"""
Patent Analysis Pipeline - Full Integration WITH REPORT GENERATION
특허 검색 → 독창성 분석 → 시장성 평가 → 지속가능성 평가 → 보고서 생성
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
from agents.suitability_agent import SuitabilityScoreAgent
from agents.report_agent import pdf_report_agent_node  # ⭐ PDF Report Agent


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
    
    patent_id = first_item.get("patent_id")
    patent_abstract = first_item.get("abstract") or first_item.get("abstract_full")
    
    if not patent_id or not patent_abstract:
        state["error"] = "No patent information for market evaluation"
        return state
    
    try:
        agent = MarketSizeGrowthAgent(
            tech_name=tech_name,
            patent_info=first_item,
            output_dir="./output/market_evaluation"
        )
        
        market_result = agent.evaluate_market()
        
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
        
    except Exception as e:
        print(f"❌ Market evaluation failed: {e}")
        state["error"] = f"Market evaluation error: {e}"
    
    return state


# ===== Suitability Scoring Node =====
def suitability_scoring_node(state: WorkflowState) -> WorkflowState:
    """지속가능성 평가 노드"""
    print("\n" + "="*80)
    print("🌱 Step 4: Suitability Scoring")
    print("="*80)
    
    if state.get("error"):
        print(f"⚠️ Skipping due to previous error: {state['error']}")
        return state
    
    originality_score = state.get("originality_score")
    market_score = state.get("market_score")
    
    if originality_score is None or market_score is None:
        state["error"] = "Missing originality or market score"
        return state
    
    tech_name = state.get("tech_name", "Unknown")
    
    try:
        agent = SuitabilityScoreAgent(
            tech_name=tech_name,
            use_llm_judge=True
        )
        
        result = agent.calculate_suitability(
            originality_score=originality_score,
            market_score=market_score,
            market_size_score=state.get("market_size_score"),
            growth_potential_score=state.get("growth_potential_score"),
            commercialization_readiness=state.get("commercialization_readiness")
        )
        
        state.update({
            "calculated_score": result["calculated_score"],
            "calculated_grade": result["calculated_grade"],
            "suitability_score": result["suitability_score"],
            "suitability_grade": result["suitability_grade"],
            "final_grade": result["final_grade"],
            "score_breakdown": result["score_breakdown"],
            "llm_evaluation": result.get("llm_evaluation"),
            "evaluation_summary": result["evaluation_summary"],
            "suitability_output_path": result["suitability_output_path"]
        })
        
        print(f"✅ Final Grade: {result['final_grade']}")
        
    except Exception as e:
        print(f"❌ Suitability scoring failed: {e}")
        state["error"] = f"Suitability scoring error: {e}"
    
    return state


# ===== Single Patent Pipeline =====
def process_single_patent(patent_item: Dict[str, Any], tech_name: str, patent_index: int) -> Dict[str, Any]:
    """단일 특허에 대한 전체 분석 파이프라인"""
    
    patent_id = patent_item.get("patent_id", "unknown")
    patent_title = patent_item.get("title", "Unknown")
    
    print("\n" + "="*80)
    print(f"🎯 Processing Patent #{patent_index}: {patent_id}")
    print(f"   Title: {patent_title}")
    print("="*80)
    
    state: WorkflowState = {
        "tech_name": tech_name,
        "first_item": patent_item,
        "items": [patent_item],
        "target_patent_id": patent_id,
        "count": 1,
    }
    
    # Step 1: Originality
    state = patent_originality_node(state)
    if state.get("error"):
        return state
    
    # Step 2: Market
    state = market_evaluation_node(state)
    if state.get("error"):
        return state
    
    # Step 3: Suitability
    state = suitability_scoring_node(state)
    if state.get("error"):
        return state
    
    # Save summary
    save_comprehensive_summary(state, tech_name, patent_index)
    
    return state


# ===== Summary Writer =====
def save_comprehensive_summary(result: WorkflowState, tech_name: str, patent_index: int = 1):
    """종합 결과 저장"""
    try:
        base_dir = Path(__file__).parent / "output" / "summary"
        base_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        patent_id = result.get("target_patent_id", "unknown")
        safe_patent_id = ''.join(
            ch if (ch.isalnum() or ch in ('_', '-')) else '_' 
            for ch in str(patent_id)
        )
        
        filename = f"{tech_name}_Patent{patent_index}_{safe_patent_id}_{timestamp}.json"
        out_path = base_dir / filename
        
        summary = {
            "tech_name": tech_name,
            "patent_index": patent_index,
            "generated_at": datetime.now().isoformat(),
            
            "patent_info": {
                "patent_id": result.get("target_patent_id"),
                "title": result.get("first_item", {}).get("title"),
                "abstract": result.get("first_item", {}).get("abstract")
            },
            
            "originality": {
                "score": result.get("originality_score"),
                "cpc_distribution": result.get("cpc_distribution"),
                "statistics": result.get("statistics"),
                "output_path": result.get("originality_output_path")
            },
            
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
            
            "suitability": {
                "calculated_score": result.get("calculated_score"),
                "calculated_grade": result.get("calculated_grade"),
                "final_score": result.get("suitability_score"),
                "final_grade": result.get("final_grade"),
                "score_breakdown": result.get("score_breakdown"),
                "llm_evaluation": result.get("llm_evaluation"),
                "evaluation_summary": result.get("evaluation_summary"),
                "output_path": result.get("suitability_output_path")
            },
            
            "error": result.get("error")
        }
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Comprehensive summary saved: {out_path}")
        return str(out_path)
        
    except Exception as e:
        print(f"⚠️ Failed to save comprehensive summary: {e}")
        return None


# ===== Display Results =====
def display_final_results(results: list[WorkflowState]):
    """최종 결과 출력"""
    print("\n" + "="*80)
    print("🎯 FINAL RESULTS - COMPREHENSIVE ANALYSIS (TOP 3 PATENTS)")
    print("="*80)
    
    for i, result in enumerate(results, 1):
        tech_name = result.get("tech_name", "N/A")
        patent_id = result.get("target_patent_id", "N/A")
        patent_title = result.get("first_item", {}).get("title", "N/A")
        
        print(f"\n{'='*80}")
        print(f"📌 Patent #{i}: {patent_id}")
        print(f"{'='*80}")
        print(f"   Technology: {tech_name}")
        print(f"   Title: {patent_title[:100]}...")
        
        # Scores
        orig_score = result.get("originality_score")
        market_score = result.get("market_score")
        final_grade = result.get("final_grade")
        
        if orig_score:
            print(f"\n🔬 Originality: {orig_score:.4f}")
        if market_score:
            print(f"📊 Market Score: {market_score:.4f}")
        if final_grade:
            print(f"🌱 Final Grade: {final_grade}")
        
        if result.get("error"):
            print(f"\n❌ Error: {result['error']}")
    
    print("\n" + "="*80 + "\n")


def save_combined_summary(results: list[WorkflowState], tech_name: str):
    """모든 특허의 결과를 하나의 파일로 저장"""
    try:
        base_dir = Path(__file__).parent / "output" / "summary"
        base_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{tech_name}_TOP3_COMBINED_{timestamp}.json"
        out_path = base_dir / filename
        
        combined = {
            "tech_name": tech_name,
            "generated_at": datetime.now().isoformat(),
            "total_patents_analyzed": len(results),
            "patents": []
        }
        
        for i, result in enumerate(results, 1):
            patent_summary = {
                "patent_index": i,
                "patent_id": result.get("target_patent_id"),
                "patent_title": result.get("first_item", {}).get("title"),
                "originality_score": result.get("originality_score"),
                "market_score": result.get("market_score"),
                "final_grade": result.get("final_grade"),
                "calculated_score": result.get("calculated_score"),
                "llm_evaluation": result.get("llm_evaluation"),
                "error": result.get("error")
            }
            combined["patents"].append(patent_summary)
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Combined summary saved: {out_path}")
        
    except Exception as e:
        print(f"⚠️ Failed to save combined summary: {e}")


# ===== Main =====
def main():
    load_dotenv()
    
    tech_name = os.environ.get("TECH_NAME", "NPU")
    
    print("\n" + "="*80)
    print("🚀 Patent Analysis Pipeline - WITH REPORT GENERATION")
    print("="*80)
    print(f"   Technology: {tech_name}")
    print(f"   Processing: Top 3 patents")
    print(f"\n   Pipeline:")
    print(f"   1. Patent Search (US patents)")
    print(f"   2. Originality Analysis")
    print(f"   3. Market Evaluation")
    print(f"   4. Suitability Scoring")
    print(f"   5. PDF Report Generation ⭐ NEW")
    print("="*80)
    
    # Step 1: Patent Search
    print("\n" + "="*80)
    print("📋 Step 1: Patent Search")
    print("="*80)
    
    init_state: WorkflowState = {
        "tech_name": tech_name,
        "num": 10,
        "page": 1,
        "ptype": "PATENT",
        "country": "US"
    }
    
    search_result: WorkflowState = patent_search_node(init_state)
    
    if search_result.get("error"):
        print(f"❌ Patent search failed: {search_result['error']}")
        return
    
    top_items = search_result.get("top_items", [])
    if not top_items:
        print("❌ No patents found")
        return
    
    print(f"\n✅ Found {len(top_items)} patents to process")
    
    # Step 2-4: Process each patent
    results = []
    for i, patent_item in enumerate(top_items, 1):
        result = process_single_patent(patent_item, tech_name, patent_index=i)
        results.append(result)
    
    # Display results
    display_final_results(results)
    
    # Save combined summary
    save_combined_summary(results, tech_name)
    
    # ⭐ Step 5: Generate PDF Report (NEW)
    print("\n" + "="*80)
    print("📊 Step 5: PDF Report Generation")
    print("="*80)
    
    final_state: WorkflowState = {
        "tech_name": tech_name,
        "all_patent_results": results,
        "output_dir": "./output/reports",
        "use_llm": True
    }
    
    final_state = pdf_report_agent_node(final_state)
    
    if final_state.get("report_pdf_path"):
        print("\n" + "="*80)
        print("🎉 PDF REPORT GENERATION COMPLETE!")
        print("="*80)
        print(f"📄 PDF Report: {final_state['report_pdf_path']}")
        print(f"📊 JSON Report: {final_state.get('report_json_path', 'N/A')}")
        print(f"📋 Report Title: {final_state['report_title']}")
        print(f"🕒 Generated At: {final_state['report_generated_at']}")
        print(f"\n📈 Statistics:")
        print(f"   Total Patents: {final_state['total_patents_analyzed']}")
        print(f"   Avg Originality: {final_state['avg_originality_score']:.4f}")
        print(f"   Avg Market: {final_state['avg_market_score']:.4f}")
        print(f"   Grade Distribution: {final_state['grade_distribution']}")
        print("="*80)
        print("\n✅ All analysis complete! Check the PDF report.")
    else:
        print("\n⚠️ PDF report generation failed. Check logs for details.")


if __name__ == "__main__":
    main()