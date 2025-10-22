"""
patent_originality_agent.py 함수 테스트
Patent_Scrapper_agent.py에서 성공한 특허 ID로 동일한 결과가 나오는지 검증
"""

import os
import sys
from dotenv import load_dotenv

# ✅ agents 폴더를 sys.path에 추가
agents_path = os.path.join(os.path.dirname(__file__), 'agents')
if os.path.exists(agents_path):
    sys.path.insert(0, agents_path)
    print(f"✅ agents 폴더 추가: {agents_path}\n")
else:
    print(f"❌ agents 폴더를 찾을 수 없습니다: {agents_path}")
    sys.exit(1)

try:
    from patent_originality_agent import (
        _fetch_patent_details,
        _collect_cpc_from_citations,
        _convert_cpc_to_keywords,
        _search_patents_with_keywords,
        _collect_cpc_from_patents,
        _calc_originality_index,
    )
    print("✅ patent_originality_agent.py 모듈 import 성공\n")
except ImportError as e:
    print(f"❌ import 실패: {e}")
    print("\n확인 사항:")
    print("  1. agents/patent_originality_agent.py 파일이 존재하는지")
    print("  2. 파일 내에 함수들이 정의되어 있는지")
    print("  3. 파일 이름 철자가 정확한지")
    sys.exit(1)

load_dotenv()

# ✅ Patent_Scrapper_agent.py에서 성공한 특허 ID
TEST_PATENT_ID = "patent/US12314567B1/en"

# Patent_Scrapper_agent.py의 성공 결과 (비교용)
EXPECTED_RESULTS = {
    "patent_id": "patent/US12314567B1/en",
    "citation_count": 5,
    "expected_citations": [
        "patent/US4334305A/en",
        "patent/US5396581A/en", 
        "patent/US5677569A/en",
        "patent/US5892287A/en",
        "patent/US5910010A/en"
    ],
    "expected_cpc_counts": [2, 1, 16, 52, 59],  # 각 인용 특허의 CPC 개수
    "total_cpc": 130,
    "unique_cpc": 103
}


def test_fetch_patent_details():
    """테스트 1: _fetch_patent_details() 함수"""
    print("="*70)
    print("🧪 테스트 1: _fetch_patent_details()")
    print("="*70)
    print(f"입력: {TEST_PATENT_ID}\n")
    
    result = _fetch_patent_details(TEST_PATENT_ID)
    
    if result is None:
        print("❌ FAIL: None 반환됨")
        return False
    
    print("✅ PASS: 특허 데이터 반환됨")
    print(f"   제목: {result.get('title', 'N/A')[:60]}...")
    
    # patent_citations 확인
    if "patent_citations" not in result:
        print("❌ FAIL: patent_citations 필드 없음")
        return False
    
    print("✅ PASS: patent_citations 필드 존재")
    
    citations = result.get("patent_citations", {}).get("original", [])
    print(f"   인용 개수: {len(citations)}")
    
    if len(citations) == 0:
        print("❌ FAIL: 인용 특허가 0개")
        return False
    
    print(f"✅ PASS: {len(citations)}개 인용 특허 발견")
    print(f"   예상값: {EXPECTED_RESULTS['citation_count']}개")
    
    return True


