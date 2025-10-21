# AI 반도체 특허 경쟁력 평가 에이전트

> 본 프로젝트는 AI 반도체 분야의 글로벌 특허 데이터를 자동 수집·평가하여,  
> **한국의 기술 경쟁력과 산업 전략 수립에 필요한 인사이트를 실시간으로 제공하는**  
> **AI Agent 기반 분석·보고서 생성 시스템**입니다.

---

## SUMMARY

### Objective
- **AI 반도체 분야 특허의 기술 경쟁력 및 시장성을 평가**하고,  
- **한국의 기술 자립 및 산업 전략 수립을 위한 데이터 기반 보고서**를 자동 생성

### Methods
- LangGraph 기반 Multi-Agent Orchestration  
- Patent Retrieval → Evaluation → Synthesis → Report Generation Pipeline

### Tools
- LangGraph, LangChain, OpenAI GPT-4o, SerpAPI, Python, ChromaDB

---

## 1️⃣ 서비스 개요

본 서비스는 **AI 반도체(AI Chip)** 관련 최신 특허를 자동으로 수집하고, 각 특허의 **기술성·시장성·적합성**을 평가하여 국가별 기술경쟁력을 비교하는 **자동 보고서 생성 시스템**입니다.

- LangGraph 기반의 멀티 에이전트 구조를 통해 특허 검색 → 평가 → 보고서 생성을 주기적으로 자동화  
- 궁극적으로는 **한국의 기술 경쟁력 강화를 위한 실시간 특허 인텔리전스 도구**로 활용되길 기대

---

## 2️⃣ 제안 배경 (AS-IS)

AI 반도체 산업은 **GPU·NPU·PIM 등 차세대 연산 아키텍처의 경쟁이 가속화**되면서 글로벌 특허 출원이 폭발적으로 증가하고 있습니다. 그러나 이러한 기술 확산 속에서도, **산업 전반의 정보 접근성과 분석 효율성에는 한계**가 존재합니다.

- 개별 기술의 **시장성·기술성·응용 가능성에 대한 정량적 비교가 어려움**  
  - HBM, NPU, QPU 등 **다양한 기술 트렌드가 병렬적으로 발전**하면서 **특허 간 편차·핵심 기술 식별의 비효율** 발생  
- 엔비디아 중심의 GPU 생태계에서 신흥 스타트업들의 **화이트 스페이스(미개척 영역)** **전략을 위한 실질적 경쟁력이나 혁신 포인트를 객관적으로 평가하기 어려움**  
- 구글·아마존·메타·MS 등 글로벌 기업들은 자체 AI칩에 대규모 투자 중이지만, **이들 기업의 기술 방향성과 특허 트렌드를 통합적으로 추적·비교할 수 있는 체계가 부재**

> (출처 : 위의 내용은 전부 기사 기반으로 작성되었으나, 향후 출처 재정리 예정)

---

## 3️⃣ 필요성 및 목적 (TO-BE)

### 🔹 What
> AI 반도체 분야의 국가별 최신 특허 데이터를 자동으로 분석하고,  
> **한국의 기술 포지션과 경쟁국 대비 기술 격차를 시각화**하는 리포트를 생성

### 🔹 Why
- 특허는 매일 신규 공개되며, 기존 정적 분석으로는 **최신 기술 트렌드 추적이 불가**  
- 특히, AI 반도체 산업의 정책·투자 판단은 **최신 특허 흐름 기반 인사이트**가 핵심 경쟁력  
- 사람 대신 **지속 모니터링·분석·보고서 재생성 루프를 수행할 수 있는 AI Agent 구조**가 필요

### 🔹 How
> LangGraph 기반 **AI Multi-Agent 시스템**으로 **루프 형태로 자동화**
> - 특허 수집(Search) → 기술/시장성 평가(Evaluation) → 종합 적합성 판단(Suitability) → 자동 보고서 생성(Report)

---

## 4️⃣ FEATURES

- **특허 검색 자동화** – SerpAPI 기반으로 ‘AI 반도체’ 하위 키워드 중심 최신 특허 수집  
- **기술성 평가** – LLM을 활용한 기술 독창성 및 트렌드 적합성 점수화 (5점 척도 예정)  
- **시장성 평가** – 기술 적용 산업 및 시장 성장 가능성 분석 (5점 척도 예정)  
- **적합성 판단** – 기술성+시장성 결과 종합, 국가별 기술 경쟁력 비교  
- **보고서 생성** – “한국의 AI 반도체 기술 경쟁력 보고서” PDF 자동 생성

---

## 5️⃣ TECH STACK

| Category | Details |
|-----------|----------|
| **Framework** | LangGraph, LangChain |
| **Language** | Python 3.11 |
| **LLM** | GPT-4o-mini |
| **Retrieval** | ChromaDB (Vector Store) |
| **Embedding** | Jina Embeddings v2 Base-ko (변경 가능) |
| **External API** | SerpAPI (Google Patents) |
| **Visualization** | Matplotlib, Pandas |

