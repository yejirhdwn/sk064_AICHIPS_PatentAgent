"""
Suitability Score Agent with LLM-as-a-Judge
- 독창성 + 시장성 점수를 LLM이 분석하여 최종 평가
- GPT-4가 점수의 의미를 해석하고 종합적인 판단 수행
"""

from __future__ import annotations
import os, json
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

try:
    from openai import OpenAI
    _OPENAI_OK = True
except Exception:
    _OPENAI_OK = False
    print("⚠️ OpenAI not available. Install: pip install openai")

load_dotenv()


# ===== Configuration =====
class ScoringConfig:
    """점수 산정 설정"""
    ORIGINALITY_WEIGHT = 0.55
    MARKET_WEIGHT = 0.45
    ORIGINALITY_MIN = 0.75
    ORIGINALITY_MAX = 1.0
    
    GRADE_THRESHOLDS = {
        "S": 0.85, "A": 0.70, "B": 0.55, "C": 0.40, "D": 0.0
    }


# ===== LLM Judge Prompts =====
JUDGE_SYSTEM_PROMPT = """당신은 특허 기술의 지속가능성을 평가하는 전문가입니다.

**역할:**
- 독창성(Originality)과 시장성(Market) 점수를 종합 분석
- 기술의 장기적 생존 가능성과 투자 가치 판단
- 점수 이면의 의미를 해석하고 구체적인 근거 제시

**평가 기준:**
1. 기술적 독창성: 특허의 신규성, 차별성, 기술적 난이도
2. 시장 잠재력: 시장 규모, 성장 가능성, 상업화 준비도
3. 지속가능성: 기술 수명, 경쟁력 지속성, 투자 리스크

**응답 형식:**
반드시 JSON 형식으로만 응답하세요:
{
  "suitability_grade": "S/A/B/C/D 중 하나",
  "confidence_score": 0.0-1.0,
  "key_strengths": ["강점1", "강점2", "강점3"],
  "key_weaknesses": ["약점1", "약점2"],
  "investment_recommendation": "추천/보류/비추천 중 하나",
  "risk_level": "낮음/보통/높음 중 하나",
  "reasoning": "종합적인 평가 근거 (2-3문장)",
  "strategic_advice": "전략적 조언 (2-3문장)"
}
"""


def _create_judge_prompt(
    tech_name: str,
    originality_score: float,
    market_score: float,
    calculated_grade: str,
    market_details: Optional[Dict] = None
) -> str:
    """LLM Judge를 위한 프롬프트 생성"""
    
    prompt = f"""**기술명**: {tech_name}

**점수 정보:**
- 독창성 점수: {originality_score:.4f} (0~1 범위, 높을수록 신규성 높음)
- 시장성 점수: {market_score:.4f} (0~1 범위, 높을수록 시장 잠재력 높음)
- 계산된 등급: {calculated_grade}

**독창성 점수 해석:**
- 0.90+: 매우 높은 기술적 독창성 (혁신적)
- 0.80-0.90: 높은 기술적 독창성 (차별화됨)
- 0.70-0.80: 양호한 기술적 독창성
- 0.70 미만: 보통 수준의 독창성

**시장성 점수 해석:**
- 0.75+: 우수한 시장 잠재력 (대규모 시장)
- 0.55-0.75: 양호한 시장 잠재력
- 0.35-0.55: 보통 수준의 시장 잠재력
- 0.35 미만: 제한적인 시장 잠재력
"""
    
    if market_details:
        prompt += f"""
**시장 세부 정보:**
- 시장 규모: {market_details.get('market_size_score', 'N/A')}
- 성장 잠재력: {market_details.get('growth_potential_score', 'N/A')}
- 상업화 준비도: {market_details.get('commercialization_readiness', 'N/A')}
"""
    
    prompt += """
위 정보를 바탕으로 이 기술의 지속가능성을 종합적으로 평가하세요.
단순히 점수만 보지 말고, 점수 조합이 의미하는 바를 깊이 있게 분석하세요.

예를 들어:
- 독창성은 높지만 시장성이 낮다면? → 틈새 시장 전략 필요
- 시장성은 높지만 독창성이 낮다면? → 경쟁 리스크 높음
- 둘 다 높다면? → 강력 투자 추천
- 둘 다 낮다면? → 재검토 필요

반드시 JSON 형식으로만 응답하세요.
"""
    
    return prompt