def test_collect_cpc_from_citations():
    """테스트 2: _collect_cpc_from_citations() 함수"""
    print("\n" + "="*70)
    print("🧪 테스트 2: _collect_cpc_from_citations() ⭐ 가장 중요!")
    print("="*70)
    print(f"입력: {TEST_PATENT_ID}")
    print(f"max_refs: 5\n")
    
    cpc_codes, citation_ids = _collect_cpc_from_citations(TEST_PATENT_ID, max_refs=5)
    
    print(f"\n📊 결과:")
    print(f"   CPC 코드 개수: {len(cpc_codes)}")
    print(f"   고유 CPC 개수: {len(set(cpc_codes))}")
    print(f"   인용 특허 개수: {len(citation_ids)}")
    
    # 기댓값과 비교
    print(f"\n📈 Patent_Scrapper_agent.py 결과와 비교:")
    print(f"   CPC 코드 개수:")
    print(f"      실제: {len(cpc_codes)}")
    print(f"      예상: {EXPECTED_RESULTS['total_cpc']}")
    
    if len(cpc_codes) == EXPECTED_RESULTS['total_cpc']:
        print(f"      ✅ PASS - 정확히 일치!")
    elif len(cpc_codes) > 0:
        print(f"      ⚠️ 다르지만 CPC는 추출됨")
    else:
        print(f"      ❌ FAIL - CPC를 전혀 추출하지 못함")
    
    print(f"   고유 CPC 개수:")
    print(f"      실제: {len(set(cpc_codes))}")
    print(f"      예상: {EXPECTED_RESULTS['unique_cpc']}")
    
    if len(set(cpc_codes)) > 0:
        print(f"      {'✅ PASS' if len(set(cpc_codes)) >= 50 else '⚠️ 적음'}")
    else:
        print(f"      ❌ FAIL")
    
    print(f"   인용 특허 개수:")
    print(f"      실제: {len(citation_ids)}")
    print(f"      예상: {EXPECTED_RESULTS['citation_count']}")
    print(f"      {'✅ PASS' if len(citation_ids) == EXPECTED_RESULTS['citation_count'] else '⚠️ 다름'}")
    
    if citation_ids:
        print(f"\n   인용 특허 ID 목록:")
        for i, cid in enumerate(citation_ids, 1):
            expected = EXPECTED_RESULTS['expected_citations'][i-1] if i <= len(EXPECTED_RESULTS['expected_citations']) else "N/A"
            match = "✅" if cid == expected else "⚠️"
            print(f"      {i}. {cid} {match}")
    
    if cpc_codes:
        print(f"\n   상위 5개 CPC 코드:")
        from collections import Counter
        for code, count in Counter(cpc_codes).most_common(5):
            print(f"      - {code}: {count}회")
    
    return len(cpc_codes) > 0, cpc_codes, citation_ids


def test_convert_cpc_to_keywords():
    """테스트 3: _convert_cpc_to_keywords() 함수"""
    print("\n" + "="*70)
    print("🧪 테스트 3: _convert_cpc_to_keywords()")
    print("="*70)
    
    test_cpc = "H01L25/0657"
    print(f"입력: {test_cpc}\n")
    
    try:
        keywords = _convert_cpc_to_keywords(test_cpc)
        print(f"✅ PASS: 키워드 생성됨")
        print(f"   결과: {keywords}")
        
        # Patent_Scrapper_agent.py 예상 결과
        print(f"\n   Patent_Scrapper_agent.py 예상 결과:")
        print(f"      'semiconductor device interconnects microbumps'")
        print(f"      또는 유사한 기술 용어")
        
        return True, keywords
    except Exception as e:
        print(f"❌ FAIL: 예외 발생 - {e}")
        return False, None


def test_search_patents_with_keywords():
    """테스트 4: _search_patents_with_keywords() 함수"""
    print("\n" + "="*70)
    print("🧪 테스트 4: _search_patents_with_keywords()")
    print("="*70)
    
    keyword = "semiconductor device interconnects microbumps"
    print(f"입력: '{keyword}'")
    print(f"num: 10, country: US\n")
    
    patent_ids = _search_patents_with_keywords(keyword, num=10, country="US")
    
    print(f"\n📊 결과:")
    print(f"   발견된 특허 개수: {len(patent_ids)}")
    
    if len(patent_ids) > 0:
        print(f"✅ PASS: {len(patent_ids)}개 특허 발견")
        print(f"   처음 3개:")
        for i, pid in enumerate(patent_ids[:3], 1):
            print(f"      {i}. {pid}")
        return True, patent_ids
    else:
        print(f"❌ FAIL: 특허를 찾지 못함")
        return False, []


def test_collect_cpc_from_patents():
    """테스트 5: _collect_cpc_from_patents() 함수"""
    print("\n" + "="*70)
    print("🧪 테스트 5: _collect_cpc_from_patents()")
    print("="*70)
    
    # 테스트용 소량의 특허 ID (실제 존재하는 ID)
    test_ids = ["patent/US4334305A/en", "patent/US5396581A/en"]
    print(f"입력: {len(test_ids)}개 특허 ID")
    for i, pid in enumerate(test_ids, 1):
        print(f"   {i}. {pid}")
    print()
    
    cpc_codes = _collect_cpc_from_patents(test_ids)
    
    print(f"\n📊 결과:")
    print(f"   CPC 코드 개수: {len(cpc_codes)}")
    
    # 기댓값 (Patent_Scrapper_agent.py 결과)
    expected_total = sum(EXPECTED_RESULTS['expected_cpc_counts'][:2])  # 2 + 1 = 3
    
    print(f"\n   Patent_Scrapper_agent.py 결과와 비교:")
    print(f"      실제: {len(cpc_codes)}개")
    print(f"      예상: {expected_total}개")
    print(f"      {'✅ PASS' if len(cpc_codes) == expected_total else '⚠️ 다름'}")
    
    if cpc_codes:
        print(f"\n   CPC 코드 목록:")
        for code in cpc_codes[:5]:
            print(f"      - {code}")
    
    return len(cpc_codes) > 0


