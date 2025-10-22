# =========================================================
# patent_originality_pipeline.py
# ---------------------------------------------------------
# 기존 검색 엔진 + 독창성 분석 통합 파이프라인
# =========================================================

import os, json, requests, time
from typing import Dict, List, Any, Optional
from collections import Counter
from dotenv import load_dotenv

# ✅ OpenAI import 추가
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ openai 모듈이 설치되지 않았습니다. 'pip install openai' 실행하세요.")

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
BASE_URL = "https://serpapi.com/search.json"

if not SERPAPI_KEY:
    raise ValueError("❌ SERPAPI_KEY 환경변수가 설정되지 않았습니다.")


# ========== 유틸리티 함수 ==========

def clamp_num(num: int) -> int:
    """검색 결과 개수 제한 (1-100)"""
    return max(1, min(num, 100))

def clamp_page(page: int) -> int:
    """페이지 번호 제한 (1+)"""
    return max(1, page)

def prepared_url(params: Dict[str, Any], hide_key: bool = True) -> str:
    """디버깅용 URL 생성"""
    import urllib.parse
    p = params.copy()
    if hide_key and "api_key" in p:
        p["api_key"] = "***"
    return f"{BASE_URL}?{urllib.parse.urlencode(p)}"

def extract_cpc_prefix(code: str) -> str:
    """CPC 코드 앞부분만 추출 (H01L25/0657 → H01L25)"""
    return code.split("/")[0] if code and "/" in code else code


def convert_cpc_to_keywords_gpt(cpc_code: str) -> str:
    """
    ✅ GPT-4o-mini로 CPC 코드 → 검색 키워드 변환
    """
    if not OPENAI_AVAILABLE:
        print(f"       ⚠️ OpenAI 모듈 없음. Fallback 사용")
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
        
        # ✅ 화살표나 CPC 코드가 포함되어 있으면 제거
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
        print(f"       ⚠️ GPT 실패: {e}")
        return "semiconductor device technology"


# ========== 1단계: 기본 특허 검색 ==========

def normalize_item(it: Dict[str, Any]) -> Dict[str, Any]:
    """organic_results를 표준 필드로 변환"""
    return {
        "title": it.get("title"),
        "abstract": it.get("snippet"),  # 짧은 요약
        "patent_id": it.get("patent_id"),
        "publication_number": it.get("publication_number"),
        "publication_date": it.get("publication_date"),
        "filing_date": it.get("filing_date"),
        "priority_date": it.get("priority_date"),
        "assignee": it.get("assignee"),
        "inventor": it.get("inventor"),
        "link": it.get("patent_link"),
        "pdf": it.get("pdf"),
    }


def search_google_patents(
    query: str,
    num: int = 10,
    page: int = 1,
    country: Optional[str] = None,
    language: Optional[str] = None,
    status: Optional[str] = None,
    ptype: Optional[str] = "PATENT",
) -> Dict[str, Any]:
    """
    Google Patents 검색 (google_patents 엔진)
    기본 정보만 가져옴 (snippet 수준)
    """
    if not SERPAPI_KEY:
        return {"error": "SERPAPI_KEY not set."}

    params: Dict[str, Any] = {
        "engine": "google_patents",
        "q": query,
        "num": clamp_num(num),
        "page": clamp_page(page),
        "api_key": SERPAPI_KEY,
    }
    if country:  params["country"]  = country
    if language: params["language"] = language
    if status:   params["status"]   = status
    if ptype:    params["type"]     = ptype

    safe_url = prepared_url(params, hide_key=True)

    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"SerpAPI request failed: {e}", "serpapi_url": safe_url}

    data = r.json()
    items = data.get("organic_results", [])
    if not items:
        return {"error": "No patents found.", "serpapi_url": safe_url}

    rows: List[Dict[str, Any]] = [normalize_item(it) for it in items]

    return {
        "success": True,
        "query": query,
        "count": len(rows),
        "patents": rows,
        "serpapi_url": safe_url,
    }


# ========== 2단계: 특허 세부 정보 조회 ==========

