# 🇰🇷 AI 반도체 특허 경쟁력 평가 에이전트

> 본 프로젝트는 AI 반도체 분야의 글로벌 특허 데이터를 자동 수집·평가하여,  
> **한국의 기술 경쟁력과 산업 전략 수립에 필요한 인사이트를 실시간으로 제공하는**  
> **AI Agent 기반 분석·보고서 생성 시스템**입니다.

---

## 📌 SUMMARY

### 🎯 Objective

- **AI 반도체 분야 특허의 기술 경쟁력 및 시장성 평가**
- **한국의 기술 자립 및 산업 전략 수립을 위한 데이터 기반 보고서 자동 생성**

### ⚙️ Methods

- LangGraph 기반 Multi-Agent Orchestration
- Patent Retrieval(Search) → Evaluation → Synthesis → Report Generation Pipeline

### 🧰 Tools

- LangGraph, LangChain, OpenAI GPT-4o, SerpAPI, Python, ChromaDB

---

## 1️⃣ 서비스 개요

본 서비스는 **AI 반도체(AI Chip)** 관련 최신 특허를 자동으로 수집하고,  
각 특허의 **기술성·시장성·적합성**을 평가하여  
국가별 기술경쟁력을 비교하는 **자동 보고서 생성 시스템**입니다.

- LangGraph 기반의 멀티 에이전트 구조로, 특허 검색 → 평가 → 보고서 생성을 주기적으로 자동화
- 궁극적으로는 **한국의 기술 경쟁력 강화를 위한 실시간 특허 인텔리전스 도구**로 발전 기대

---

## 2️⃣ 제안 배경 (AS-IS)

AI 반도체 산업은 **GPU·NPU·PIM 등 차세대 연산 아키텍처의 경쟁 가속화**로  
글로벌 특허 출원이 폭발적으로 증가하고 있습니다.  
그러나 이러한 확산 속에서도 **산업 전반의 정보 접근성과 분석 효율성에는 한계**가 있습니다.

- 다양한 기술 트렌드(HBM, QPU 등) 병렬 발전 → **특허 간 편차 및 핵심 기술 식별의 어려움**
- **엔비디아 중심 생태계**에서 신흥 기업의 **화이트 스페이스 전략** 평가 한계
- 구글, 아마존 등은 독자 AI칩을 대규모 개발 중이나,  
  **기술 방향성 및 트렌드를 종합 분석하는 체계 부재**

---

## 3️⃣ 필요성 및 목적 (TO-BE)

### 🔹 What

> 국가별 최신 AI 반도체 특허를 자동 분석하고,  
> **한국의 기술 포지션과 기술 격차를 시각화한 리포트 생성**

### 🔹 Why

- 특허는 **매일 공개**되므로, 기존의 **정적 분석 방식은 한계**
- **최신 특허 흐름 기반 인사이트**가 정책·투자 판단의 핵심
- **지속 모니터링·자동 평가·리포트화**가 가능한 AI 에이전트 구조 필요

### 🔹 How

- LangGraph 기반 **루프 자동화 시스템**
  - 특허 수집 → 기술/시장 평가 → 통합 적합성 판단 → 리포트 생성

---

## 4️⃣ FEATURES

- 🔍 **특허 검색 자동화** : SerpAPI로 ‘AI 반도체’ 하위 키워드 기반 최신 특허 수집
- 🧠 **기술성 평가** : GPT로 독창성·트렌드 적합성 점수화 (0~5점)
- 💡 **시장성 평가** : 산업 적용성 및 시장 성장성 평가 (0~5점)
- ⚖️ **적합성 판단** : 기술 + 시장 통합 평가, 유망 특허 선별
- 📄 **보고서 생성** : "한국 AI 반도체 기술 경쟁력 보고서" 자동 출력

---

## 5️⃣ TECH STACK

| Category         | Details                               |
|------------------|----------------------------------------|
| **Framework**    | LangGraph, LangChain                  |
| **Language**     | Python 3.11                           |
| **LLM**          | GPT-4o-mini (via OpenAI)              |
| **Retrieval**    | ChromaDB                              |
| **Embedding**    | Jina Embeddings v2 Base-ko            |
| **External API** | SerpAPI (Google Patents)              |
| **Visualization**| Pandas, Matplotlib                    |

---

## 6️⃣ STATE 구조

| State             | 주요 필드                                      | 설명 |
|------------------|------------------------------------------------|------|
| **PatentState**   | `patents[]`, `basis`, `keywords[]`             | 특허 수집 + 요약 + 키워드 추출 |
| **TechState**     | `technology_score`, `category_scores`, `technology_analysis_basis` | 기술성 평가 |
| **MarketState**   | `market_score`, `market_analysis_basis`        | 시장성 평가 |
| **SuitabilityState** | *(미정)*                                   | 기술·시장 통합 적합성 판단 |
| **ReportState**   | `report_summary`, `report_path`                | 리포트 본문 및 저장 경로 |
| **WorkflowState** | `query`, `patent`, `tech`, `market`, `suitability`, `report`, `error` | 전체 상태 통합 |

---

## 7️⃣ AGENTS

| Agent                | 역할                                               | 출력(STATE)       |
|----------------------|----------------------------------------------------|-------------------|
| **PatentSearchAgent**| 특허 수집 + 요약 + 키워드 정리                     | PatentState       |
| **TechEvaluationAgent** | 기술 독창성·트렌드 적합성 평가                  | TechState         |
| **MarketEvaluationAgent** | 시장성 및 산업 적용성 평가                  | MarketState       |
| **SuitabilityAgent** | 기술 + 시장 통합 적합성 판단                       | SuitabilityState  |
| **ReportAgent**      | 전체 상태 기반 보고서 생성                         | ReportState       |

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
        ┌───────────────┐
        │   Parallel    │
        └───────────────┘
        ┌───────────────┬───────────────┐
        ▼                               ▼
 [TechEvaluationAgent]          [MarketEvaluationAgent]
 ──▶ 기술 독창성·트렌드 적합성 평가     ──▶ 시장 적용성·성장성 평가
        └───────────────┬───────────────┘
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
      └─ 국내 적용성 및 리스크 포인트
```

---

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


```markdown
ai-semiconductor-report/
├── agents/                          
│   ├── patent_search_agent.py       
│   ├── tech_evaluation_agent.py     
│   ├── market_evaluation_agent.py   
│   ├── suitability_agent.py         
│   └── report_agent.py              
│
├── state/                           
│   ├── patent_state.py              
│   ├── tech_state.py                
│   ├── market_state.py              
│   ├── suitability_state.py         
│   ├── report_state.py              
│   └── workflow_state.py            
│  
├── rag/                             
│   ├── build_index.py               
│   ├── chroma_store/                
│   └── embeddings/                  
│
└── main.py                     
```

---

## 🤝 CONTRIBUTORS

- 추후 수정 예정

---

## 🧩 CONCLUSION

본 프로젝트는 **AI 반도체 산업의 기술 경쟁력 분석을 자동화**하기 위한 목적으로 시행되었습니다.  
LangGraph 기반의 에이전트 체계를 통해, 단일 실행만으로 “최신 특허 수집 → 평가 → 보고서 생성”까지 수행할 수 있으며,  
향후에는 **Airflow 기반 주기적 재분석**, **정책기관용 리포트 대시보드**로 확장될 수 있습니다.