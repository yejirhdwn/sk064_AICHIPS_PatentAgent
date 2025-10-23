"""
Multi-Country Patent Analysis Pipeline
국가별 특허 분석 → 한국 기술 경쟁력 보고서 생성
"""

from __future__ import annotations

import os
import json
from typing import Any, Dict, List
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from state.workflow_state import WorkflowState
from agents.patent_search_agent import patent_search_node
from agents.patent_originality_agent import patent_originality_node
from agents.market_size_growth_agent import MarketSizeGrowthAgent
from agents.suitability_agent import SuitabilityScoreAgent
from agents.report_agent import ReportAgent


# ===== Configuration =====
TARGET_COUNTRIES = [
    {"code": "US", "name": "United States"},
    {"code": "KR", "name": "South Korea"},
    {"code": "JP", "name": "Japan"},
]

PATENTS_PER_COUNTRY = 3


# ===== Helper Functions =====
def market_evaluation_node(state: WorkflowState) -> WorkflowState:
    """시장성 평가"""
    if state.get("error"):
        return state
    
    tech_name = state.get("tech_name", "Unknown")
    first_item = state.get("first_item", {})
    
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
            "market_rationale": market_result.get("market_rationale", ""),
            "demand_signals": market_result.get("demand_signals", []),
        })
        
    except Exception as e:
        state["error"] = f"Market evaluation error: {e}"
    
    return state


def suitability_scoring_node(
    state: WorkflowState, 
    patent_id: str, 
    patent_title: str
) -> WorkflowState:
    """지속가능성 평가"""
    if state.get("error"):
        return state
    
    originality_score = state.get("originality_score")
    market_score = state.get("market_score")
    
    if originality_score is None or market_score is None:
        state["error"] = "Missing scores"
        return state
    
    tech_name = state.get("tech_name", "Unknown")
    
    try:
        agent = SuitabilityScoreAgent(tech_name=tech_name, use_llm_judge=True)
        
        result = agent.calculate_suitability(
            originality_score=originality_score,
            market_score=market_score,
            patent_id=patent_id,
            patent_title=patent_title,
            market_size_score=state.get("market_size_score"),
            growth_potential_score=state.get("growth_potential_score"),
            commercialization_readiness=state.get("commercialization_readiness")
        )
        
        state.update({
            "suitability_score": result["suitability_score"],
            "final_grade": result["final_grade"],
            "llm_evaluation": result.get("llm_evaluation"),
        })
        
    except Exception as e:
        state["error"] = f"Suitability error: {e}"
    
    return state


# ===== Single Patent Analysis =====
def analyze_single_patent(
    patent_item: Dict[str, Any], 
    tech_name: str, 
    country_code: str,
    patent_index: int
) -> Dict[str, Any]:
    """단일 특허 분석"""
    
    patent_id = patent_item.get("patent_id", "unknown")
    patent_title = patent_item.get("title", "Unknown")
    
    print(f"   [{country_code}-{patent_index}] {patent_id}")
    
    state: WorkflowState = {
        "tech_name": tech_name,
        "first_item": patent_item,
        "target_patent_id": patent_id,
    }
    
    # 1. Originality
    state = patent_originality_node(state)
    if state.get("error"):
        print(f"       ❌ Originality failed: {state['error']}")
        return {
            "country": country_code,
            "patent_id": patent_id,
            "title": patent_title,
            "error": state["error"],
            "originality_score": 0.0,
            "market_score": 0.0,
            "suitability_score": 0.0,
            "final_grade": "N/A"
        }
    
    # 2. Market
    state = market_evaluation_node(state)
    if state.get("error"):
        print(f"       ❌ Market failed: {state['error']}")
        return {
            "country": country_code,
            "patent_id": patent_id,
            "title": patent_title,
            "error": state["error"],
            "originality_score": state.get("originality_score", 0.0),
            "market_score": 0.0,
            "suitability_score": 0.0,
            "final_grade": "N/A"
        }
    
    # 3. Suitability
    state = suitability_scoring_node(state, patent_id, patent_title)
    if state.get("error"):
        print(f"       ❌ Suitability failed: {state['error']}")
        return {
            "country": country_code,
            "patent_id": patent_id,
            "title": patent_title,
            "error": state["error"],
            "originality_score": state.get("originality_score", 0.0),
            "market_score": state.get("market_score", 0.0),
            "suitability_score": 0.0,
            "final_grade": "N/A"
        }
    
    # Result
    return {
        "country": country_code,
        "patent_id": patent_id,
        "title": patent_title,
        "abstract": patent_item.get("abstract"),
        "publication_date": patent_item.get("publication_date"),
        "assignee": patent_item.get("assignee"),
        
        "originality_score": state.get("originality_score"),
        "market_score": state.get("market_score"),
        "market_size_score": state.get("market_size_score"),
        "growth_potential_score": state.get("growth_potential_score"),
        "commercialization_readiness": state.get("commercialization_readiness"),
        "suitability_score": state.get("suitability_score"),
        "final_grade": state.get("final_grade"),
        
        "application_domains": state.get("application_domains", []),
        "market_rationale": state.get("market_rationale", ""),
        "llm_evaluation": state.get("llm_evaluation", {}),
    }


