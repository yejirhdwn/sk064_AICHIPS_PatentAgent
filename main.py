from __future__ import annotations

import os
import json
import argparse
from typing import Any, Dict
from dotenv import load_dotenv

try:
    from langgraph.graph import StateGraph, END  # type: ignore
    _HAS_LANGGRAPH = True
except Exception:
    _HAS_LANGGRAPH = False

from agents.patent_search_agent import patent_search_node
from agents.patent_originality_agent import patent_originality_node


DEFAULT_TECH_NAME = "Neuromorphic"  # Change here; everything follows this


def build_graph():
    if _HAS_LANGGRAPH:
        workflow = StateGraph(dict)  # dict state
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

    parser = argparse.ArgumentParser()
    parser.add_argument("--tech_name", type=str, default=DEFAULT_TECH_NAME)
    parser.add_argument("--num", type=int, default=10)
    parser.add_argument("--page", type=int, default=1)
    args = parser.parse_args()

    tech_name = args.tech_name

    print("="*70)
    print(f"🚀 Patent Analysis Pipeline Starting")
    print("="*70)
    print(f"Technology: {tech_name}")
    print(f"Number of patents: {args.num}")
    print(f"Page: {args.page}")
    print("="*70 + "\n")

    app = build_graph()
    init_state: Dict[str, Any] = {
        "tech_name": tech_name, 
        "num": args.num, 
        "page": args.page, 
        "ptype": "PATENT"
    }

    try:
        result = app.invoke(init_state)
        
        # Debug: Print result keys
        print("\n" + "="*70)
        print("📊 Pipeline Results")
        print("="*70)
        print(f"Result keys: {list(result.keys())}")
        
        if result.get("error"):
            print(f"❌ Error occurred: {result.get('error')}")
        else:
            print(f"✅ Pipeline completed successfully")
            
        # Write optional summary
        try:
            base_dir = os.path.join(os.path.dirname(__file__), "output", "summary")
            os.makedirs(base_dir, exist_ok=True)
            patent_id = (result.get("first_item") or {}).get("patent_id") or result.get("target_patent_id") or "unknown"
            # sanitize file name
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
            print(f"💾 Summary saved: {out_path}")
        except Exception as e:
            print(f"⚠️ Failed to write summary: {e}")

        print(f"\n{'='*70}")
        print(f"🎯 Final Originality Score: {result.get('originality_score', 'N/A')}")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()