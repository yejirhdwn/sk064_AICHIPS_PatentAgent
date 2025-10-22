"""
Build Patent Market RAG Index (Chroma) - PDF 직접 로드 (RAG 폴더 기준 실행)
품질 개선:
- bge-m3 임베딩(다국어 강함) 기본값
- 텍스트 정규화 후 청크
- 유사도 점수(similarity_search_with_score) + 중복 제거
- 페이지/청크/점수 출력
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_chroma import Chroma
# ⚠️ Deprecation 대응: langchain_ollama 우선, 없으면 community로 폴백
try:
    from langchain_ollama import OllamaEmbeddings  # pip install langchain-ollama
except Exception:
    from langchain_community.embeddings import OllamaEmbeddings

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

# 환경변수 로드
load_dotenv()


# -------------------------------------------------------------
# 1) PDF 경로 자동 정규화 (항상 프로젝트 루트 기준)
# -------------------------------------------------------------
def resolve_repo_path(p: str | Path) -> Path:
    p = Path(p)
    if p.is_absolute():
        return p
    repo_root = Path(__file__).resolve().parents[1]
    return (repo_root / p).resolve()


# -------------------------------------------------------------
# 2) 텍스트 정규화 유틸 (PDF 노이즈 제거)
# -------------------------------------------------------------
def normalize_text(t: str) -> str:
    if not t:
        return t
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"-\s*\n\s*", "", t)      # 하이픈 줄바꿈 연결 제거
    t = t.replace("\r", "")
    t = re.sub(r"\s*\n\s*", " ", t)      # 개행 → 공백
    t = re.sub(r"[ \t]+", " ", t)        # 중복 공백 축소
    return t.strip()


# -------------------------------------------------------------
# 3) PDF 로드
# -------------------------------------------------------------
def load_pdf_document(pdf_path: str) -> List[Document]:
    documents: List[Document] = []
    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        print(f"❌ PDF file not found: {pdf_file}")
        return documents

    print(f"📄 Loading PDF: {pdf_file.name}")
    try:
        loader = PyPDFLoader(str(pdf_file))
        docs = loader.load()

        for doc in docs:
            doc.page_content = normalize_text(doc.page_content)
            doc.metadata["source"] = str(pdf_file)
            doc.metadata["filename"] = pdf_file.name
            doc.metadata["extension"] = ".pdf"
            if "page" not in doc.metadata:
                doc.metadata["page"] = None

        documents.extend(docs)
        print(f"  ✅ Loaded {len(docs)} pages from PDF")

    except Exception as e:
        print(f"  ⚠️ Failed to load PDF: {e}")

    return documents


# -------------------------------------------------------------
# 4) 문서 분할 (+chunk_id, page 보존)
# -------------------------------------------------------------
def split_documents(documents: List[Document], chunk_size: int = 800, chunk_overlap: int = 250) -> List[Document]:
    if not documents:
        return []

    print(f"\n✂️ Splitting documents (chunk_size={chunk_size}, overlap={chunk_overlap})...")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    split_docs = splitter.split_documents(documents)

    for i, d in enumerate(split_docs):
        d.page_content = normalize_text(d.page_content)
        d.metadata["chunk_id"] = i
        if "page" not in d.metadata:
            d.metadata["page"] = None

    print(f"📄 Total chunks: {len(split_docs)}")
    return split_docs


# -------------------------------------------------------------
# 5) 검색 결과 중복 제거
# -------------------------------------------------------------
def dedupe_results(results: List[Tuple[Document, float]], max_items: int = 3) -> List[Tuple[Document, float]]:
    """같은 페이지·chunk 또는 거의 동일한 스니펫은 제거"""
    seen = set()
    out: List[Tuple[Document, float]] = []
    for doc, score in results:
        page = doc.metadata.get("page")
        chunk_id = doc.metadata.get("chunk_id")
        key = (page, chunk_id)
        snippet_key = normalize_text(doc.page_content[:160])
        if key in seen or snippet_key in seen:
            continue
        seen.add(key)
        seen.add(snippet_key)
        out.append((doc, score))
        if len(out) >= max_items:
            break
    return out


# -------------------------------------------------------------
# 6) Chroma 인덱스 구축
# -------------------------------------------------------------
def build_chroma_index(
    pdf_path: str = "data/품목별ICT시장동향_AI반도체.pdf",
    collection_name: str = "patent_market_index",
    chroma_dir: str = "./chroma",
    embedding_model: str = "bge-m3",   # 다국어 임베딩
    chunk_size: int = 800,
    chunk_overlap: int = 250,
) -> None:

    print("=" * 80)
    print("🚀 Starting Patent Market RAG Index Build")
    print("=" * 80)

    # ✅ 경로 정규화
    pdf_path = str(resolve_repo_path(pdf_path))
    print(f"📂 Current working dir: {Path().resolve()}")
    print(f"📄 Resolved PDF path:   {pdf_path}")

    # 1) PDF 로드
    documents = load_pdf_document(pdf_path)
    if not documents:
        print("\n❌ No documents loaded. Please check the PDF path.")
        return

    # 2) 문서 분할
    split_docs = split_documents(documents, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not split_docs:
        print("\n❌ No chunks created.")
        return

    # 3) 임베딩 모델
    print(f"\n🤖 Initializing embedding model: {embedding_model}")
    embeddings = OllamaEmbeddings(model=embedding_model)

    # 4) Chroma 생성/초기화
    chroma_path = Path(chroma_dir)
    chroma_path.mkdir(parents=True, exist_ok=True)

    print(f"\n💾 Creating Chroma vector store...")
    print(f"  Collection: {collection_name}")
    print(f"  Persist dir: {chroma_path.resolve()}")

    try:
        temp_vs = Chroma(
            collection_name=collection_name,
            persist_directory=str(chroma_path),
            embedding_function=embeddings,
        )
        temp_vs.delete_collection()
        print(f"  ♻️ Deleted existing collection: {collection_name}")
    except Exception:
        pass

    vectorstore = Chroma.from_documents(
        documents=split_docs,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=str(chroma_path),
    )

    print(f"\n✅ Index build completed!")
    print(f"  Total chunks indexed: {len(split_docs)}")
    print(f"  Collection name: {collection_name}")
    print(f"  Persist directory: {chroma_path}")

    # 5) 테스트 쿼리 (유사도 점수 + 중복 제거, 페이지/청크/점수 출력)
    print(f"\n🔍 Testing retrieval with sample query...")
    test_queries = [
        "HBM AI 반도체 시장 규모",
        "HBM 채택이 데이터센터 시장에 미치는 영향",
    ]

    for q in test_queries:
        # 점수 포함 검색 (버전 호환 안정)
        raw_results = vectorstore.similarity_search_with_score(q, k=12)  # 넓게 뽑고
        results = dedupe_results(raw_results, max_items=3)               # 중복 제거 후 상위 3개

        print(f"\nTop 3 results for '{q}':")
        if not results:
            print("  (no result)")
            continue

        for rank, (doc, score) in enumerate(results, 1):
            page0 = doc.metadata.get("page")
            page_disp = (page0 + 1) if isinstance(page0, int) else "?"
            chunk_id = doc.metadata.get("chunk_id", "?")
            src = doc.metadata.get("source", "N/A")
            preview = doc.page_content.replace("\n", " ")
            print(f"  [{rank}] (score={score:.4f}) p.{page_disp}  chunk#{chunk_id}")
            print(f"      {preview[:350]}...")
            print(f"      Source: {src}")

    print("\n" + "=" * 80)
    print("✅ RAG Index Build Complete!")
    print("=" * 80)


# -------------------------------------------------------------
# 7) CLI 실행
# -------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build Patent Market RAG Index from PDF (RAG 폴더 기준)")
    parser.add_argument("--pdf-path", type=str, default="data/품목별ICT시장동향_AI반도체.pdf")
    parser.add_argument("--collection", type=str, default="patent_market_index")
    parser.add_argument("--chroma-dir", type=str, default="./chroma")
    parser.add_argument("--embedding-model", type=str, default="bge-m3")  # ← 필요시 변경
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--chunk-overlap", type=int, default=250)

    args = parser.parse_args()

    build_chroma_index(
        pdf_path=args.pdf_path,
        collection_name=args.collection,
        chroma_dir=args.chroma_dir,
        embedding_model=args.embedding_model,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
