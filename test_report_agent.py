"""
PDF Report Agent 테스트 (ReportLab 기반)
"""
from dotenv import load_dotenv
load_dotenv()

import json
import sys
import os
import subprocess
from pathlib import Path

# API 키 확인
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("\n❌ OPENAI_API_KEY not found!")
    sys.exit(1)

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.report_agent import ReportAgent


def load_suitability_json(json_path: str) -> dict:
    """Suitability 평가 JSON 로드"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_test_patent_result(suitability_data: dict) -> dict:
    """테스트용 특허 결과 생성 (영문 데이터 사용)"""
    # LLM evaluation에서 한글을 영문으로 변환
    llm_eval = suitability_data.get("llm_evaluation", {})
    
    # 한글 -> 영문 변환 매핑
    recommendation_map = {
        "추천": "Recommended",
        "강력 추천": "Strong Buy",
        "보류": "Hold",
        "비추천": "Not Recommended"
    }
    
    risk_map = {
        "낮음": "Low",
        "보통": "Medium",
        "높음": "High"
    }
    
    original_recommendation = llm_eval.get("investment_recommendation", "추천")
    original_risk = llm_eval.get("risk_level", "보통")
    
    return {
        "target_patent_id": "US-TEST-001",
        "first_item": {
            "title": "Neural Processing Unit (NPU) Architecture for Edge AI Computing",
            "patent_id": "US-TEST-001",
            "abstract": "A novel neural processing unit architecture..."
        },
        "originality_score": suitability_data.get("originality_score", 0.993),
        "market_score": suitability_data.get("market_score", 0.75),
        "market_size_score": suitability_data.get("market_size_score", 0.25),
        "growth_potential_score": suitability_data.get("growth_potential_score", 0.25),
        "commercialization_readiness": suitability_data.get("commercialization_readiness", 0.25),
        "final_grade": suitability_data.get("final_grade", "A"),
        "suitability_grade": suitability_data.get("suitability_grade", "A"),
        "suitability_score": suitability_data.get("suitability_score", 0.8728),
        "calculated_score": suitability_data.get("calculated_score", 0.8728),
        "calculated_grade": suitability_data.get("calculated_grade", "S"),
        "application_domains": ["Edge AI", "Mobile Computing", "IoT Devices", "Autonomous Systems"],
        "commercialization_potential": "High",
        "market_rationale": "NPU technology has high demand forecast in the edge AI market",
        "llm_evaluation": {
            "suitability_grade": llm_eval.get("sustainability_grade", "A"),
            "confidence_score": llm_eval.get("confidence_score", 0.85),
            "key_strengths": llm_eval.get("key_strengths", ["Very high technical originality", "Excellent market potential"]),
            "key_weaknesses": llm_eval.get("key_weaknesses", ["Relatively small market size"]),
            "investment_recommendation": recommendation_map.get(original_recommendation, "Recommended"),
            "risk_level": risk_map.get(original_risk, "Medium"),
            "reasoning": llm_eval.get("reasoning", "Excellent technical capabilities with strong market positioning"),
            "strategic_advice": llm_eval.get("strategic_advice", "Focus on niche market penetration strategy")
        },
        "score_breakdown": suitability_data.get("score_breakdown", {}),
        "evaluation_summary": suitability_data.get("evaluation_summary", "")
    }


def main():
    print("\n" + "="*80)
    print("🧪 Report Agent 테스트")
    print("="*80)
    
    # output/suitability 폴더에서 JSON 찾기
    output_dir = project_root / "output" / "suitability"
    
    if not output_dir.exists():
        print(f"\n❌ Directory not found: {output_dir}")
        print(f"ℹ️  Using default test data instead")
        # 기본 테스트 데이터 사용
        suitability_data = {
            "tech_name": "NPU",
            "originality_score": 0.85,
            "market_score": 0.72,
            "final_grade": "A",
            "llm_evaluation": {
                "sustainability_grade": "A",
                "confidence_score": 0.85,
                "investment_recommendation": "Recommended",
                "risk_level": "Medium",
                "reasoning": "Strong technical foundation with good market prospects",
                "strategic_advice": "Focus on partnerships for market entry"
            }
        }
    else:
        json_files = list(output_dir.glob("*.json"))
        
        if not json_files:
            print(f"\n❌ No JSON files in: {output_dir}")
            print(f"ℹ️  Using default test data instead")
            suitability_data = {
                "tech_name": "NPU",
                "originality_score": 0.85,
                "market_score": 0.72,
                "final_grade": "A",
                "llm_evaluation": {
                    "sustainability_grade": "A",
                    "confidence_score": 0.85,
                    "investment_recommendation": "Recommended",
                    "risk_level": "Medium"
                }
            }
        else:
            print(f"\n📂 Found {len(json_files)} JSON file(s)")
            latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
            print(f"📄 Using: {latest_json.name}")
            
            # JSON 로드
            suitability_data = load_suitability_json(latest_json)
            print(f"   Tech: {suitability_data.get('tech_name', 'N/A')}")
            print(f"   Grade: {suitability_data.get('final_grade', 'N/A')}")
            print(f"   Score: {suitability_data.get('suitability_score', 0):.4f}")
    
    # 3개 특허 시뮬레이션
    print("\n" + "="*80)
    print("📊 Creating Test Patent Results (3 patents)")
    print("="*80)
    
    all_patent_results = []
    
    # Patent #1: 실제 데이터 (A등급)
    patent1 = create_test_patent_result(suitability_data)
    all_patent_results.append(patent1)
    print(f"   #1: {patent1['target_patent_id']} (Grade: {patent1['final_grade']})")
    
    # Patent #2: B등급
    patent2 = create_test_patent_result(suitability_data)
    patent2.update({
        "target_patent_id": "US-TEST-002",
        "first_item": {
            "title": "Optimized NPU Memory Architecture for Low Power Applications",
            "patent_id": "US-TEST-002"
        },
        "originality_score": 0.78,
        "market_score": 0.68,
        "market_size_score": 0.22,
        "growth_potential_score": 0.23,
        "commercialization_readiness": 0.23,
        "final_grade": "B",
        "application_domains": ["Wearables", "IoT"],
        "llm_evaluation": {
            "suitability_grade": "B",
            "confidence_score": 0.75,
            "key_strengths": ["Good power efficiency", "Market ready"],
            "key_weaknesses": ["Limited differentiation", "Competitive market"],
            "investment_recommendation": "Hold",
            "risk_level": "Medium",
            "reasoning": "Solid technology with stable market presence but limited growth potential due to intense competition",
            "strategic_advice": "Focus on cost optimization and explore niche vertical markets for differentiation"
        }
    })
    all_patent_results.append(patent2)
    print(f"   #2: {patent2['target_patent_id']} (Grade: {patent2['final_grade']})")
    
    # Patent #3: S등급
    patent3 = create_test_patent_result(suitability_data)
    patent3.update({
        "target_patent_id": "US-TEST-003",
        "first_item": {
            "title": "Advanced NPU with Hardware-Software Co-Design for Real-Time AI Processing",
            "patent_id": "US-TEST-003"
        },
        "originality_score": 0.95,
        "market_score": 0.85,
        "market_size_score": 0.38,
        "growth_potential_score": 0.28,
        "commercialization_readiness": 0.19,
        "final_grade": "S",
        "application_domains": ["Autonomous Vehicles", "Robotics", "Smart City"],
        "llm_evaluation": {
            "suitability_grade": "S",
            "confidence_score": 0.95,
            "key_strengths": ["Breakthrough innovation", "Large market opportunity", "First-mover advantage"],
            "key_weaknesses": ["High development cost", "Long time-to-market"],
            "investment_recommendation": "Strong Buy",
            "risk_level": "Low",
            "reasoning": "Game-changing technology with exceptional ROI potential. Strong technical moat and massive addressable market in autonomous systems",
            "strategic_advice": "Aggressive market entry with strategic partnerships. Prioritize pilot programs with tier-1 automotive manufacturers to establish market leadership"
        }
    })
    all_patent_results.append(patent3)
    print(f"   #3: {patent3['target_patent_id']} (Grade: {patent3['final_grade']})")
    
    # Report Agent 실행
    print("\n" + "="*80)
    print("📊 Generating PDF Report")
    print("="*80)
    
    try:
        agent = ReportAgent(
            tech_name="NPU",
            output_dir=str(project_root / "output" / "reports"),
            use_llm=True  # LLM 요약 사용
        )
        
        result = agent.generate_report(all_patent_results)
        
        print("\n✅ Success!")
        print("="*80)
        print(f"📄 PDF: {result['report_pdf_path']}")
        print(f"📊 JSON: {result['report_json_path']}")
        print(f"📝 Title: {result['report_title']}")
        print("\n📈 Statistics:")
        print(f"   Patents: {result['total_patents_analyzed']}")
        print(f"   Avg Originality: {result['avg_originality_score']:.4f}")
        print(f"   Avg Market: {result['avg_market_score']:.4f}")
        print(f"   Grades: {result['grade_distribution']}")
        print("="*80)
        
        # PDF 자동으로 열기
        pdf_path = Path(result['report_pdf_path'])
        if pdf_path.exists():
            print(f"\n📖 PDF 파일 열기...")
            try:
                # Windows
                os.startfile(str(pdf_path))
                print(f"✅ PDF가 열렸습니다!")
            except AttributeError:
                # Linux/Mac
                try:
                    subprocess.run(['open', str(pdf_path)])  # Mac
                except FileNotFoundError:
                    subprocess.run(['xdg-open', str(pdf_path)])  # Linux
                print(f"✅ PDF가 열렸습니다!")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # ReportLab 설치 확인
    try:
        import reportlab
        print(f"✅ ReportLab {reportlab.Version} installed")
    except ImportError:
        print("\n❌ ReportLab not installed!")
        print("   Install: pip install reportlab")
        sys.exit(1)
    
    result = main()
    
    if result:
        print("\n✅ 테스트 완료!")
        print(f"\n💡 PDF 보고서:")
        print(f"   {result['report_pdf_path']}")
    else:
        print("\n❌ 테스트 실패!")
        sys.exit(1)