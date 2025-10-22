from __future__ import annotations

import os
import json
import time
import requests
from collections import Counter
from typing import Any, Dict, List, Optional, TypedDict
from dotenv import load_dotenv

try:
    from openai import OpenAI
    _OPENAI_OK = True
except Exception:
    _OPENAI_OK = False

try:
    from state.originality_state import OriginalityState
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

# ========== 🔧 API 호출 제한 설정 ==========
MAX_CITATIONS = 3           # 인용 특허 개수 (기본: 5 → 3)
TOP_K_CPC = 3              # Top CPC 개수 (기본: 5 → 3)
PATENTS_PER_KEYWORD = 10   # 키워드당 검색 특허 (최소 10 - SerpAPI 요구사항)
MAX_EXPANDED_PATENTS = 15  # 확장 특허 최대 개수 (신규 추가)
MAX_CPC_PER_PATENT = 30    # 특허당 최대 CPC 개수 (편향 방지)

# API 호출 예상: 1 + 3 + 3 + 3 + 15 = 25회 (기존 36회에서 11회 절약)
# ===========================================


def _fetch_patent_details(patent_id: str) -> Optional[Dict[str, Any]]:
    """특허 상세 정보 조회"""
    if not patent_id:
        return None
    
    try:
        r = requests.get(
            BASE_URL,
            params={
                "engine": "google_patents_details",
                "patent_id": patent_id,
                "api_key": SERPAPI_KEY,
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        
        if "error" in data:
            print(f"   ❌ API error for {patent_id}: {data.get('error')}")
            return None
            
        return data
    except Exception as e:
        print(f"   ❌ Failed to fetch {patent_id}: {e}")
        return None


def _normalize_patent_metadata(details: Dict[str, Any]) -> Dict[str, Any]:
    """
    ✅ 특허 메타데이터 추출 및 정규화
    Patent_Scrapper_agent.py와 동일한 필드 저장
    """
    return {
        "title": details.get("title"),
        "abstract": details.get("snippet") or details.get("abstract"),
        "patent_id": details.get("patent_id"),
        "publication_number": details.get("publication_number"),
        "publication_date": details.get("publication_date"),
        "filing_date": details.get("filing_date"),
        "priority_date": details.get("priority_date"),
        "assignee": details.get("assignee"),
        "inventor": details.get("inventor"),
        "link": details.get("patent_link"),
        "pdf": details.get("pdf"),
    }


def _collect_cpc_from_citations(
    patent_id: str, 
    max_refs: int = MAX_CITATIONS
) -> tuple[List[str], List[str], List[Dict[str, Any]]]:
    """
    인용 특허에서 CPC 수집 + 메타데이터 저장
    
    Returns:
        (cpc_codes, citation_ids, citation_metadata)
    """
    print(f"\n{'='*70}")
    print(f"📋 Step 1: Collecting CPC from Citations")
    print(f"{'='*70}")
    print(f"   Target Patent: {patent_id}")
    print(f"   Max Citations: {max_refs} (API 절약 모드)")
    
    details = _fetch_patent_details(patent_id)
    if not details:
        print("   ❌ Failed to fetch patent details")
        return [], [], []

    print(f"   ✅ Patent: {details.get('title', 'N/A')[:60]}...")
    
    patent_citations = details.get("patent_citations")
    if not patent_citations:
        print("   ⚠️ No 'patent_citations' field")
        return [], [], []
    
    citations = patent_citations.get("original", [])[:max_refs]
    if not citations:
        print("   ⚠️ No backward citations")
        return [], [], []
    
    print(f"   ✅ Found {len(citations)} citations\n")

    all_cpc_codes = []
    citation_ids = []
    citation_metadata = []  # ✅ 메타데이터 저장

    for i, citation in enumerate(citations, start=1):
        cid = citation.get("patent_id")
        if not cid:
            continue
        
        citation_ids.append(cid)
        print(f"   [{i}/{len(citations)}] {cid}")
        
        cit_details = _fetch_patent_details(cid)
        if not cit_details:
            continue
        
        # ✅ 메타데이터 저장
        citation_metadata.append(_normalize_patent_metadata(cit_details))
        
        # CPC 코드 추출 (최대 개수 제한)
        classifications = cit_details.get("classifications", []) or []
        cpc_count = 0
        cpc_collected = 0
        for cls in classifications:
            if cls.get("is_cpc") and cls.get("code"):
                cpc_count += 1
                # ✅ 최대 개수 제한
                if cpc_collected < MAX_CPC_PER_PATENT:
                    all_cpc_codes.append(cls["code"])
                    cpc_collected += 1
        
        if cpc_count > 0:
            if cpc_count > MAX_CPC_PER_PATENT:
                print(f"       ✅ {cpc_collected}/{cpc_count} CPC codes (limited)")
            else:
                print(f"       ✅ {cpc_count} CPC codes")
        
        time.sleep(0.3)

    print(f"\n{'='*70}")
    print(f"   📊 Summary:")
    print(f"      • Total CPC: {len(all_cpc_codes)}")
    print(f"      • Unique CPC: {len(set(all_cpc_codes))}")
    print(f"      • Citations processed: {len(citation_ids)}")
    print(f"      • Metadata saved: {len(citation_metadata)}")
    print(f"{'='*70}\n")
    
    return all_cpc_codes, citation_ids, citation_metadata


def _convert_cpc_to_keywords(cpc_code: str) -> str:
    """CPC → 키워드 변환 (GPT 사용) - Fixed to avoid numbered lists"""
    if not _OPENAI_OK:
        return "semiconductor device technology"
    
    try:
        import re
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""CPC code: {cpc_code}

Generate ONE single line of 2-4 space-separated technical keywords for patent search.
DO NOT use numbering (1., 2., etc.). DO NOT use line breaks.
Output format: just the keywords in one line, space-separated.

Examples:
H01L25/065 → chip stacking TSV interposer
G06F12/0802 → cache coherency protocol
G06N3/045 → neural network training backpropagation

{cpc_code} →"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0
        )
        
        keywords = response.choices[0].message.content.strip()
        
        # Clean up arrows and CPC code
        for sep in ["→", "->", cpc_code]:
            keywords = keywords.replace(sep, "").strip()
        
        # ✅ Remove numbering if GPT still added it
        keywords = re.sub(r"^\d+[\.\)]\s*", "", keywords)
        
        # ✅ If multi-line, take only first line
        if "\n" in keywords:
            keywords = keywords.split("\n")[0].strip()
        
        # ✅ Remove any numbering in the middle
        keywords = re.sub(r"\s+\d+[\.\)]\s+", " ", keywords)
        
        # ✅ Final cleanup: remove extra spaces
        keywords = " ".join(keywords.split())
        
        return keywords
        
    except Exception as e:
        print(f"   ⚠️ Keyword conversion failed: {e}")
        return "semiconductor device technology"


def _search_patents_with_keywords(
    keyword: str, 
    num: int = PATENTS_PER_KEYWORD, 
    country: str = "US"
) -> List[str]:
    """키워드로 특허 검색 - Simplified query to avoid 400 errors"""
    try:
        # ✅ Simple query - SerpAPI doesn't like complex OR operators
        # Just use the keywords with "patent" or "method" suffix
        # Example: "image recognition feature extraction" → "image recognition feature extraction patent"
        enhanced_query = f'{keyword} patent'
        
        print(f"       Query: {enhanced_query}")
        
        params = {
            "engine": "google_patents",
            "q": enhanced_query,
            "country": country,
            "num": max(10, num),  # ✅ Ensure minimum 10 (SerpAPI requirement)
            "api_key": SERPAPI_KEY,
        }
        
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        if "error" in data:
            print(f"       ❌ API Error: {data.get('error')}")
            return []
        
        results = data.get("organic_results", []) or []
        patent_ids = [item.get("patent_id") for item in results if item.get("patent_id")]
        
        print(f"       ✅ Found {len(patent_ids)} patents")
        return patent_ids
        
    except Exception as e:
        print(f"       ❌ Search failed: {e}")
        return []


def _collect_cpc_from_patents(
    patent_ids: List[str]
) -> tuple[List[str], List[Dict[str, Any]]]:
    """
    확장 특허에서 CPC 수집 + 메타데이터 저장
    
    Returns:
        (cpc_codes, patents_metadata)
    """
    print(f"\n{'='*70}")
    print(f"📋 Step 3: Collecting CPC from Expanded Patents")
    print(f"{'='*70}")
    print(f"   Total patents: {len(patent_ids)}\n")
    
    all_cpc_codes = []
    patents_metadata = []  # ✅ 메타데이터 저장
    
    for i, pid in enumerate(patent_ids, start=1):
        print(f"   [{i}/{len(patent_ids)}] {pid}")
        
        details = _fetch_patent_details(pid)
        if not details:
            continue
        
        # ✅ 메타데이터 저장
        patents_metadata.append(_normalize_patent_metadata(details))
        
        # CPC 수집 (최대 개수 제한)
        classifications = details.get("classifications", []) or []
        cpc_count = 0
        cpc_collected = 0
        for cls in classifications:
            if cls.get("is_cpc") and cls.get("code"):
                cpc_count += 1
                # ✅ 최대 개수 제한
                if cpc_collected < MAX_CPC_PER_PATENT:
                    all_cpc_codes.append(cls["code"])
                    cpc_collected += 1
        
        if cpc_count > 0:
            if cpc_count > MAX_CPC_PER_PATENT:
                print(f"       ✅ {cpc_collected}/{cpc_count} CPC codes (limited)")
            else:
                print(f"       ✅ {cpc_count} CPC codes")
        
        time.sleep(0.3)
    
    print(f"\n{'='*70}")
    print(f"   📊 Summary:")
    print(f"      • Successful: {len(patents_metadata)}/{len(patent_ids)}")
    print(f"      • Total CPC: {len(all_cpc_codes)}")
    print(f"      • Unique CPC: {len(set(all_cpc_codes))}")
    print(f"      • Metadata saved: {len(patents_metadata)}")
    print(f"{'='*70}\n")
    
    return all_cpc_codes, patents_metadata


def _calc_originality_index(cpc_codes: List[str]) -> float:
    """Herfindahl Index 기반 독창성 계산"""
    if not cpc_codes:
        return 0.0
    
    counter = Counter(cpc_codes)
    total = sum(counter.values())
    hhi = sum((count / total) ** 2 for count in counter.values())
    
    return 1 - hhi


def patent_originality_node(state: OriginalityState) -> OriginalityState:
    """특허 독창성 분석 Agent (API 호출 최적화 + 메타데이터 저장)"""
    
    print("\n" + "="*70)
    print("🎯 Patent Originality Analysis Agent (Optimized)")
    print("="*70)
    print(f"⚡ API Call Limits:")
    print(f"   • Max Citations: {MAX_CITATIONS}")
    print(f"   • Top K CPC: {TOP_K_CPC}")
    print(f"   • Patents per Keyword: {PATENTS_PER_KEYWORD}")
    print(f"   • Max Expanded Patents: {MAX_EXPANDED_PATENTS}")
    print("="*70)
    
    if not SERPAPI_KEY:
        return {**state, "error": "SERPAPI_KEY not set"}
    
    if state.get("error"):
        return {**state, "error": f"Previous error: {state['error']}"}

    # Target patent
    target_id = (state.get("first_item") or {}).get("patent_id")
    if not target_id and state.get("items"):
        target_id = state["items"][0].get("patent_id")
    
    if not target_id:
        return {**state, "error": "No target patent_id"}

    print(f"🎯 Target: {target_id}\n")

    # Step 1: Citations CPC + metadata
    base_cpc, citation_ids, citation_metadata = _collect_cpc_from_citations(
        target_id, 
        max_refs=MAX_CITATIONS
    )

    if not base_cpc:
        return {
            **state,
            "target_patent_id": target_id,
            "originality_score": 0.0,
            "cpc_distribution": {},
            "statistics": {
                "base_cpc_count": 0,
                "expanded_cpc_count": 0,
                "total_cpc_count": 0,
                "unique_cpc_count": 0,
                "citations_analyzed": 0,
                "patents_expanded": 0,
            },
            "error": "No CPC codes in citations"
        }

    # Step 2: Top-K CPC selection
    print(f"{'='*70}")
    print(f"📋 Step 2: Top-K CPC Selection")
    print(f"{'='*70}")
    
    counter = Counter(base_cpc)
    top_k = [c for c, _ in counter.most_common(TOP_K_CPC)]
    
    print(f"   🔝 Top {len(top_k)} CPC codes:")
    for i, code in enumerate(top_k, 1):
        print(f"      {i}. {code} (count: {counter[code]})")
    print()

    # Step 3: Keyword expansion
    print(f"{'='*70}")
    print(f"📋 Step 2.5: Keyword Expansion")
    print(f"{'='*70}")
    
    expanded_ids: List[str] = []
    seen = {target_id, *citation_ids}
    
    for i, code in enumerate(top_k, 1):
        # ⚠️ 최대 개수 도달 시 중단
        if len(expanded_ids) >= MAX_EXPANDED_PATENTS:
            print(f"\n   ⚠️ Reached max expanded patents ({MAX_EXPANDED_PATENTS})")
            break
        
        print(f"\n   [{i}/{len(top_k)}] CPC: {code}")
        kw = _convert_cpc_to_keywords(code)
        print(f"       Keywords: '{kw}'")
        
        ids = _search_patents_with_keywords(kw, num=PATENTS_PER_KEYWORD)
        print(f"       Found: {len(ids)} patents")
        
        new_count = 0
        for pid in ids:
            if len(expanded_ids) >= MAX_EXPANDED_PATENTS:
                break
            if pid not in seen and pid not in expanded_ids:
                expanded_ids.append(pid)
                seen.add(pid)
                new_count += 1
        
        print(f"       ➕ Added: {new_count}")
        time.sleep(0.3)

    print(f"\n{'='*70}")
    print(f"   📊 Total expanded: {len(expanded_ids)}/{MAX_EXPANDED_PATENTS}")
    print(f"{'='*70}\n")

    # Step 4: Expanded patents CPC + metadata
    expanded_cpc, expanded_metadata = _collect_cpc_from_patents(expanded_ids)

    # Step 5: Calculate originality
    print(f"{'='*70}")
    print(f"📊 Step 4: Originality Calculation")
    print(f"{'='*70}")
    
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
        "api_calls_saved": "~11 calls (vs original)",
    }

    if originality >= 0.8:
        interp = "🔥 Highly Original"
    elif originality >= 0.6:
        interp = "✅ Original"
    elif originality >= 0.4:
        interp = "➖ Moderate"
    else:
        interp = "⚠️ Low"

    print(f"\n   🎯 Score: {originality:.4f} - {interp}")
    print(f"\n   📊 Statistics:")
    for key, val in stats.items():
        print(f"      • {key}: {val}")
    
    if len(set(all_cpc)) >= 10:
        print(f"\n   🔝 Top 10 CPC:")
        for i, (code, count) in enumerate(Counter(all_cpc).most_common(10), 1):
            pct = (count / len(all_cpc)) * 100
            print(f"      {i:2d}. {code:15s} {count:3d} ({pct:5.1f}%)")
    
    print(f"{'='*70}\n")

    out: OriginalityState = {**state}
    out.update({
        "target_patent_id": target_id,
        "originality_score": originality,
        "cpc_distribution": dist,
        "statistics": stats,
    })

    # ✅ 메타데이터 포함 JSON 저장
    try:
        base_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "output", 
            "originality"
        )
        os.makedirs(base_dir, exist_ok=True)
        
        safe_id = ''.join(
            ch if (ch.isalnum() or ch in ('_','-')) else '_' 
            for ch in str(target_id)
        )
        out_path = os.path.join(base_dir, f"{safe_id}_originality.json")
        
        output_data = {
            "target_patent_id": target_id,
            "originality_score": originality,
            "statistics": stats,
            "cpc_distribution": dist,
            # ✅ 메타데이터 저장
            "citation_patents": citation_metadata,
            "expanded_patents": expanded_metadata,
        }
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        out["originality_output_path"] = out_path
        print(f"💾 Results saved: {out_path}")
        print(f"   • Citations metadata: {len(citation_metadata)} patents")
        print(f"   • Expanded metadata: {len(expanded_metadata)} patents")
        
    except Exception as e:
        out["error"] = f"Save failed: {e}"
        print(f"⚠️ Save failed: {e}")

    return out


__all__ = ["patent_originality_node", "OriginalityState"]