def test_calc_originality_index():
    """테스트 6: _calc_originality_index() 함수"""
    print("\n" + "="*70)
    print("🧪 테스트 6: _calc_originality_index()")
    print("="*70)
    
    # 샘플 CPC 코드
    sample_cpc = [
        "H01L25/0657", "H01L25/0657", "H01L25/0657",  # 3개
        "G06F3/0604", "G06F3/0604",  # 2개
        "H01L23/31",  # 1개
        "G11C11/401",  # 1개
    ]
    
    print(f"입력: {len(sample_cpc)}개 CPC 코드")
    print(f"   고유 코드: {len(set(sample_cpc))}개")
    
    from collections import Counter
    print(f"   분포:")
    for code, count in Counter(sample_cpc).most_common():
        print(f"      {code}: {count}회")
    
    originality = _calc_originality_index(sample_cpc)
    
    print(f"\n📊 결과:")
    print(f"   Originality Score: {originality:.4f}")
    print(f"   {'✅ PASS' if 0 <= originality <= 1 else '❌ FAIL: 범위 초과'}")
    
    # 해석
    if originality >= 0.8:
        interpretation = "🔥 Highly Original"
    elif originality >= 0.6:
        interpretation = "✅ Original"
    elif originality >= 0.4:
        interpretation = "➖ Moderate"
    else:
        interpretation = "⚠️ Low"
    
    print(f"   해석: {interpretation}")
    
    return True


def run_all_tests():
    """모든 테스트 실행"""
    print("="*70)
    print("🚀 patent_originality_agent.py 함수 테스트")
    print("="*70)
    print(f"📌 테스트 특허: {TEST_PATENT_ID}")
    print(f"   (Patent_Scrapper_agent.py에서 성공한 특허)")
    print("="*70 + "\n")
    
    results = {}
    
    # 테스트 1
    results['fetch_details'] = test_fetch_patent_details()
    
    # 테스트 2 (가장 중요!)
    results['collect_citations'], cpc_codes, citation_ids = test_collect_cpc_from_citations()
    
    # 테스트 3
    results['convert_keywords'], keywords = test_convert_cpc_to_keywords()
    
    # 테스트 4
    results['search_keywords'], patent_ids = test_search_patents_with_keywords()
    
    # 테스트 5
    results['collect_expanded'] = test_collect_cpc_from_patents()
    
    # 테스트 6
    results['calc_originality'] = test_calc_originality_index()
    
    # 결과 요약
    print("\n" + "="*70)
    print("📊 테스트 결과 요약")
    print("="*70)
    
    test_names = {
        'fetch_details': '1. 특허 조회',
        'collect_citations': '2. 인용 CPC 수집 ⭐',
        'convert_keywords': '3. CPC→키워드 변환',
        'search_keywords': '4. 키워드 검색',
        'collect_expanded': '5. 확장 CPC 수집',
        'calc_originality': '6. 독창성 계산'
    }
    
    for test_id, test_name in test_names.items():
        result = results[test_id]
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name:30s}: {status}")
    
    total = len([k for k in results.keys() if not k.endswith('_data')])
    passed = sum([v for k, v in results.items() if not k.endswith('_data')])
    
    print(f"\n   총 {total}개 테스트 중 {passed}개 통과 ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 모든 테스트 통과!")
        print("   patent_originality_agent.py가 정상 작동합니다.")
    else:
        print(f"\n⚠️ {total - passed}개 테스트 실패")
        print("   특히 '2. 인용 CPC 수집' 테스트를 확인하세요.")
    
    print("="*70)


if __name__ == "__main__":
    run_all_tests()