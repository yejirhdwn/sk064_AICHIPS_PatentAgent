"""
Sustainability Agent 테스트 스크립트 (LLM Judge 버전)
- 프로젝트 루트에서 실행
- suitability_agent_v2_llm_judge.py 사용
"""

import json
import sys
from pathlib import Path

# agents 폴더를 Python 경로에 추가
project_root = Path(__file__).parent
agents_path = project_root / "agents"
sys.path.insert(0, str(agents_path))

try:
    from suitability_agent_v2_llm_judge import SustainabilityScoreAgent
    print("✅ Using LLM Judge version (v2)")
except ImportError:
    print("⚠️ v2 not found, trying v1...")
    from suitability_agent import SustainabilityScoreAgent
    print("✅ Using calculation-only version (v1)")


def test_direct_input(use_llm: bool = True):
    """방법 1: 직접 점수 입력하여 테스트"""
    print("\n" + "="*80)
    print("테스트 방법 1: 직접 점수 입력")
    print("="*80)
    
    agent = SustainabilityScoreAgent(
        tech_name="NPU",
        use_llm_judge=use_llm
    )
    
    # 예시 점수
    result = agent.calculate_sustainability(
        originality_score=0.92,  # 독창성 매우 높음
        market_score=0.88,        # 시장성 우수
        market_size_score=0.35,   # 세부 점수 (옵션)
        growth_potential_score=0.28,
        commercialization_readiness=0.25
    )
    
    return result


def test_from_saved_files(use_llm: bool = True):
    """방법 2: 저장된 결과 파일에서 점수 로드"""
    print("\n" + "="*80)
    print("테스트 방법 2: 저장된 결과 파일 사용")
    print("="*80)
    
    # 파일 경로 설정
    project_root = Path(__file__).parent
    originality_dir = project_root / "output" / "originality"
    market_dir = project_root / "output" / "market_evaluation"
    
    # 최신 파일 찾기
    originality_files = list(originality_dir.glob("*_originality.json")) if originality_dir.exists() else []
    market_files = list(market_dir.glob("market_eval_*.json")) if market_dir.exists() else []
    
    if not originality_files:
        print(f"❌ Originality 결과 파일을 찾을 수 없습니다.")
        print(f"   경로: {originality_dir}")
        print(f"   먼저 patent_originality_agent.py를 실행하세요.")
        return None
    
    if not market_files:
        print(f"❌ Market 결과 파일을 찾을 수 없습니다.")
        print(f"   경로: {market_dir}")
        print(f"   먼저 market_size_growth_agent.py를 실행하세요.")
        return None
    
    # 최신 파일 선택
    originality_file = max(originality_files, key=lambda p: p.stat().st_mtime)
    market_file = max(market_files, key=lambda p: p.stat().st_mtime)
    
    print(f"\n📂 Loading files:")
    print(f"   Originality: {originality_file.name}")
    print(f"   Market: {market_file.name}")
    
    # 파일 로드
    with open(originality_file, 'r', encoding='utf-8') as f:
        originality_data = json.load(f)
    
    with open(market_file, 'r', encoding='utf-8') as f:
        market_data = json.load(f)
    
    # 점수 추출
    originality_score = originality_data.get("originality_score", 0.0)
    market_score = market_data.get("market_score", 0.0)
    tech_name = market_data.get("tech_name", "Unknown")
    
    print(f"\n📊 Extracted Scores:")
    print(f"   Tech Name: {tech_name}")
    print(f"   Originality: {originality_score:.4f}")
    print(f"   Market: {market_score:.4f}")
    
    # Agent 실행
    agent = SustainabilityScoreAgent(
        tech_name=tech_name,
        use_llm_judge=use_llm
    )
    
    result = agent.calculate_sustainability(
        originality_score=originality_score,
        market_score=market_score,
        market_size_score=market_data.get("market_size_score"),
        growth_potential_score=market_data.get("growth_potential_score"),
        commercialization_readiness=market_data.get("commercialization_readiness")
    )
    
    return result


