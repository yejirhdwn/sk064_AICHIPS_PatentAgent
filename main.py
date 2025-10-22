from __future__ import annotations

import os
import json
from typing import Any, Dict
from dotenv import load_dotenv

try:
    from langgraph.graph import StateGraph, END
    _HAS_LANGGRAPH = True
except Exception:
    _HAS_LANGGRAPH = False

from state.workflow_state import WorkflowState
from agents.patent_search_agent import patent_search_node
from agents.patent_originality_agent import patent_originality_node


def build_graph():
    """Build the patent analysis workflow graph"""
    if _HAS_LANGGRAPH:
        workflow = StateGraph(WorkflowState)
        workflow.add_node("PatentSearchAgent", patent_search_node)
        workflow.add_node("PatentOriginalityAgent", patent_originality_node)
        workflow.set_entry_point("PatentSearchAgent")
        workflow.add_edge("PatentSearchAgent", "PatentOriginalityAgent")
        workflow.add_edge("PatentOriginalityAgent", END)
        return workflow.compile()
    else:
        class _App:
            def invoke(self, init_state: Dict[str, Any]) -> Dict[str, Any]:
                s1 = patent_search_node(init_state)
                s2 = patent_originality_node(s1)
                return s2
        return _App()


def main():
    load_dotenv()
    tech_name = os.environ.get("TECH_NAME", "NPU")

    print("\n" + "="*70)
    print(f"🚀 Patent Analysis Starting")
    print(f"   Technology: {tech_name}")
    print(f"   Using LangGraph: {_HAS_LANGGRAPH}")
    print("="*70)

    app = build_graph()
    init_state: WorkflowState = {
        "tech_name": tech_name,
        "num": 10,
        "page": 1,
        "ptype": "PATENT"
    }

    result: WorkflowState = app.invoke(init_state)

    # DEBUG: Print result structure
    print("\n" + "="*70)
    print("🔍 DEBUG: Result Structure")
    print("="*70)
    print(f"   Result type: {type(result)}")
    if isinstance(result, dict):
        print(f"   Available keys ({len(result.keys())}): {sorted(result.keys())}")
        
        critical_fields = ['target_patent_id', 'originality_score', 'statistics']
        print(f"\n   Critical fields check:")
        for field in critical_fields:
            value = result.get(field)
            if value is not None:
                if field == 'originality_score':
                    print(f"      ✅ {field}: {value:.4f}")
                elif field == 'statistics' and isinstance(value, dict):
                    print(f"      ✅ {field}: dict with {len(value)} keys")
                else:
                    value_str = str(value)[:50]
                    print(f"      ✅ {field}: {value_str}")
            else:
                print(f"      ❌ {field}: None")
    print("="*70 + "\n")

    # Write summary
    try:
        base_dir = os.path.join(os.path.dirname(__file__), "output", "summary")
        os.makedirs(base_dir, exist_ok=True)
        
        patent_id = result.get("target_patent_id")
        if not patent_id and result.get("first_item"):
            patent_id = result["first_item"].get("patent_id")
        if not patent_id:
            patent_id = "unknown"
            
        safe_patent_id = ''.join(ch if (ch.isalnum() or ch in ('_','-')) else '_' for ch in str(patent_id))
        out_path = os.path.join(base_dir, f"{tech_name}_{safe_patent_id}_summary.json")
        
        summary = {
            "tech_name": tech_name,
            "patent_id": patent_id,
            "originality_score": result.get("originality_score"),
            "cpc_distribution": result.get("cpc_distribution"),
            "statistics": result.get("statistics"),
            "search_output_path": result.get("search_output_path"),
            "originality_output_path": result.get("originality_output_path"),
            "error": result.get("error"),
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"💾 Summary saved: {out_path}\n")
    except Exception as e:
        print(f"⚠️ Failed to write summary: {e}\n")

    # Display final results
    print("="*70)
    print("📊 FINAL RESULTS")
    print("="*70)
    print(f"   Technology: {tech_name}")
    
    patent_id = result.get('target_patent_id')
    if not patent_id and result.get('first_item'):
        patent_id = result['first_item'].get('patent_id')
    print(f"   Target Patent: {patent_id or 'N/A'}")
    
    orig_score = result.get('originality_score')
    if orig_score is not None:
        if orig_score >= 0.8:
            interpretation = "🔥 Highly Original"
        elif orig_score >= 0.6:
            interpretation = "✅ Original"
        elif orig_score >= 0.4:
            interpretation = "➖ Moderate"
        else:
            interpretation = "⚠️ Low"
        print(f"   Originality Score: {orig_score:.4f} ({interpretation})")
    else:
        print(f"   Originality Score: N/A")
    
    if result.get("statistics"):
        stats = result["statistics"]
        print(f"\n   📊 Detailed Statistics:")
        print(f"      • Base CPC Count: {stats.get('base_cpc_count', 0)}")
        print(f"      • Expanded CPC Count: {stats.get('expanded_cpc_count', 0)}")
        print(f"      • Total CPC Count: {stats.get('total_cpc_count', 0)}")
        print(f"      • Unique CPC Count: {stats.get('unique_cpc_count', 0)}")
        print(f"      • Citations Analyzed: {stats.get('citations_analyzed', 0)}")
        print(f"      • Patents Expanded: {stats.get('patents_expanded', 0)}")
    
    if result.get("search_output_path"):
        print(f"\n   📁 Search results: {result['search_output_path']}")
    if result.get("originality_output_path"):
        print(f"   📁 Originality results: {result['originality_output_path']}")
    
    if result.get("error"):
        print(f"\n   ❌ Error: {result.get('error')}")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()