# ===== Country Analysis =====
def analyze_country_patents(tech_name: str, country: Dict[str, str]) -> Dict[str, Any]:
    """국가별 특허 분석"""
    
    country_code = country["code"]
    country_name = country["name"]
    
    print(f"\n{'='*80}")
    print(f"🌏 {country_name} ({country_code})")
    print(f"{'='*80}")
    
    # 1. Patent Search
    init_state: WorkflowState = {
        "tech_name": tech_name,
        "num": 10,
        "page": 1,
        "ptype": "PATENT",
        "country": country_code
    }
    
    search_result = patent_search_node(init_state)
    
    if search_result.get("error"):
        print(f"   ❌ Search failed: {search_result['error']}")
        return {
            "country_code": country_code,
            "country_name": country_name,
            "error": search_result["error"],
            "patents": []
        }
    
    top_items = search_result.get("top_items", [])
    if not top_items:
        print(f"   ⚠️ No patents found")
        return {
            "country_code": country_code,
            "country_name": country_name,
            "patents": []
        }
    
    print(f"   ✅ Found {len(top_items)} patents")
    
    # 2. Analyze each patent
    patent_results = []
    for i, patent_item in enumerate(top_items[:PATENTS_PER_COUNTRY], 1):
        result = analyze_single_patent(patent_item, tech_name, country_code, i)
        patent_results.append(result)
        
        # 결과 확인
        if result.get("error"):
            print(f"       ❌ Error: {result['error']}")
        else:
            print(f"       ✅ Success - Grade: {result.get('final_grade', 'N/A')}")
    
    # 3. Calculate statistics
    valid_results = [r for r in patent_results if not r.get("error")]
    
    if valid_results:
        avg_originality = sum(r["originality_score"] for r in valid_results) / len(valid_results)
        avg_market = sum(r["market_score"] for r in valid_results) / len(valid_results)
        avg_suitability = sum(r["suitability_score"] for r in valid_results) / len(valid_results)
        
        grade_counts = {}
        for r in valid_results:
            grade = r["final_grade"]
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
    else:
        avg_originality = 0.0
        avg_market = 0.0
        avg_suitability = 0.0
        grade_counts = {}
    
    summary = {
        "country_code": country_code,
        "country_name": country_name,
        "total_patents": len(patent_results),
        "successful_analyses": len(valid_results),
        "avg_originality_score": round(avg_originality, 4),
        "avg_market_score": round(avg_market, 4),
        "avg_suitability_score": round(avg_suitability, 4),
        "grade_distribution": grade_counts,
        "patents": patent_results
    }
    
    if valid_results:
        print(f"   📊 Avg: Orig={avg_originality:.3f}, Market={avg_market:.3f}, Suit={avg_suitability:.3f}")
        print(f"   ✅ Successfully analyzed: {len(valid_results)}/{len(patent_results)} patents")
    else:
        print(f"   ❌ No successful analyses (0/{len(patent_results)})")
    
    return summary