def fetch_patent_details(patent_id: str) -> Optional[Dict[str, Any]]:
    """
    google_patents_details 엔진으로 특허 세부정보 조회
    - 풀 초록
    - 인용 특허 (patent_citations)
    - CPC 분류 (classifications)
    """
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
            print(f"⚠️ API 에러 ({patent_id}): {data.get('error')}")
            return None
            
        return data
    except Exception as e:
        print(f"⚠️ {patent_id} 조회 실패: {e}")
        return None


def enrich_patent_with_full_abstract(patent: Dict[str, Any]) -> Dict[str, Any]:
    """
    특허 기본 정보에 풀 초록 추가
    ⚠️ 1회 API 호출 (크레딧 소모)
    """
    patent_id = patent.get("patent_id")
    if not patent_id:
        return patent
    
    details = fetch_patent_details(patent_id)
    if details:
        # 풀 초록이 있으면 업데이트
        full_abstract = details.get("abstract") or details.get("description")
        if full_abstract:
            patent["abstract_full"] = full_abstract
    
    return patent


# ========== 3단계: 인용 특허 CPC 수집 ==========

def collect_cpc_from_citations(patent_id: str, max_refs: int = 5) -> tuple[List[str], List[str]]:
    """
    특정 특허의 backward citations에서 CPC 코드 수집
    
    Returns:
        (cpc_codes, citation_ids): CPC 코드 리스트, 인용 특허 ID 리스트
    """
    print(f"\n📚 Step: 인용 특허에서 CPC 수집 ({patent_id})")
    
    details = fetch_patent_details(patent_id)
    if not details:
        print("❌ 특허 조회 실패")
        return [], []

    # citations 추출
    patent_citations = details.get("patent_citations")
    if not patent_citations:
        print("⚠️ 인용 정보 없음")
        return [], []
    
    citations = patent_citations.get("original", [])[:max_refs]
    if not citations:
        print("⚠️ backward citation 없음")
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
        cit_details = fetch_patent_details(cid)
        if not cit_details:
            continue
        
        # CPC 코드 추출
        classifications = cit_details.get("classifications", []) or []
        cpc_count = 0
        for cls in classifications:
            if cls.get("is_cpc") and cls.get("code"):
                all_cpc_codes.append(cls["code"])
                cpc_count += 1
        
        print(f"       → CPC {cpc_count}개 수집")
        time.sleep(0.3)  # API 부하 방지

    print(f"\n✅ CPC 수집 완료: 총 {len(all_cpc_codes)}개 (고유 {len(set(all_cpc_codes))}개)\n")
    return all_cpc_codes, citation_ids


# ========== 4단계: CPC별 대표 특허 확장 검색 ==========