---

## 6️⃣ STATE 구조

| State | 주요 필드 | 설명 |
| --- | --- | --- |
| **PatentState** | `patents[]`, `basis`, `keywords[]` | 국가별 상위 N 특허 수집 + 초록 한국어 요약 + 핵심 키워드 추출 |
| **TechState** | `technology_score (0~5)`, `category_scores`, `technology_analysis_basis` | 기술 독창성·트렌드 적합성 평가 |
| **MarketState** | `market_score (0~5)`, `market_analysis_basis` | 시장 적용성·성장성 평가 |
| **SuitabilityState** | *(미정)* | 기술/시장 통합 적합성 판단 및 유망 특허 선별 |
| **ReportState** | `report_summary`, `report_path` | 최종 보고서 본문 및 저장 경로 |
| **WorkflowState** | `query`, `patent`, `tech`, `market`, `suitability`, `report`, `error` | 전체 워크플로우 상태 통합 |

---

## 7️⃣ AGENTS

| Agent | 역할 | 출력 |
| --- | --- | --- |
| **PatentSearchAgent** | ‘AI 반도체’ 관련 최신 글로벌 특허 수집 (국가별 상위 N개) + LLM : 초록 요약 - 한국어 정렬, 기술 키워드 수집 | PatentState |
| **TechEvaluationAgent** | 기술 독창성 및 트렌드 적합성 평가 | TechState |
| **MarketEvaluationAgent** | 시장 적용성 및 성장성 평가 | MarketState |
| **SuitabilityAgent** | 기술성+시장성 종합 평가 | SuitabilityState |
| **ReportAgent** | 한국의 기술 경쟁력 보고서 자동 생성 (국가별 상위 점수의 특허만을 대상) | FinalState |

---

## 8️⃣ ARCHITECTURE

```markdown
┌──────────────────────────────┐
│        LangGraph Flow        │
└──────────────────────────────┘
              │
              ▼
 [PatentSearchAgent]  
 ──▶ (국가별 상위 N 특허 수집 + 초록 한국어 요약 + 키워드 추출 )
              │
              ▼
 [TechEvaluationAgent]
 ──▶ 기술 독창성 · 트렌드 적합성 평가
              │
              ▼
 [MarketEvaluationAgent]
 ──▶ 시장 적용성 · 성장성 평가
              │
              ▼
 [SuitabilityAgent]
 ──▶ 기술성 + 시장성 통합 점수 산출
 ──▶ 유망 특허만 선별하여 전달
              │
              ▼
 [ReportAgent]
 ──▶ 선별된 상위 특허 기반
 ──▶ 한국 AI 반도체 기술경쟁력 보고서 생성
              │
              ▼
 📄 **최종 출력:** 한국 AI 반도체 기술경쟁력 보고서
      ├─ 국가별 상위 점수 특허 분석
      ├─ 기술·시장 통합 인사이트
      ├─ 선도 출원인 및 트렌드 요약
      └─ 국내 적용성 및 리스크 포인트

## 9️⃣ OUTPUT ToC (Report 목차)

1. **SUMMARY**
   - 국가별 기술 경쟁력 비교 요약  
   - 주요 기술 키워드별 평가 결과  
   - 한국의 강점 및 개선 필요 영역  

2. **DETAIL ANALYSIS**
   - 상위 특허별 기술 요약  
   - 기술성 / 시장성 평가 세부 내용 및 점수  

3. **REFERENCE**
   - 보고서 생성에 활용된 출처 및 기사, 특허 데이터  

4. **APPENDIX**
   - 평가 로직 설명 (점수화 기준, 지표 해석 등)  
   - Agent별 분석 프로세스  

---

## 🔟 DIRECTORY STRUCTURE

ai-semiconductor-report/
├── agents/
│ ├── patent_search_agent.py
│ ├── tech_evaluation_agent.py
│ ├── market_evaluation_agent.py
│ ├── suitability_agent.py
│ └── report_agent.py
├── state/
│ ├── patent_state.py
│ ├── tech_state.py
│ ├── market_state.py
│ ├── suitability_state.py
│ └── final_state.py
├── rag/
│ ├── build_index.py
│ ├── chroma_store/
│ └── embeddings/
└── main.py


---

## 🤝 CONTRIBUTORS

- 추후 수정 예정

---

## 🧩 CONCLUSION

본 프로젝트는 **AI 반도체 산업의 기술 경쟁력 분석을 자동화**하기 위한 목적으로 시행되었습니다.  
LangGraph 기반의 에이전트 체계를 통해, 단일 실행만으로 “최신 특허 수집 → 평가 → 보고서 생성”까지 수행할 수 있으며,  
향후에는 **Airflow 기반 주기적 재분석**, **정책기관용 리포트 대시보드**로 확장될 수 있습니다.