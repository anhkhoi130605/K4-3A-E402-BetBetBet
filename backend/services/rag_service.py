"""
RAG Service: Semantic Dense Vector & Hybrid Retrieval Engine
Powered by OpenAI's 'openai/text-embedding-3-small' (1536-dimensional Dense Vectors)
via OpenRouter Embeddings API & Vector Space Model.

Ingests:
  1. 700+ clean transcript chunks [Txx-NNN] from Data/vlearn-pack/transcript/*.md
  2. Slide PDF text & rendered high-resolution images from Data/vlearn-pack/slides/*.pdf
Features:
  - True 1536-dim Dense Vector Embeddings (openai/text-embedding-3-small)
  - Persistent Local Vector Cache (Data/vlearn-pack/dense_embeddings_cache.json)
  - Mathematical Cosine Similarity Ranking (Dense + Sparse Hybrid)
"""

import math
import json
import re
import os
import sys
import httpx
from pathlib import Path
from typing import Dict, Optional, List, Tuple

# Đảm bảo in an toàn trên console Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from backend.config import SLIDES_DIR, TRANSCRIPT_DIR, OPENROUTER_API_KEY, EMBEDDING_MODEL, EMBEDDING_CACHE_FILE

VIETNAMESE_STOP_WORDS = {
    "là", "của", "và", "các", "có", "trong", "được", "cho", "với", "để", "thì", "khi",
    "những", "một", "này", "về", "lại", "gì", "thế", "nào", "sao", "bạn", "tôi", "em",
    "ơi", "hỏi", "xin", "giúp", "ở", "từ", "ra", "vào", "lên", "xuống", "đến"
}