def expand_by_top_cpc(
    cpc_codes: List[str],
    max_cpc_refs: int = 2,
    unique_cpc_limit: int = 5,
    exclude_ids: Optional[set] = None,
    country: str = "US",
    use_llm: bool = False,  # ✅ LLM 사용 여부
) -> List[str]:
    """
    상위 빈도 CPC 코드로 대표 특허 검색 (google_patents 엔진)
    
    Args:
        cpc_codes: 수집된 CPC 코드 리스트
        max_cpc_refs: CPC당 검색할 특허 개수
        unique_cpc_limit: 상위 몇 개 CPC만 사용할지
        exclude_ids: 제외할 특허 ID 집합
        country: 국가 코드
    
    Returns:
        확장 검색된 특허 ID 리스트
    """
    exclude_ids = exclude_ids or set()
    
    # CPC 빈도 계산
    counter = Counter(cpc_codes)
    top_cpc = [c for c, _ in counter.most_common(unique_cpc_limit)]
    
    print(f"🔁 Step: CPC별 대표 특허 확장 검색")
    print(f"   상위 {len(top_cpc)}개 CPC 사용\n")
    
    expanded_patent_ids = []
    
    for idx, cpc_code in enumerate(top_cpc, start=1):
        freq = counter[cpc_code]
        
        print(f"   [{idx}/{len(top_cpc)}] {cpc_code} (빈도: {freq})")
        
        # ✅ GPT로 CPC → 키워드 변환
        if use_llm:
            search_term = convert_cpc_to_keywords_gpt(cpc_code)
        else:
            # Fallback: 간단 매핑
            cpc_prefix = extract_cpc_prefix(cpc_code)
            if cpc_prefix.startswith("H01L"):
                search_term = "semiconductor device package"
            elif cpc_prefix.startswith("G06F"):
                search_term = "computing processor"
            elif cpc_prefix.startswith("G11C"):
                search_term = "memory storage"
            else:
                search_term = "semiconductor technology"
            print(f"       룰 기반: {search_term}")
        
        
        print(f"       디버깅: 검색 쿼리 = '{search_term}'")
        
        try:
            params = {
                "engine": "google_patents",
                "q": search_term,
                "country": country,
                "num": max(10, max_cpc_refs * 2),  # ✅ 최소 10 (SerpAPI 요구사항)
                "api_key": SERPAPI_KEY,
            }
            
            # 디버깅: 실제 요청 URL 출력
            import urllib.parse
            debug_url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
            print(f"       요청 URL: {debug_url[:150]}...")
            
            r = requests.get(BASE_URL, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            
            if "error" in data:
                print(f"       ⚠️ API 에러: {data.get('error')}")
                print(f"       응답: {json.dumps(data, indent=2)}\n")
                continue
            
            results = data.get("organic_results", []) or []
            
            # 중복 제외하며 추가
            added = 0
            for item in results:
                pid = item.get("patent_id")
                if pid and pid not in exclude_ids and pid not in expanded_patent_ids:
                    expanded_patent_ids.append(pid)
                    added += 1
                    if added >= max_cpc_refs:
                        break
            
            print(f"       → {added}개 특허 추가\n")
            time.sleep(0.3)
            
        except Exception as e:
            print(f"       ⚠️ 검색 실패: {str(e)[:100]}")
            # 400 에러면 응답 본문 확인
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"       에러 상세: {error_data}\n")
                except:
                    print(f"       응답 텍스트: {e.response.text[:200]}\n")
    
    print(f"✅ 확장 검색 완료: 총 {len(expanded_patent_ids)}개 특허\n")
    return expanded_patent_ids


# ========== 5단계: 확장 특허 CPC 수집 ==========

def collect_cpc_from_patents(patent_ids: List[str]) -> List[str]:
    """
    특허 ID 리스트에서 CPC 코드 수집 (google_patents_details 반복 호출)
    """
    print(f"📊 Step: 확장 특허 {len(patent_ids)}개의 CPC 수집\n")
    
    all_cpc_codes = []
    
    for i, pid in enumerate(patent_ids, start=1):
        print(f"   [{i}/{len(patent_ids)}] {pid}")
        
        details = fetch_patent_details(pid)
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
    
    print(f"\n✅ 확장 CPC 수집 완료: {len(all_cpc_codes)}개\n")
    return all_cpc_codes


# ========== 6단계: 독창성 점수 계산 ==========

