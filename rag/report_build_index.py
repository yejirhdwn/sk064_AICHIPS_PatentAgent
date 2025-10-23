"""
Report Build Index - AI 반도체 시장 보고서 RAG 인덱스 생성
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Any
import json

try:
    from langchain_community.document_loaders import PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings
    from langchain.schema import Document
    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False
    print("⚠️ Install: pip install langchain langchain-community langchain-openai faiss-cpu pypdf")


def get_project_root() -> Path:
    """프로젝트 루트 디렉토리 찾기 (Windows/Linux 호환)"""
    current = Path(__file__).resolve()
    
    # rag/ 디렉토리에서 실행된 경우
    if current.parent.name == 'rag':
        return current.parent.parent
    
    # 프로젝트 루트에서 실행된 경우
    return current.parent


class ReportIndexBuilder:
    """AI 반도체 시장 보고서 RAG 인덱스 빌더"""
    
    def __init__(
        self,
        pdf_path: str = None,
        index_dir: str = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        if not _HAS_LANGCHAIN:
            raise ImportError("LangChain is required")
        
        # 프로젝트 루트
        self.project_root = get_project_root()
        
        # PDF 경로
        if pdf_path is None:
            pdf_path = self.project_root / "data" / "AI반도체시장현황및전망.pdf"
        self.pdf_path = Path(pdf_path)
        
        # 인덱스 디렉토리
        if index_dir is None:
            index_dir = self.project_root / "rag" / "indexes"
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.environ.get("OPENAI_API_KEY")
        )
        
        self.vectorstore = None
        self.documents = []
    
    def load_pdf(self) -> List[Document]:
        """PDF 로드"""
        print(f"📄 Loading PDF: {self.pdf_path}")
        print(f"   Absolute: {self.pdf_path.resolve()}")
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(
                f"\n❌ PDF not found!\n"
                f"Expected: {self.pdf_path}\n"
                f"Absolute: {self.pdf_path.resolve()}\n"
            )
        
        loader = PyPDFLoader(str(self.pdf_path))
        documents = loader.load()
        
        print(f"✅ Loaded {len(documents)} pages")
        return documents
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """문서 분할"""
        print(f"✂️ Splitting (size={self.chunk_size}, overlap={self.chunk_overlap})")
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", ".", " ", ""]
        )
        
        chunks = splitter.split_documents(documents)
        print(f"✅ Created {len(chunks)} chunks")
        return chunks
    
    def build_index(self, force_rebuild: bool = False) -> FAISS:
        """인덱스 생성/로드"""
        index_path = self.index_dir / "ai_chip_market"
        
        # 기존 인덱스 로드
        if not force_rebuild and index_path.exists():
            print(f"📦 Loading from {index_path}")
            self.vectorstore = FAISS.load_local(
                str(index_path),
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            print("✅ Loaded")
            return self.vectorstore
        
        # 새 인덱스 생성
        print("🏗️ Building new index...")
        documents = self.load_pdf()
        self.documents = self.split_documents(documents)
        
        print("🔢 Creating embeddings...")
        self.vectorstore = FAISS.from_documents(self.documents, self.embeddings)
        
        print(f"💾 Saving to {index_path}")
        self.vectorstore.save_local(str(index_path))
        
        # 메타데이터
        metadata = {
            "pdf_path": str(self.pdf_path),
            "total_pages": len(documents),
            "total_chunks": len(self.documents),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap
        }
        
        with open(self.index_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print("✅ Built and saved")
        return self.vectorstore


class ReportRAGRetriever:
    """Report Agent용 검색기"""
    
    def __init__(self, index_dir: str = None):
        if not _HAS_LANGCHAIN:
            raise ImportError("LangChain required")
        
        project_root = get_project_root()
        
        if index_dir is None:
            index_dir = project_root / "rag" / "indexes"
        
        self.index_dir = Path(index_dir)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.environ.get("OPENAI_API_KEY")
        )
        
        index_path = self.index_dir / "ai_chip_market"
        if not index_path.exists():
            raise FileNotFoundError(f"Index not found: {index_path}")
        
        self.vectorstore = FAISS.load_local(
            str(index_path),
            self.embeddings,
            allow_dangerous_deserialization=True
        )
    
    def retrieve_industry_context(self, k: int = 3) -> str:
        queries = ["AI 반도체 시장 규모", "AI 반도체 산업 동향"]
        results = []
        for q in queries:
            results.extend([d.page_content for d in self.vectorstore.similarity_search(q, k=k)])
        return "\n\n".join(list(dict.fromkeys(results))[:5])
    
    def retrieve_policy_context(self, k: int = 3) -> str:
        queries = ["주요국 AI 반도체 정책", "반도체 지원 정책"]
        results = []
        for q in queries:
            results.extend([d.page_content for d in self.vectorstore.similarity_search(q, k=k)])
        return "\n\n".join(list(dict.fromkeys(results))[:5])
    
    def retrieve_korea_position(self, k: int = 3) -> str:
        queries = ["한국 AI 반도체 경쟁력", "한국 반도체 현황"]
        results = []
        for q in queries:
            results.extend([d.page_content for d in self.vectorstore.similarity_search(q, k=k)])
        return "\n\n".join(list(dict.fromkeys(results))[:3])


def main():
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("\n" + "="*80)
    print("🏗️ Report Index Builder")
    print("="*80)
    
    root = get_project_root()
    print(f"\n📁 Project Root: {root}")
    
    pdf = root / "data" / "AI반도체시장현황및전망.pdf"
    print(f"📄 PDF: {pdf}")
    print(f"   Exists: {pdf.exists()}")
    
    if not pdf.exists():
        print(f"\n❌ PDF not found!")
        print(f"   Expected: {pdf}")
        print(f"   Absolute: {pdf.resolve()}")
        print(f"\n💡 해결 방법:")
        print(f"   1. PDF를 다음 위치에 배치: {root / 'data'}")
        print(f"   2. 파일명 확인: AI반도체시장현황및전망.pdf")
        
        data_dir = root / "data"
        if not data_dir.exists():
            print(f"\n🔧 Creating: {data_dir}")
            data_dir.mkdir(parents=True, exist_ok=True)
        
        sys.exit(1)
    
    try:
        builder = ReportIndexBuilder()
        builder.build_index(force_rebuild=False)
        
        print("\n" + "="*80)
        print("🧪 Testing")
        print("="*80)
        
        retriever = ReportRAGRetriever()
        
        print("\n1️⃣ Industry:")
        print(retriever.retrieve_industry_context()[:200] + "...")
        
        print("\n2️⃣ Policy:")
        print(retriever.retrieve_policy_context()[:200] + "...")
        
        print("\n3️⃣ Korea:")
        print(retriever.retrieve_korea_position()[:200] + "...")
        
        print("\n" + "="*80)
        print("✅ Success!")
        print("="*80)
        print(f"📦 Index: {root / 'rag' / 'indexes' / 'ai_chip_market'}")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()