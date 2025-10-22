"""
Patent-Centric Market Evaluation with Tavily Search Integration
- RAG (로컬 문서) + Tavily (실시간 웹 검색) Hybrid
- 시장 규모: 특허가 실제 적용 가능한 세부 시장(SAM) 기준
- 성장률: CAGR 또는 구체적 성장 수치
- Tavily로 최신 시장 데이터 보완
"""

from __future__ import annotations
import os, json, re
from typing import Any, Dict, List, Optional, TypedDict
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from pydantic import BaseModel, Field, field_validator

# LangChain / LangGraph
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Tavily Search
from tavily import TavilyClient

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# ===== State Definition =====
class MarketState(TypedDict, total=False):
    """특허 시장성 평가 State"""
    tech_name: str
    error: str
    first_item: Dict[str, Any]
    target_patent_id: str
    query: str
    keyterms: List[str]
    retrieved_docs: List[Any]
    web_search_results: List[Dict[str, Any]]
    
    # Scores
    market_size_score: float
    growth_potential_score: float
    commercialization_readiness: float
    market_score: float
    
    # Outputs
    patent_id: str
    patent_title: str
    application_domains: List[str]
    commercialization_potential: str
    market_rationale: str
    demand_signals: List[str]
    sources: List[str]
    market_output_path: str


# ===== Schema =====
class _KeytermsSchema(BaseModel):
    keyterms: List[str] = Field(..., description="abstract에서 추출한 핵심 기술 키워드(대표어, 3~8개)")


class _MarketSchema(BaseModel):
    tech_name: str
    patent_id: str
    patent_title: str
    
    # 정량적 점수
    market_size_score: float = Field(..., ge=0.0, le=0.4, description="실제 적용 가능 시장(SAM) 기반")
    growth_potential_score: float = Field(..., ge=0.0, le=0.3, description="CAGR 또는 구체적 성장률")
    commercialization_readiness: float = Field(..., ge=0.0, le=0.3, description="상용화 준비도")
    market_score: float = Field(..., ge=0.0, le=1.0, description="총점")
    
    # 정성적 평가
    application_domains: List[str] = Field(..., description="적용 가능한 산업/제품군 (최대 5개)")
    commercialization_potential: str = Field(..., description="High/Medium/Low")
    market_rationale: str = Field(..., description="'이 특허(patent_id)는 ...' 형식, 5~7문장")
    demand_signals: List[str] = Field(default_factory=list, description="시장 수요 신호 (최대 5개)")
    
    # 출처 (코드에서 자동 덮어쓰기)
    sources: Optional[List[str]] = None

    @field_validator("commercialization_potential")
    @classmethod
    def _validate_potential(cls, v):
        if v not in ["High", "Medium", "Low"]:
            raise ValueError("Must be High/Medium/Low")
        return v


# ===== Helpers =====
def _extract_keyterms_from_abstract(llm: ChatOpenAI, title: str, abstract: str, max_terms: int = 8) -> List[str]:
    """LLM으로 abstract에서 핵심 기술 키워드 추출"""
    system = (
        "너는 특허 기술 분석 전문가다. "
        "제목과 초록에서 핵심 기술 키워드(대표어)만 추출한다. "
        "회사명, 제품명, 형용사, 일반적인 단어는 제외하고 기술적 개념만 추출."
    )
    human = (
        "제목: {title}\n\n"
        "초록: {abstract}\n\n"
        f"핵심 기술 키워드를 최대 {max_terms}개 추출하라. "
        "JSON 형식으로 반환: {{\"keyterms\": [\"keyword1\", \"keyword2\", ...]}}"
    )
    
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    chain = prompt | llm.with_structured_output(_KeytermsSchema)

    try:
        result: _KeytermsSchema = chain.invoke({"title": title, "abstract": abstract})
        return [t.strip() for t in result.keyterms if t.strip()][:max_terms]
    except Exception as e:
        print(f"  ⚠️ Keyterm extraction failed: {e}")
        # Fallback: 단순 추출
        text = (abstract or "").lower()
        tokens = re.findall(r"[a-z][a-z0-9\-]{3,}", text)
        return sorted(set(tokens), key=tokens.count, reverse=True)[:max_terms]