# ===== Main Agent =====
class SuitabilityScoreAgent:
    """
    LLM-as-a-Judge 기반 지속가능성 평가 Agent
    
    1차: 수식 기반 점수 계산
    2차: LLM이 점수를 해석하고 최종 판단
    """
    
    def __init__(
        self, 
        tech_name: str,
        output_dir: str = "./output/suitability",
        use_llm_judge: bool = True
    ):
        self.tech_name = tech_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_llm_judge = use_llm_judge and _OPENAI_OK
        
        if self.use_llm_judge:
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = "gpt-4o-mini"  # or "gpt-4o"
    
    def calculate_suitability(
        self,
        originality_score: float,
        market_score: float,
        market_size_score: Optional[float] = None,
        growth_potential_score: Optional[float] = None,
        commercialization_readiness: Optional[float] = None,
        normalize_originality: bool = True
    ) -> Dict[str, Any]:
        """
        지속가능성 점수 계산 + LLM 평가
        """
        print("=" * 80)
        print(f"🌱 Suitability Score Calculation: {self.tech_name}")
        print("=" * 80)
        
        # 입력 검증
        if not (0 <= originality_score <= 1):
            raise ValueError(f"originality_score must be in [0, 1], got {originality_score}")
        if not (0 <= market_score <= 1):
            raise ValueError(f"market_score must be in [0, 1], got {market_score}")
        
        print(f"📊 Input Scores:")
        print(f"   - Originality: {originality_score:.4f}")
        print(f"   - Market: {market_score:.4f}")
        
        # ===== Step 1: 수식 기반 계산 =====
        if normalize_originality:
            originality_normalized = self._normalize_originality(originality_score)
        else:
            originality_normalized = originality_score
        
        calculated_score = self._calculate_score(originality_normalized, market_score)
        calculated_grade = self._determine_grade(calculated_score)
        
        breakdown = {
            "originality_raw": originality_score,
            "originality_normalized": originality_normalized,
            "originality_weighted": round(originality_normalized * ScoringConfig.ORIGINALITY_WEIGHT, 4),
            "market_score": market_score,
            "market_weighted": round(market_score * ScoringConfig.MARKET_WEIGHT, 4),
            "calculated_score": calculated_score,
            "calculated_grade": calculated_grade
        }
        
        print(f"\n📐 Calculated Metrics:")
        print(f"   - Score: {calculated_score:.4f}")
        print(f"   - Grade: {calculated_grade}")
        
        # ===== Step 2: LLM Judge 평가 =====
        llm_evaluation = None
        final_grade = calculated_grade
        final_score = calculated_score
        
        if self.use_llm_judge:
            print(f"\n🤖 LLM Judge Evaluation...")
            
            market_details = {
                "market_size_score": market_size_score,
                "growth_potential_score": growth_potential_score,
                "commercialization_readiness": commercialization_readiness
            }
            
            llm_evaluation = self._llm_judge_evaluation(
                originality_score,
                market_score,
                calculated_grade,
                market_details if any(market_details.values()) else None
            )
            
            if llm_evaluation:
                final_grade = llm_evaluation.get("suitability_grade", calculated_grade)
                print(f"   ✅ LLM Grade: {final_grade}")
                print(f"   ✅ Confidence: {llm_evaluation.get('confidence_score', 0):.2f}")
                print(f"   ✅ Recommendation: {llm_evaluation.get('investment_recommendation', 'N/A')}")
                print(f"   ✅ Risk Level: {llm_evaluation.get('risk_level', 'N/A')}")
        
        # ===== Step 3: 종합 요약 생성 =====
        summary = self._generate_summary(
            originality_score, 
            market_score, 
            final_score, 
            final_grade,
            llm_evaluation
        )
        
        # 결과 구성
        result = {
            "tech_name": self.tech_name,
            "originality_score": originality_score,
            "market_score": market_score,
            "calculated_score": calculated_score,
            "calculated_grade": calculated_grade,
            "final_grade": final_grade,
            "suitability_score": final_score,
            "suitability_grade": final_grade,
            "score_breakdown": breakdown,
            "llm_evaluation": llm_evaluation,
            "evaluation_summary": summary
        }
        
        # 세부 점수 추가
        if market_size_score is not None:
            result["market_size_score"] = market_size_score
        if growth_potential_score is not None:
            result["growth_potential_score"] = growth_potential_score
        if commercialization_readiness is not None:
            result["commercialization_readiness"] = commercialization_readiness
        
        # 결과 저장
        output_path = self._save_result(result)
        result["suitability_output_path"] = str(output_path)
        
        # 결과 출력
        print("\n" + "=" * 80)
        print("🎯 Final Evaluation Result")
        print("=" * 80)
        print(f"✅ Grade: {final_grade}")
        print(f"   - Calculated: {calculated_grade} ({calculated_score:.4f})")
        if llm_evaluation:
            print(f"   - LLM Assessed: {final_grade}")
            print(f"\n💡 Key Strengths:")
            for strength in llm_evaluation.get("key_strengths", []):
                print(f"   • {strength}")
            print(f"\n⚠️ Key Weaknesses:")
            for weakness in llm_evaluation.get("key_weaknesses", []):
                print(f"   • {weakness}")
            print(f"\n🎯 Investment: {llm_evaluation.get('investment_recommendation', 'N/A')}")
            print(f"📊 Risk Level: {llm_evaluation.get('risk_level', 'N/A')}")
        print(f"\n📝 {summary}")
        print(f"\n💾 Saved to: {output_path}")
        print("=" * 80)
        
        return result
    
    def _llm_judge_evaluation(
        self,
        originality: float,
        market: float,
        calculated_grade: str,
        market_details: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """LLM을 Judge로 사용하여 평가"""
        if not self.use_llm_judge:
            return None
        
        try:
            prompt = _create_judge_prompt(
                self.tech_name,
                originality,
                market,
                calculated_grade,
                market_details
            )
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            evaluation = json.loads(response.choices[0].message.content)
            return evaluation
            
        except Exception as e:
            print(f"   ⚠️ LLM evaluation failed: {e}")
            return None
    
    def _normalize_originality(self, score: float) -> float:
        """독창성 점수 정규화"""
        if score >= ScoringConfig.ORIGINALITY_MAX:
            return 1.0
        if score <= ScoringConfig.ORIGINALITY_MIN:
            return 0.0
        normalized = (score - ScoringConfig.ORIGINALITY_MIN) / \
                     (ScoringConfig.ORIGINALITY_MAX - ScoringConfig.ORIGINALITY_MIN)
        return max(0.0, min(1.0, normalized))
    
    def _calculate_score(self, originality_normalized: float, market: float) -> float:
        """지속가능성 점수 계산"""
        suitability = (
            originality_normalized * ScoringConfig.ORIGINALITY_WEIGHT +
            market * ScoringConfig.MARKET_WEIGHT
        )
        return round(suitability, 4)
    
    def _determine_grade(self, score: float) -> str:
        """점수에 따른 등급 결정"""
        for grade, threshold in ScoringConfig.GRADE_THRESHOLDS.items():
            if score >= threshold:
                return grade
        return "D"
    
    def _generate_summary(
        self, 
        originality: float, 
        market: float, 
        score: float, 
        grade: str,
        llm_eval: Optional[Dict] = None
    ) -> str:
        """종합 평가 요약 생성"""
        if llm_eval and llm_eval.get("reasoning"):
            # LLM이 생성한 평가 사용
            base_summary = f"'{self.tech_name}' 기술 (등급: {grade}, 점수: {score:.2f})"
            reasoning = llm_eval.get("reasoning", "")
            advice = llm_eval.get("strategic_advice", "")
            return f"{base_summary}\n\n평가: {reasoning}\n\n전략적 조언: {advice}"
        else:
            # 기본 요약
            if originality >= 0.90:
                orig_eval = "매우 높은 기술적 독창성"
            elif originality >= 0.80:
                orig_eval = "높은 기술적 독창성"
            else:
                orig_eval = "양호한 기술적 독창성"
            
            if market >= 0.75:
                market_eval = "우수한 시장 잠재력"
            elif market >= 0.55:
                market_eval = "양호한 시장 잠재력"
            else:
                market_eval = "보통 수준의 시장 잠재력"
            
            return f"'{self.tech_name}' 기술은 {orig_eval}과 {market_eval}을 보유하고 있으며, 최종 등급은 {grade}입니다."
    
    def _save_result(self, result: Dict[str, Any]) -> Path:
        """결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"suitability_{self.tech_name}_{timestamp}.json"
        output_path = self.output_dir / filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return output_path


# ===== CLI =====
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Suitability Agent with LLM Judge")
    parser.add_argument("tech_name", type=str, help="기술 키워드")
    parser.add_argument("--originality", type=float, required=True, help="독창성 점수")
    parser.add_argument("--market", type=float, required=True, help="시장성 점수")
    parser.add_argument("--no-llm", action="store_true", help="LLM Judge 비활성화")
    args = parser.parse_args()
    
    agent = SuitabilityScoreAgent(
        tech_name=args.tech_name,
        use_llm_judge=not args.no_llm
    )
    
    result = agent.calculate_suitability(
        originality_score=args.originality,
        market_score=args.market
    )
    
    print(f"\n✅ Grade: {result['suitability_grade']}")


__all__ = ["SuitabilityScoreAgent"]