# ===== Technology Gap Analysis =====
def analyze_technology_gap(country_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """기술 격차 분석"""
    
    print(f"\n{'='*80}")
    print("🔍 Technology Gap Analysis")
    print(f"{'='*80}")
    
    # Find Korea
    korea_data = next((c for c in country_results if c["country_code"] == "KR"), None)
    
    if not korea_data or korea_data["successful_analyses"] == 0:
        print("   ⚠️ No Korean data")
        return {"error": "No Korean data"}
    
    korea_orig = korea_data["avg_originality_score"]
    korea_market = korea_data["avg_market_score"]
    korea_suit = korea_data["avg_suitability_score"]
    
    print(f"\n   🇰🇷 Korea Baseline:")
    print(f"      Orig={korea_orig:.4f}, Market={korea_market:.4f}, Suit={korea_suit:.4f}")
    
    # Compare
    comparisons = []
    
    for country in country_results:
        if country["country_code"] == "KR":
            continue
        
        if country.get("error") or country["successful_analyses"] == 0:
            continue
        
        orig_gap = country["avg_originality_score"] - korea_orig
        market_gap = country["avg_market_score"] - korea_market
        suit_gap = country["avg_suitability_score"] - korea_suit
        overall_gap = (orig_gap + market_gap + suit_gap) / 3
        
        comparison = {
            "country_code": country["country_code"],
            "country_name": country["country_name"],
            "originality_gap": round(orig_gap, 4),
            "market_gap": round(market_gap, 4),
            "suitability_gap": round(suit_gap, 4),
            "overall_gap": round(overall_gap, 4),
            "status": "Leading" if overall_gap > 0 else "Behind"
        }
        
        comparisons.append(comparison)
        
        status = "📈" if comparison["status"] == "Leading" else "📉"
        print(f"\n   {status} {country['country_name']}: {overall_gap:+.4f}")
    
    comparisons.sort(key=lambda x: x["overall_gap"], reverse=True)
    
    return {
        "korea_scores": {
            "originality": korea_orig,
            "market": korea_market,
            "suitability": korea_suit
        },
        "comparisons": comparisons
    }


# ===== Main =====
def main():
    load_dotenv()
    
    tech_name = os.environ.get("TECH_NAME", "NPU")
    
    print(f"\n{'='*80}")
    print("🚀 Multi-Country Patent Analysis")
    print(f"{'='*80}")
    print(f"   Technology: {tech_name}")
    print(f"   Countries: {', '.join([c['code'] for c in TARGET_COUNTRIES])}")
    print(f"{'='*80}")
    
    # Step 1: Analyze each country
    country_results = []
    
    for country in TARGET_COUNTRIES:
        result = analyze_country_patents(tech_name, country)
        country_results.append(result)
    
    # Step 2: Gap analysis
    gap_analysis = analyze_technology_gap(country_results)
    
    # Step 3: Save JSON
    base_dir = Path(__file__).parent / "output" / "multi_country"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = base_dir / f"{tech_name}_MultiCountry_{timestamp}.json"
    
    result_data = {
        "tech_name": tech_name,
        "generated_at": datetime.now().isoformat(),
        "countries": country_results,
        "gap_analysis": gap_analysis
    }
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Results saved: {json_path}")
    
    # Step 4: Generate Report
    print(f"\n{'='*80}")
    print("📊 Generating Report")
    print(f"{'='*80}")
    
    try:
        agent = ReportAgent(tech_name=tech_name, output_dir="./output/reports")
        
        # Flatten all patents for report
        all_patents = []
        for country in country_results:
            for patent in country.get("patents", []):
                if not patent.get("error"):
                    all_patents.append(patent)
        
        # Generate report with country comparison
        report_result = agent.generate_report_with_country_comparison(
            all_patents=all_patents,
            country_summaries=country_results,
            gap_analysis=gap_analysis
        )
        
        print(f"\n✅ Report generated: {report_result['report_pdf_path']}")
        
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("🎉 Analysis Complete!")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()