def _build_rag_query(tech_name: str, keyterms: List[str]) -> str:
    """RAG 검색 쿼리 구성"""
    parts = [tech_name] + keyterms[:6] + ["market size", "growth", "industry application"]
    seen = set()
    unique = []
    for p in parts:
        p_lower = p.lower().strip()
        if p_lower and p_lower not in seen:
            unique.append(p.strip())
            seen.add(p_lower)
    return " ".join(unique)


def _build_tavily_queries(tech_name: str, keyterms: List[str]) -> List[str]:
    """Tavily 검색 쿼리 생성 (시장 규모, CAGR)"""
    queries = []
    
    # 1. 기술 키워드 기반 시장 규모
    tech_terms = " ".join([tech_name] + keyterms[:3])
    queries.append(f"{tech_terms} market size 2024 2025 billion USD")
    
    # 2. CAGR 및 성장률
    queries.append(f"{tech_terms} CAGR growth rate forecast 2024-2028")
    
    # 3. 응용 분야 일반 쿼리
    queries.append(f"{tech_name} application market forecast")
    
    return queries[:3]  # 최대 3개 쿼리


def _collect_sources(rag_docs: List[Document], tavily_results: List[Dict[str, Any]], max_items: int = 8) -> List[str]:
    """RAG + Tavily 출처 수집"""
    sources = []
    seen = set()
    
    # RAG 문서
    for doc in rag_docs:
        src = (doc.metadata or {}).get("source") or (doc.metadata or {}).get("filename")
        if src and src not in seen:
            sources.append(f"[RAG] {src}")
            seen.add(src)
    
    # Tavily 결과
    for result in tavily_results:
        url = result.get("url", "")
        title = result.get("title", "")
        if url and url not in seen:
            display = title[:50] if title else url
            sources.append(f"[Web] {display} ({url})")
            seen.add(url)
        
        if len(sources) >= max_items:
            break
    
    return sources or ["No sources available"]