def test_various_scenarios(use_llm: bool = True):
    """방법 3: 다양한 시나리오 테스트"""
    print("\n" + "="*80)
    print("테스트 방법 3: 다양한 시나리오")
    print("="*80)
    
    scenarios = [
        {
            "name": "S등급 - 혁신적 기술",
            "tech_name": "Quantum_AI",
            "originality": 0.95,
            "market": 0.90
        },
        {
            "name": "A등급 - 우수한 기술",
            "tech_name": "Edge_AI",
            "originality": 0.88,
            "market": 0.75
        },
        {
            "name": "B등급 - 양호한 기술",
            "tech_name": "IoT_Sensor",
            "originality": 0.82,
            "market": 0.60
        },
        {
            "name": "애매한 케이스 - 고독창성 저시장",
            "tech_name": "Niche_Tech",
            "originality": 0.92,
            "market": 0.35
        },
    ]
    
    results = []
    for scenario in scenarios:
        print(f"\n{'─'*80}")
        print(f"시나리오: {scenario['name']}")
        print(f"{'─'*80}")
        
        agent = SustainabilityScoreAgent(
            tech_name=scenario["tech_name"],
            use_llm_judge=use_llm
        )
        
        result = agent.calculate_sustainability(
            originality_score=scenario["originality"],
            market_score=scenario["market"]
        )
        results.append(result)
    
    # 결과 요약
    print("\n" + "="*80)
    print("📊 전체 시나리오 결과 요약")
    print("="*80)
    
    if use_llm:
        print(f"{'Tech Name':<20} {'Orig':>6} {'Market':>6} {'Calc':>5} {'LLM':>5} {'Invest':>10} {'Risk':>8}")
        print("─"*80)
        for r in results:
            llm_eval = r.get('llm_evaluation', {})
            calc_grade = r.get('calculated_grade', 'N/A')
            llm_grade = r.get('final_grade', calc_grade)
            invest = llm_eval.get('investment_recommendation', 'N/A')[:8]
            risk = llm_eval.get('risk_level', 'N/A')
            
            print(f"{r['tech_name']:<20} {r['originality_score']:>6.2f} {r['market_score']:>6.2f} "
                  f"{calc_grade:>5} {llm_grade:>5} {invest:>10} {risk:>8}")
    else:
        print(f"{'Tech Name':<20} {'Orig':>6} {'Market':>6} {'Score':>7} {'Grade':>6}")
        print("─"*80)
        for r in results:
            print(f"{r['tech_name']:<20} {r['originality_score']:>6.2f} {r['market_score']:>6.2f} "
                  f"{r['sustainability_score']:>7.4f} {r['sustainability_grade']:>6}")
    
    return results


def test_llm_vs_calculation():
    """방법 4: LLM vs 수식 비교"""
    print("\n" + "="*80)
    print("테스트 방법 4: LLM Judge vs 수식 비교")
    print("="*80)
    
    # 애매한 케이스들
    test_cases = [
        {"name": "고독창성-저시장", "orig": 0.92, "market": 0.35},
        {"name": "저독창성-고시장", "orig": 0.76, "market": 0.88},
        {"name": "중간-중간", "orig": 0.82, "market": 0.65},
    ]
    
    print(f"\n{'케이스':<20} {'수식등급':>10} {'LLM등급':>10} {'차이':>6} {'LLM추천':>12}")
    print("─"*80)
    
    for case in test_cases:
        # 수식만
        agent_calc = SustainabilityScoreAgent(
            tech_name=case["name"],
            use_llm_judge=False
        )
        result_calc = agent_calc.calculate_sustainability(
            originality_score=case["orig"],
            market_score=case["market"]
        )
        
        # LLM Judge
        agent_llm = SustainabilityScoreAgent(
            tech_name=case["name"],
            use_llm_judge=True
        )
        result_llm = agent_llm.calculate_sustainability(
            originality_score=case["orig"],
            market_score=case["market"]
        )
        
        calc_grade = result_calc["sustainability_grade"]
        llm_grade = result_llm["final_grade"]
        diff = "동일" if calc_grade == llm_grade else "변경"
        llm_rec = result_llm.get("llm_evaluation", {}).get("investment_recommendation", "N/A")
        
        print(f"{case['name']:<20} {calc_grade:>10} {llm_grade:>10} {diff:>6} {llm_rec:>12}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sustainability Agent 테스트 (LLM Judge)")
    parser.add_argument(
        "--mode", 
        choices=["direct", "files", "scenarios", "compare", "all"],
        default="direct",
        help="테스트 모드 선택 (기본: direct)"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="LLM Judge 비활성화 (수식만 사용)"
    )
    args = parser.parse_args()
    
    use_llm = not args.no_llm
    
    if use_llm:
        print("\n🤖 LLM Judge 활성화")
    else:
        print("\n📊 수식 계산만 사용 (LLM 비활성화)")
    
    try:
        if args.mode in ["direct", "all"]:
            print("\n🎯 실행 중: 직접 점수 입력 테스트")
            test_direct_input(use_llm=use_llm)
        
        if args.mode in ["files", "all"]:
            print("\n🎯 실행 중: 저장된 파일 테스트")
            test_from_saved_files(use_llm=use_llm)
        
        if args.mode in ["scenarios", "all"]:
            print("\n🎯 실행 중: 시나리오 테스트")
            test_various_scenarios(use_llm=use_llm)
        
        if args.mode in ["compare", "all"]:
            print("\n🎯 실행 중: LLM vs 수식 비교")
            test_llm_vs_calculation()
        
        print("\n" + "="*80)
        print("✅ 테스트 완료!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()