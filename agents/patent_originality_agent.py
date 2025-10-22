from __future__ import annotations

import os
import json
import time
import requests
from collections import Counter
from typing import Any, Dict, List, Optional, TypedDict
from dotenv import load_dotenv

# Optional OpenAI client for CPC->keyword mapping
try:
    from openai import OpenAI  # type: ignore
    _OPENAI_OK = True
except Exception:
    _OPENAI_OK = False

# State types (fallbacks)
try:
    from state.originality_state import OriginalityState  # type: ignore
except Exception:
    class OriginalityState(TypedDict, total=False):
        tech_name: str
        first_item: Dict[str, Any]
        items: List[Dict[str, Any]]
        target_patent_id: str
        originality_score: float
        cpc_distribution: Dict[str, int]
        statistics: Dict[str, Any]
        originality_output_path: str
        error: str

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
BASE_URL = "https://serpapi.com/search.json"


def _fetch_patent_details(patent_id: str) -> Optional[Dict[str, Any]]:
    """
    OK: Simplified: No forced normalization, just like Patent_Scrapper_agent.py
    """
    if not patent_id:
        return None
    
    try:
        r = requests.get(
            BASE_URL,
            params={
                "engine": "google_patents_details",
                "patent_id": patent_id,  # ← Use patent_id as-is
                "api_key": SERPAPI_KEY,
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        
        if "error" in data:
            print(f"Warn: API 에러 ({patent_id}): {data.get('error')}")
            return None
            
        return data
    except Exception as e:
        print(f"Warn: {patent_id} 조회 실패: {e}")
        return None


def _collect_cpc_from_citations(patent_id: str, max_refs: int = 5) -> tuple[List[str], List[str]]:
    """
    OK: Exact copy from Patent_Scrapper_agent.py (lines 226-281)
    """
    print(f"\n* Step: 인용 특허에서 CPC 수집 ({patent_id})")
    
    details = _fetch_patent_details(patent_id)
    if not details:
        print("Error: 특허 조회 실패")
        return [], []

    # citations 추출
    patent_citations = details.get("patent_citations")
    if not patent_citations:
        print("Warn: 인용 정보 없음")
        return [], []
    
    citations = patent_citations.get("original", [])[:max_refs]
    if not citations:
        print("Warn: backward citation 없음")
        return [], []

    all_cpc_codes = []
    citation_ids = []

    print(f"   총 {len(citations)}건의 인용 특허 조회\n")
    
    for i, citation in enumerate(citations, start=1):
        cid = citation.get("patent_id")
        if not cid:
            continue
        
        citation_ids.append(cid)
        print(f"   [{i}/{len(citations)}] {cid}")
        
        # 각 인용 특허의 details 조회
        cit_details = _fetch_patent_details(cid)
        if not cit_details:
            continue
        
        # OK: CPC 코드 추출 (Patent_Scrapper_agent.py lines 269-276)
        classifications = cit_details.get("classifications", []) or []
        cpc_count = 0
        for cls in classifications:
            if cls.get("is_cpc") and cls.get("code"):
                all_cpc_codes.append(cls["code"])
                cpc_count += 1
        
        print(f"       → CPC {cpc_count}개 수집")
        time.sleep(0.3)  # API 부하 방지

    print(f"\nOK: CPC 수집 완료: 총 {len(all_cpc_codes)}개 (고유 {len(set(all_cpc_codes))}개)\n")
    return all_cpc_codes, citation_ids


def _convert_cpc_to_keywords(cpc_code: str) -> str:
    """
    OK: Exact copy from Patent_Scrapper_agent.py (lines 51-99)
    """
    if not _OPENAI_OK:
        print(f"       Warn: OpenAI 모듈 없음. Fallback 사용")
        return "semiconductor device technology"
    
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""CPC patent code: {cpc_code}

Generate a SPECIFIC patent search query (2-4 technical terms) for Google Patents.
Use concrete technical terms, avoid generic words like "AI", "computing", "architecture".
Focus on physical components, processes, or structures.

Examples:
H01L25/065 → chip stacking TSV interposer
G06F12/0802 → cache coherency protocol
H01L23/31 → thermal interface material heatsink
G11C11/401 → DRAM sense amplifier

{cpc_code} →"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=30,
            temperature=0
        )
        
        keywords = response.choices[0].message.content.strip()
        
        # OK: 화살표나 CPC 코드가 포함되어 있으면 제거
        if "→" in keywords:
            keywords = keywords.split("→")[-1].strip()
        if "->" in keywords:
            keywords = keywords.split("->")[-1].strip()
        # CPC 코드 자체가 포함되어 있으면 제거
        if cpc_code in keywords:
            keywords = keywords.replace(cpc_code, "").strip()
        
        print(f"       GPT: {keywords}")
        return keywords
        
    except Exception as e:
        print(f"       Warn: GPT 실패: {e}")
        return "semiconductor device technology"


def _search_patents_with_keywords(keyword: str, num: int = 10, country: str = "US") -> List[str]:
    """Search patents using keywords"""
    try:
        params = {
            "engine": "google_patents",
            "q": keyword,
            "country": country,
            "num": max(10, num),
            "api_key": SERPAPI_KEY,
        }
        
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        if "error" in data:
            print(f"       Warn: API 에러: {data.get('error')}")
            return []
        
        results = data.get("organic_results", []) or []
        
        ids: List[str] = []
        for item in results:
            pid = item.get("patent_id")
            if pid:
                ids.append(pid)
        
        return ids
        
    except Exception as e:
        print(f"       Warn: 검색 실패: {str(e)[:100]}")
        return []


def _collect_cpc_from_patents(patent_ids: List[str]) -> List[str]:
    """
    OK: Exact copy from Patent_Scrapper_agent.py (lines 396-424)
    """
    print(f"* Step: 확장 특허 {len(patent_ids)}개의 CPC 수집\n")
    
    all_cpc_codes = []
    
    for i, pid in enumerate(patent_ids, start=1):
        print(f"   [{i}/{len(patent_ids)}] {pid}")
        
        details = _fetch_patent_details(pid)
        if not details:
            continue
        
        classifications = details.get("classifications", []) or []
        cpc_count = 0
        for cls in classifications:
            if cls.get("is_cpc") and cls.get("code"):
                all_cpc_codes.append(cls["code"])
                cpc_count += 1
        
        if cpc_count > 0:
            print(f"       → CPC {cpc_count}개 추가")
        
        time.sleep(0.3)
    
    print(f"\nOK: 확장 CPC 수집 완료: {len(all_cpc_codes)}개\n")
    return all_cpc_codes


def _calc_originality_index(cpc_codes: List[str]) -> float:
    """
    OK: Exact copy from Patent_Scrapper_agent.py (lines 429-451)
    """
    if not cpc_codes:
        return 0.0
    
    counter = Counter(cpc_codes)
    total = sum(counter.values())
    
    # Herfindahl Index 계산
    hhi = sum((count / total) ** 2 for count in counter.values())
    
    # Originality = 1 - HHI
    originality = 1 - hhi
    
    return originality


def patent_originality_node(state: OriginalityState) -> OriginalityState:
    """Calculate patent originality score based on CPC classification diversity."""
    
    print("\n" + "="*60)
    print("* Starting Originality Analysis")
    print("="*60)
    
    # Check prerequisites
    if not SERPAPI_KEY:
        out = dict(state)
        out["error"] = "SERPAPI_KEY not set in environment variables"
        print("Error: Error: SERPAPI_KEY not configured")
        return out  # type: ignore

    # Check if previous search had errors
    if state.get("error"):
        out = dict(state)
        out["error"] = f"Previous search failed: {state['error']}"
        print(f"Error: Cannot calculate originality: {state['error']}")
        return out  # type: ignore

    # Pick target patent
    target_id = state.get("first_item", {}).get("patent_id") if state.get("first_item") else None
    if not target_id and state.get("items"):
        target_id = state["items"][0].get("patent_id")

    if not target_id:
        out = dict(state)
        out["error"] = "No target patent_id available from search results"
        print("Error: Error: No patent found to analyze")
        return out  # type: ignore

    print(f"* Target patent: {target_id}")

    # Step 1: Collect CPC from citations (using Patent_Scrapper_agent.py logic)
    base_cpc, citation_ids = _collect_cpc_from_citations(target_id, max_refs=5)

    if not base_cpc:
        out = dict(state)
        out.update({
            "target_patent_id": target_id,
            "originality_score": 0.0,
            "cpc_distribution": {},
            "statistics": {
                "base_cpc_count": 0,
                "expanded_cpc_count": 0,
                "total_cpc_count": 0,
                "unique_cpc_count": 0,
                "citations_analyzed": len(citation_ids),
                "patents_expanded": 0,
            },
            "error": "No CPC codes found in citations - cannot calculate originality"
        })
        print("Warn: No CPC codes found in citations")
        return out  # type: ignore

    # Step 2: Top-K CPC selection
    counter = Counter(base_cpc)
    top_k = [c for c, _ in counter.most_common(5)]
    print(f"\n🔝 Top {len(top_k)} CPC codes for expansion:")
    for i, code in enumerate(top_k, 1):
        print(f"  {i}. {code} (count: {counter[code]})")

    # Step 3: Convert CPC to keywords and expand
    print(f"\n🔄 Expanding patent pool via keyword search...")
    expanded_ids: List[str] = []
    seen = {target_id, *citation_ids}
    
    for i, code in enumerate(top_k, 1):
        print(f"\n  [{i}/{len(top_k)}] Processing CPC: {code}")
        kw = _convert_cpc_to_keywords(code)
        print(f"    → Keywords: {kw}")
        
        ids = _search_patents_with_keywords(kw, num=10, country="US")
        print(f"    → Found {len(ids)} patents")
        
        new_count = 0
        for pid in ids:
            if pid not in seen and pid not in expanded_ids:
                expanded_ids.append(pid)
                new_count += 1
        
        print(f"    → Added {new_count} new patents")
        time.sleep(0.3)

    print(f"\nOK: Total expanded patents: {len(expanded_ids)}")

    # Step 4: Collect CPC from expanded patents
    expanded_cpc = _collect_cpc_from_patents(expanded_ids)

    # Step 5: Calculate originality
    all_cpc = base_cpc + expanded_cpc
    originality = _calc_originality_index(all_cpc)
    dist = dict(Counter(all_cpc))

    stats: Dict[str, Any] = {
        "base_cpc_count": len(base_cpc),
        "expanded_cpc_count": len(expanded_cpc),
        "total_cpc_count": len(all_cpc),
        "unique_cpc_count": len(set(all_cpc)),
        "citations_analyzed": len(citation_ids),
        "patents_expanded": len(expanded_ids),
    }

    print(f"\n" + "="*60)
    print(f"* Originality Score: {originality:.4f}")
    print(f"* Statistics:")
    for key, val in stats.items():
        print(f"  • {key}: {val}")
    print("="*60)

    out: OriginalityState = dict(state)
    out.update(
        {
            "target_patent_id": target_id,
            "originality_score": originality,
            "cpc_distribution": dist,
            "statistics": stats,
        }
    )

    # Persist JSON
    try:
        base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "originality")
        os.makedirs(base_dir, exist_ok=True)
        safe_id = ''.join(ch if (ch.isalnum() or ch in ('_','-')) else '_' for ch in str(target_id))
        out_path = os.path.join(base_dir, f"{safe_id}_originality.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "target_patent_id": target_id,
                    "originality_score": originality,
                    "statistics": stats,
                    "cpc_distribution": dist,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        out["originality_output_path"] = out_path  # type: ignore
        print(f"💾 Originality results saved: {out_path}")
    except Exception as e:
        out["error"] = f"Failed to write originality JSON: {e}"  # type: ignore
        print(f"Warn: Failed to save results: {e}")

    return out


__all__ = ["patent_originality_node", "OriginalityState"]