def calculate_originality_index(cpc_codes: List[str]) -> float:
    """
    Originality Index = 1 - Σ(p_i^2)
    
    Args:
        cpc_codes: CPC 코드 리스트
    
    Returns:
        독창성 점수 (0~1, 높을수록 다양함)
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


# ========== 통합 파이프라인 ==========

def analyze_patent_originality(
    query: str,
    country: str = "US",
    max_backward_refs: int = 5,
    max_cpc_refs: int = 2,
    cpc_top_k: int = 5,
    use_llm_for_keywords: bool = False,  # ✅ LLM 사용 여부
) -> Dict[str, Any]:
    """
    특허 검색부터 독창성 분석까지 전체 파이프라인
    
    Steps:
        1. google_patents 검색 (기본 정보)
        2. 첫 번째 특허의 google_patents_details 조회
        3. backward citations의 CPC 수집 (details 반복)
        4. 상위 CPC로 대표 특허 검색 (google_patents)
        5. 확장 특허의 CPC 수집 (details 반복)
        6. 독창성 점수 계산
    """
    
    print("="*60)
    print("🔍 특허 독창성 분석 파이프라인 시작")
    print("="*60)
    
    # Step 1: 기본 검색
    print(f"\n📝 Step 1: 특허 검색 (query: {query})\n")
    search_result = search_google_patents(query, num=10, country=country)
    
    if not search_result.get("success"):
        return {"error": "검색 실패", "details": search_result}
    
    patents = search_result["patents"]
    target_patent = patents[0]  # 첫 번째 특허 선택
    
    print(f"✅ 대상 특허 선택:")
    print(f"   제목: {target_patent['title']}")
    print(f"   ID: {target_patent['patent_id']}")
    print(f"   링크: {target_patent['link']}\n")
    
    target_id = target_patent["patent_id"]
    
    # Step 2-3: 인용 특허 CPC 수집
    base_cpc, citation_ids = collect_cpc_from_citations(
        target_id, 
        max_refs=max_backward_refs
    )
    
    if not base_cpc:
        return {
            "error": "CPC 코드 없음",
            "target_patent": target_patent,
            "originality_score": 0.0
        }
    
    # Step 4: CPC별 대표 특허 확장 검색
    exclude_set = {target_id} | set(citation_ids)
    expanded_ids = expand_by_top_cpc(
        base_cpc,
        max_cpc_refs=max_cpc_refs,
        unique_cpc_limit=cpc_top_k,
        exclude_ids=exclude_set,
        country=country,
        use_llm=use_llm_for_keywords,  # ✅ LLM 사용
    )
    
    # Step 5: 확장 특허 CPC 수집
    expanded_cpc = collect_cpc_from_patents(expanded_ids)
    
    # 전체 CPC 통합
    all_cpc = base_cpc + expanded_cpc
    
    # Step 6: 독창성 계산
    originality = calculate_originality_index(all_cpc)
    
    # 통계 출력
    cpc_counter = Counter(all_cpc)
    
    print("\n" + "="*60)
    print("📊 최종 결과")
    print("="*60)
    print(f"\n🎯 독창성 점수: {originality:.4f}")
    print(f"\n📈 통계:")
    print(f"   - 기본 CPC: {len(base_cpc)}개 (고유 {len(set(base_cpc))}개)")
    print(f"   - 확장 CPC: {len(expanded_cpc)}개 (고유 {len(set(expanded_cpc))}개)")
    print(f"   - 전체 CPC: {len(all_cpc)}개 (고유 {len(set(all_cpc))}개)")
    
    print(f"\n🔹 상위 CPC 분포 (Top 15):")
    for code, count in cpc_counter.most_common(15):
        percentage = (count / len(all_cpc)) * 100
        print(f"   {code}: {count}회 ({percentage:.1f}%)")
    
    print("="*60)
    
    # 결과 반환
    return {
        "success": True,
        "target_patent": target_patent,
        "originality_score": originality,
        "statistics": {
            "base_cpc_count": len(base_cpc),
            "expanded_cpc_count": len(expanded_cpc),
            "total_cpc_count": len(all_cpc),
            "unique_cpc_count": len(set(all_cpc)),
            "citations_analyzed": len(citation_ids),
            "patents_expanded": len(expanded_ids),
        },
        "cpc_distribution": dict(cpc_counter.most_common(20)),
        "query": query,
        "params": {
            "country": country,
            "max_backward_refs": max_backward_refs,
            "max_cpc_refs": max_cpc_refs,
            "cpc_top_k": cpc_top_k,
        }
    }


# ========== 실행 예시 ==========

if __name__ == "__main__":
    # HBM 특허 독창성 분석
    # ✅ use_llm_for_keywords=True 로 설정하면 GPT-4o-mini 사용
    # ✅ .env에 OPENAI_API_KEY 필요
    
    result = analyze_patent_originality(
        query='(HBM OR "High Bandwidth Memory") (AI OR accelerator OR processor)',
        country="US",
        max_backward_refs=5,
        max_cpc_refs=2,
        cpc_top_k=5,
        use_llm_for_keywords=True,  # ✅ GPT 사용
    )
    
    # 결과 저장
    if result.get("success"):
        output_file = "patent_originality_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n📁 결과 저장 완료 → {output_file}")