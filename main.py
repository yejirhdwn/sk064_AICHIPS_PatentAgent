from __future__ import annotations

import os
import json
from typing import Any, Dict
from dotenv import load_dotenv

try:
    from langgraph.graph import StateGraph, END  # type: ignore
    _HAS_LANGGRAPH = True
except Exception:
    _HAS_LANGGRAPH = False

from agents.patent_search_agent import patent_search_node
from agents.patent_originality_agent import patent_originality_node


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
    tech_name = os.environ.get("TECH_NAME", "HBM")

    app = build_graph()
    init_state: Dict[str, Any] = {"tech_name": tech_name, "num": 10, "page": 1, "ptype": "PATENT"}

    result = app.invoke(init_state)

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
        print(f"Summary saved: {out_path}")
    except Exception as e:
        print(f"Failed to write summary: {e}")

    print("Originality score:", result.get("originality_score"))


if __name__ == "__main__":
    main()