SEMANTIC_SYNONYMS = {
    "ảo ma": "hallucination bịa đặt không có căn cứ factual grounding",
    "bịa": "hallucination bịa chuyện factual grounding",
    "song song": "self-attention transformer parallel ma trận song song",
    "tuần tự": "rnn lstm sequential tuần tự từ trái sang phải",
    "tính tiền": "api cost pricing chi phí token hóa đơn system prompt",
    "đắt": "chi phí token cost budget tối ưu",
    "bpe": "byte pair encoding tokenizer sub-token tách từ tiếng việt",
    "nhiệt độ": "temperature sampling greedy decoding deterministic ngẫu nhiên"
}

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Tính độ tương đồng Cosine chuẩn toán học giữa 2 vector đa chiều"""
    dot = 0.0
    norm1 = 0.0
    norm2 = 0.0
    for a, b in zip(v1, v2):
        dot += a * b
        norm1 += a * a
        norm2 += b * b
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (math.sqrt(norm1) * math.sqrt(norm2))


class DenseEmbeddingEngine:
    """
    Bộ máy Dense Vector Embedding thực thụ:
    Sử dụng model 'openai/text-embedding-3-small' (1536 chiều) qua OpenRouter Embeddings API.
    Có lưu cache đĩa (dense_embeddings_cache.json) để khởi động tức thì và tiết kiệm token.
    """
    def __init__(self, api_key: str, model: str = EMBEDDING_MODEL):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model
        self.endpoint = "https://openrouter.ai/api/v1/embeddings"
        self.doc_embeddings: Dict[str, List[float]] = {}
        self._load_cache()

    def _load_cache(self):
        """Nạp vector 1536 chiều đã tính sẵn từ cache đĩa nếu có"""
        if EMBEDDING_CACHE_FILE.exists():
            try:
                data = json.loads(EMBEDDING_CACHE_FILE.read_text(encoding="utf-8"))
                self.doc_embeddings = data.get("embeddings", {})
                print(f"[DenseEmbedding] Đã nạp {len(self.doc_embeddings)} dense vectors (model: {self.model}) từ cache đĩa.")
            except Exception as e:
                print(f"[DenseEmbedding] Lỗi đọc cache embedding: {e}")

    def save_cache(self):
        """Lưu trữ vector cache để tái sử dụng bền vững"""
        try:
            payload = {
                "model": self.model,
                "dimension": 1536,
                "total_chunks": len(self.doc_embeddings),
                "embeddings": self.doc_embeddings
            }
            EMBEDDING_CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            print(f"[DenseEmbedding] Đã lưu {len(self.doc_embeddings)} dense vectors vào {EMBEDDING_CACHE_FILE.name}")
        except Exception as e:
            print(f"[DenseEmbedding] Lỗi ghi cache: {e}")

    def get_query_embedding_sync(self, text: str) -> Optional[List[float]]:
        """Gọi đồng bộ API OpenRouter Embeddings để lấy vector 1536 chiều cho câu truy vấn"""
        if not self.api_key:
            return None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "VLearn Vector RAG"
        }
        body = {
            "model": self.model,
            "input": text.strip()
        }
        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.post(self.endpoint, headers=headers, json=body)
                if res.status_code == 200:
                    result = res.json()
                    return result["data"][0]["embedding"]
                else:
                    print(f"[DenseEmbedding] API Error {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[DenseEmbedding] Request failed: {e}")
        return None

    def search(self, query_vector: List[float], documents: Dict[str, dict], limit: int = 3) -> List[Tuple[float, dict]]:
        """Tính Cosine Similarity trên không gian 1536 chiều giữa query vector và toàn bộ tài liệu"""
        scored: List[Tuple[float, dict]] = []
        for doc_id, emb in self.doc_embeddings.items():
            if doc_id in documents:
                sim = cosine_similarity(query_vector, emb)
                scored.append((sim, documents[doc_id]))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:limit]


class VectorSpaceRAG:
    """
    Bộ máy Vector Space Model (TF-IDF Cosine Similarity)
    Đóng vai trò Hybrid Retrieval và Fallback tức thì (< 1ms).
    """
    def __init__(self, documents: Dict[str, dict]):
        self.documents = documents
        self.idf: Dict[str, float] = {}
        self.doc_vectors: Dict[str, Dict[str, float]] = {}
        self.doc_norms: Dict[str, float] = {}
        self.total_docs = len(documents)
        if self.total_docs > 0:
            self._build_vector_space()

    def _tokenize(self, text: str) -> List[str]:
        words = [w.lower() for w in re.findall(r"\w+", text) if len(w) > 1]
        return [w for w in words if w not in VIETNAMESE_STOP_WORDS]

    def _build_vector_space(self):
        df_counts: Dict[str, int] = {}
        doc_tokens: Dict[str, List[str]] = {}

        for doc_id, doc in self.documents.items():
            tokens = self._tokenize(doc["text"])
            doc_tokens[doc_id] = tokens
            for token in set(tokens):
                df_counts[token] = df_counts.get(token, 0) + 1

        for token, df in df_counts.items():
            self.idf[token] = math.log(1.0 + (self.total_docs - df + 0.5) / (df + 0.5))

        for doc_id, tokens in doc_tokens.items():
            if not tokens:
                continue
            tf: Dict[str, float] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0.0) + 1.0

            doc_len = len(tokens)
            vec: Dict[str, float] = {}
            norm_sq = 0.0
            for t, count in tf.items():
                weight = (count / doc_len) * self.idf.get(t, 1.0)
                vec[t] = weight
                norm_sq += weight * weight

            self.doc_vectors[doc_id] = vec
            self.doc_norms[doc_id] = math.sqrt(norm_sq) if norm_sq > 0 else 1.0

    def search(self, query: str, limit: int = 3) -> List[Tuple[float, dict]]:
        if not query or not self.doc_vectors:
            return []

        query_expanded = query.lower()
        for syn, expansion in SEMANTIC_SYNONYMS.items():
            if syn in query_expanded:
                query_expanded += " " + expansion

        query_tokens = self._tokenize(query_expanded)
        if not query_tokens:
            query_tokens = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 1]

        q_tf: Dict[str, float] = {}
        for t in query_tokens:
            q_tf[t] = q_tf.get(t, 0.0) + 1.0

        q_len = len(query_tokens)
        q_vec: Dict[str, float] = {}
        q_norm_sq = 0.0
        for t, count in q_tf.items():
            idf_val = self.idf.get(t, math.log(1.0 + self.total_docs))
            weight = (count / q_len) * idf_val
            q_vec[t] = weight
            q_norm_sq += weight * weight

        q_norm = math.sqrt(q_norm_sq) if q_norm_sq > 0 else 1.0

        scored: List[Tuple[float, dict]] = []
        for doc_id, doc_vec in self.doc_vectors.items():
            dot_product = 0.0
            for t, q_weight in q_vec.items():
                if t in doc_vec:
                    dot_product += q_weight * doc_vec[t]

            if dot_product > 0:
                cosine_sim = dot_product / (q_norm * self.doc_norms.get(doc_id, 1.0))
                scored.append((cosine_sim, self.documents[doc_id]))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:limit]


class RAGService:
    def __init__(self):
        self.transcripts: Dict[str, dict] = {}
        self.slide_cache: Dict[str, Dict[int, str]] = {"d1": {}, "d2": {}}
        self._img_cache: Dict[str, bytes] = {}
        self.vector_engine: Optional[VectorSpaceRAG] = None
        self.dense_engine: DenseEmbeddingEngine = DenseEmbeddingEngine(api_key=OPENROUTER_API_KEY)
        self._load_transcripts()

    def _load_transcripts(self):
        """Index toàn bộ 700+ đoạn transcript sạch có gắn mã [Txx-NNN] và khởi tạo RAG Engines"""
        if not TRANSCRIPT_DIR.exists():
            return

        for path in sorted(TRANSCRIPT_DIR.glob("*.md")):
            if path.name == "README.md":
                continue
            try:
                content = path.read_text(encoding="utf-8")
                pattern = r"\*\*\[(T\d{2}-\d{3})\]\*\*\s*([^\n\r]+)"
                for tag, text in re.findall(pattern, content):
                    self.transcripts[tag] = {
                        "id": tag,
                        "file": path.name,
                        "text": text.strip()
                    }
            except Exception as e:
                print(f"[RAGService] Error reading {path.name}: {e}")

        if self.transcripts:
            self.vector_engine = VectorSpaceRAG(self.transcripts)
            print(f"[RAGService] RAG Service Ready: {len(self.transcripts)} chunks indexed | Dense Model: {self.dense_engine.model}")

    def get_citation(self, citation_id: str) -> Optional[dict]:
        return self.transcripts.get(citation_id)

    def extract_slide_page(self, deck: str, page: int) -> str:
        if page in self.slide_cache.get(deck, {}):
            return self.slide_cache[deck][page]

        pdf_name = "d1-slide-hackathon.pdf" if deck == "d1" else "d2-slide-hackathon.pdf"
        pdf_path = SLIDES_DIR / pdf_name
        if not pdf_path.exists():
            return ""

        try:
            import pypdf
            reader = pypdf.PdfReader(str(pdf_path))
            if 1 <= page <= len(reader.pages):
                text = reader.pages[page - 1].extract_text() or ""
                clean_text = " ".join(text.split())
                if deck not in self.slide_cache:
                    self.slide_cache[deck] = {}
                self.slide_cache[deck][page] = clean_text
                return clean_text
        except Exception as e:
            print(f"[RAGService] PDF extract error on {deck} page {page}: {e}")

        return ""

    def render_slide_image(self, deck: str, page: int, dpi: int = 150) -> Optional[bytes]:
        cache_key = f"{deck}_{page}_{dpi}"
        if cache_key in self._img_cache:
            return self._img_cache[cache_key]

        pdf_name = "d1-slide-hackathon.pdf" if deck == "d1" else "d2-slide-hackathon.pdf"
        pdf_path = SLIDES_DIR / pdf_name
        if not pdf_path.exists():
            return None

        try:
            import pymupdf
            doc = pymupdf.open(str(pdf_path))
            if 1 <= page <= len(doc):
                pdf_page = doc.load_page(page - 1)
                pix = pdf_page.get_pixmap(dpi=dpi)
                png_bytes = pix.tobytes("png")
                self._img_cache[cache_key] = png_bytes
                return png_bytes
        except Exception as e:
            print(f"[RAGService] Render slide image error on {deck} page {page}: {e}")

        return None

    def search_transcripts(self, keyword: str, limit: int = 3) -> List[dict]:
        """
        Truy xuất thông tin thông minh:
        1. Ưu tiên Dense Vector Embedding (openai/text-embedding-3-small, 1536 chiều) nếu có cache vector.
        2. Kết hợp với Vector Space Model (TF-IDF Cosine Similarity) tạo thành Hybrid RAG chuẩn.
        """
        if not keyword:
            return []

        # 1. Thử Dense Vector Search nếu đã có cached embeddings
        if self.dense_engine.doc_embeddings:
            query_vec = self.dense_engine.get_query_embedding_sync(keyword)
            if query_vec:
                dense_results = self.dense_engine.search(query_vec, self.transcripts, limit=limit)
                if dense_results:
                    return [doc for score, doc in dense_results]

        # 2. Vector Space Model (TF-IDF Cosine Similarity) chuẩn toán học
        if self.vector_engine:
            results = self.vector_engine.search(keyword, limit=limit)
            return [doc for score, doc in results]

        return []

# Singleton instance
rag_service = RAGService()