# ===== Agent =====
class MarketSizeGrowthAgent:
    def __init__(
        self, 
        tech_name: str, 
        patent_info: Dict[str, Any], 
        output_dir: str = "./output/market_evaluation"
    ):
        self.tech_name = tech_name
        self.patent_info = patent_info
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Environment variables
        self.collection = os.getenv("MARKET_COLLECTION", "patent_market_index")
        self.chroma_dir = os.getenv("MARKET_CHROMA_DIR", "./rag/chroma")
        self.embed_model = os.getenv("MARKET_EMBED_MODEL", "bge-m3")
        self.llm_model = os.getenv("MARKET_LLM_MODEL", "gpt-4o-mini")
        api_key = os.getenv("OPENAI_API_KEY")
        tavily_key = os.getenv("TAVILY_API_KEY")

        # VectorDB setup
        self.embeddings = OllamaEmbeddings(model=self.embed_model)
        self.vs = Chroma(
            collection_name=self.collection,
            persist_directory=self.chroma_dir,
            embedding_function=self.embeddings
        )
        self.semantic = self.vs.as_retriever(search_kwargs={"k": 4})

        # BM25 setup
        all_docs = self.vs.get(include=["documents", "metadatas"])
        bm25_docs = [
            Document(page_content=d or "", metadata=m or {}) 
            for d, m in zip(all_docs["documents"], all_docs["metadatas"])
        ]
        self.bm25 = BM25Retriever.from_documents(bm25_docs)
        self.bm25.k = 4

        # LLM
        self.llm = ChatOpenAI(model=self.llm_model, temperature=0, openai_api_key=api_key)
        
        # Tavily Client
        self.tavily = TavilyClient(api_key=tavily_key) if tavily_key else None
        
        self.graph = self._build_graph()

    def _build_graph(self):
        """LangGraph 구성"""
        g = StateGraph(MarketState)
        g.add_node("retrieve_rag", self._node_retrieve_rag)
        g.add_node("retrieve_web", self._node_retrieve_web)
        g.add_node("synthesize", self._node_synthesize)
        
        g.set_entry_point("retrieve_rag")
        g.add_edge("retrieve_rag", "retrieve_web")
        g.add_edge("retrieve_web", "synthesize")
        g.add_edge("synthesize", END)
        
        return g.compile(checkpointer=MemorySaver())

    def _node_retrieve_rag(self, state: MarketState) -> MarketState:
        """RAG 검색 노드"""
        query = state["query"]
        print(f"🔍 [RAG] Retrieving documents for: {query}")
        
        docs_semantic = self.semantic.invoke(query)
        docs_bm25 = self.bm25.invoke(query)  # get_relevant_documents → invoke
        all_docs = (docs_semantic or []) + (docs_bm25 or [])
        
        print(f"  ✅ Retrieved {len(all_docs)} RAG documents")
        state["retrieved_docs"] = all_docs
        return state

    def _node_retrieve_web(self, state: MarketState) -> MarketState:
        """Tavily 웹 검색 노드"""
        if not self.tavily:
            print("  ⚠️ Tavily API key not found, skipping web search")
            state["web_search_results"] = []
            return state
        
        tech = state["tech_name"]
        keyterms = state["keyterms"]
        
        # 시장 데이터 검색 쿼리 생성
        queries = _build_tavily_queries(tech, keyterms)
        all_results = []
        
        for q in queries:
            print(f"🌐 [Tavily] Searching: {q}")
            try:
                result = self.tavily.search(query=q, max_results=2)
                all_results.extend(result.get("results", []))
            except Exception as e:
                print(f"  ⚠️ Tavily search failed for '{q}': {e}")
        
        print(f"  ✅ Retrieved {len(all_results)} web search results")
        state["web_search_results"] = all_results
        return state

    def _node_synthesize(self, state: MarketState) -> MarketState:
        """시장성 평가 종합 노드"""
        tech = state["tech_name"]
        pi = state.get("first_item") or {}
        
        title = pi.get("title", "")
        abstract = pi.get("abstract", "")
        patent_id = (
            pi.get("publication_number") or 
            pi.get("patent_id") or 
            pi.get("id") or 
            "UNKNOWN"
        )
        
        rag_docs = state.get("retrieved_docs", [])
        web_results = state.get("web_search_results", [])
        
        # 컨텍스트 구성 (안전하게 처리)
        rag_text = ""
        for doc in rag_docs:
            if hasattr(doc, 'page_content'):
                rag_text += doc.page_content + "\n\n"
            elif isinstance(doc, dict):
                rag_text += doc.get('page_content', '') + "\n\n"
        rag_text = rag_text[:4000]
        
        web_text = ""
        for idx, result in enumerate(web_results[:6]):
            content = result.get("content", "")
            url = result.get("url", "")
            web_text += f"[Web Source {idx+1}] {url}\n{content[:500]}\n\n"
        
        sources = _collect_sources(rag_docs, web_results)

        system = (
            "너는 특허 상업화 분석 전문가다. "
            "특허의 제목과 초록을 **중심**으로 시장성을 평가하며, "
            "RAG 문서와 웹 검색 결과는 **시장 데이터 참고용**으로만 사용한다.\n\n"
            
            "## 정량적 점수 기준\n\n"
            
            "### 1. market_size_score (0~0.4)\n"
            "특허 기술이 **실제로 적용 가능한 세부 시장 규모(SAM)**를 평가:\n"
            "- 0.35~0.4: 적용 가능 시장 $10B 이상 (여러 주요 제품군에 필수)\n"
            "  예: LLM 훈련 인프라 $12B, 자율주행 센서 시장 $15B\n"
            "- 0.25~0.35: 적용 가능 시장 $3B~$10B (특정 주요 제품군의 핵심)\n"
            "  예: 추천시스템 AI 하드웨어 $5B, 음성인식 가속 $4B\n"
            "- 0.15~0.25: 적용 가능 시장 $1B~$3B (특정 Use Case 집중)\n"
            "  예: 특정 모델 최적화 시장 $1.5B\n"
            "- 0.1~0.15: 적용 가능 시장 $300M~$1B (틈새 응용)\n"
            "  예: 의료 영상 전용 NPU $800M\n"
            "- 0.0~0.1: 적용 가능 시장 $300M 미만 (실험적/제한적)\n\n"
            
            "**중요**: 전체 산업 규모(예: AI 반도체 $85B)가 아닌, "
            "해당 특허 기술이 실제 사용될 구체적 세부 시장을 판단\n\n"
            
            "### 2. growth_potential_score (0~0.3)\n"
            "해당 세부 시장의 **CAGR 또는 구체적 성장 수치**:\n"
            "- 0.25~0.3: CAGR 25%+ 또는 향후 5년간 3배+ 성장\n"
            "  예: '2025년 310억 달러 → 2028년 602억 달러' (CAGR 25%)\n"
            "- 0.2~0.25: CAGR 20~25% 또는 2배+ 성장\n"
            "- 0.15~0.2: CAGR 15~20% 또는 1.5배+ 성장\n"
            "- 0.1~0.15: CAGR 10~15%\n"
            "- 0.0~0.1: CAGR 10% 미만 또는 정체\n\n"
            
            "**중요**: 웹 검색 결과에서 구체적 수치(억/조 단위 포함) 우선 활용\n\n"
            
            "### 3. commercialization_readiness (0~0.3)\n"
            "특허 기술의 **상용화 가능 시점과 준비도**:\n"
            "- 0.25~0.3: 즉시~1년 내 적용 가능, 명확한 고객\n"
            "- 0.2~0.25: 1~2년, 프로토타입 검증 완료\n"
            "- 0.15~0.2: 2~3년, 파일럿 단계\n"
            "- 0.1~0.15: 3~5년, 초기 R&D\n"
            "- 0.0~0.1: 5년+, 상업화 경로 불명확\n\n"
            
            "## market_rationale 작성 규칙\n"
            "- 반드시 '이 특허({patent_id})는 ...'로 시작\n"
            "- 5~7문장, 한 문단\n"
            "- 특허 기술 + 적용 시장 규모 + 성장률 + 상용화 준비도 통합 설명\n"
            "- 웹 검색에서 발견한 구체적 수치 인용 (예: '602억 달러', 'CAGR 11%')\n"
            "- 추측 금지, 구체적 근거 기반\n\n"
            
            "출력은 단일 JSON, sources는 작성하지 말 것."
        )

        human = (
            "평가 대상:\n"
            "Patent ID: {patent_id}\n"
            "Title: {title}\n\n"
            "Abstract:\n{abstract}\n\n"
            "=== RAG 로컬 문서 ===\n{rag}\n\n"
            "=== 웹 검색 결과 (Tavily) ===\n{web}\n\n"
            "위 정보를 바탕으로 정량적 점수와 정성적 평가를 포함한 JSON을 생성하라. "
            "특히 웹 검색 결과의 구체적 시장 규모/성장률 수치를 최대한 활용할 것."
        )

        prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
        chain = prompt | self.llm.with_structured_output(_MarketSchema)

        try:
            output: _MarketSchema = chain.invoke({
                "patent_id": patent_id,
                "title": title,
                "abstract": abstract,
                "rag": rag_text,
                "web": web_text[:4000]
            })
            
            # ✅ Sources를 RAG + Tavily로 덮어쓰기
            result = output.model_dump()
            result["sources"] = sources
            
            # market_score 검증 및 재계산
            calculated_score = (
                result["market_size_score"] + 
                result["growth_potential_score"] + 
                result["commercialization_readiness"]
            )
            result["market_score"] = round(calculated_score, 3)
            
            # MarketState에 결과 저장
            state["patent_id"] = patent_id
            state["patent_title"] = title
            state["market_size_score"] = result["market_size_score"]
            state["growth_potential_score"] = result["growth_potential_score"]
            state["commercialization_readiness"] = result["commercialization_readiness"]
            state["market_score"] = result["market_score"]
            state["application_domains"] = result["application_domains"]
            state["commercialization_potential"] = result["commercialization_potential"]
            state["market_rationale"] = result["market_rationale"]
            state["demand_signals"] = result["demand_signals"]
            state["sources"] = sources
            
            print(f"  ✅ Evaluation complete:")
            print(f"     - Potential: {output.commercialization_potential}")
            print(f"     - Total Score: {result['market_score']:.3f}")
            print(f"     - Sources: {len(sources)} items")
            
        except Exception as e:
            print(f"  ❌ Synthesis failed: {e}")
            state["patent_id"] = patent_id
            state["patent_title"] = title
            state["error"] = str(e)
            state["market_score"] = 0.0
            state["sources"] = sources
        
        return state

    def evaluate_market(self) -> Dict[str, Any]:
        """시장성 평가 실행"""
        print("=" * 80)
        print(f"🚀 Patent Market Evaluation (RAG + Tavily): {self.tech_name}")
        print("=" * 80)

        title = self.patent_info.get("title", "")
        abstract = self.patent_info.get("abstract", "")
        
        # Abstract에서 핵심 기술 키워드 추출
        print("📝 Extracting key technical terms from abstract...")
        keyterms = _extract_keyterms_from_abstract(
            self.llm, title, abstract, max_terms=8
        )
        print(f"  ✅ Extracted keyterms: {keyterms}")
        
        # RAG 검색 쿼리 구성
        query = _build_rag_query(self.tech_name, keyterms)
        print(f"  🔎 RAG query: {query}")

        # State 초기화
        init_state: MarketState = {
            "query": query,
            "tech_name": self.tech_name,
            "first_item": self.patent_info,  # MarketState의 first_item 필드 사용
            "keyterms": keyterms,
            "retrieved_docs": [],
            "web_search_results": [],
        }

        # Graph 실행
        final_state = self.graph.invoke(
            init_state,
            config={"configurable": {"thread_id": f"market-eval-{self.tech_name}"}}
        )

        # 결과를 dict로 변환
        result = {
            "tech_name": final_state.get("tech_name"),
            "patent_id": final_state.get("patent_id"),
            "patent_title": final_state.get("patent_title"),
            "market_size_score": final_state.get("market_size_score", 0.0),
            "growth_potential_score": final_state.get("growth_potential_score", 0.0),
            "commercialization_readiness": final_state.get("commercialization_readiness", 0.0),
            "market_score": final_state.get("market_score", 0.0),
            "application_domains": final_state.get("application_domains", []),
            "commercialization_potential": final_state.get("commercialization_potential", "Low"),
            "market_rationale": final_state.get("market_rationale", ""),
            "demand_signals": final_state.get("demand_signals", []),
            "sources": final_state.get("sources", []),
            "error": final_state.get("error"),
        }
        
        # 결과 저장
        output_path = self._save(result)
        result["market_output_path"] = str(output_path)

        print("=" * 80)
        print("📊 Final Market Evaluation Result")
        print("=" * 80)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        return result

    def _save(self, result: Dict[str, Any]) -> Path:
        """결과를 JSON 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"market_eval_{self.tech_name}_{timestamp}.json"
        output_path = self.output_dir / filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Saved to: {output_path}")
        return output_path


# ===== CLI =====
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="시장성 평가 Agent (RAG + Tavily Web Search)"
    )
    parser.add_argument("tech_name", type=str, help="기술 키워드 (예: NPU, AI accelerator)")
    parser.add_argument("--patent-json", type=str, required=True, help="특허 정보 JSON 파일 경로")
    args = parser.parse_args()

    # 특허 정보 로드
    with open(args.patent_json, "r", encoding="utf-8") as f:
        patent_data = json.load(f)
    
    first_patent = (patent_data.get("items") or [{}])[0]

    # Agent 실행
    agent = MarketSizeGrowthAgent(args.tech_name, first_patent)
    agent.evaluate_market()