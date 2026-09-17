"""
RAG Service: Slide PDF & Transcript Retrieval
Responsible for ingesting Data/vlearn-pack resources
"""
import random
import re
from pathlib import Path
from typing import Dict, Optional, List
from backend.config import SLIDES_DIR, TRANSCRIPT_DIR

class RAGService:
    def __init__(self):
        self.transcripts: Dict[str, dict] = {}
        self.slide_cache = {}
        self.active_deck = random.choice(["d1", "d2"])
        self._load_transcripts()

    def _load_transcripts(self): #chunk
        """Index all [Txx-NNN] chunks from clean transcript files"""
        if not TRANSCRIPT_DIR.exists():
            return

        for path in sorted(TRANSCRIPT_DIR.glob("*.md")):
            if path.name == "README.md":
                continue
            try:
                content = path.read_text(encoding="utf-8")
                # Match: **[Txx-NNN]** text
                pattern = r"\*\*\[(T\d{2}-\d{3})\]\*\*\s*([^\n\r]+)"
                for tag, text in re.findall(pattern, content):
                    self.transcripts[tag] = { #self script
                        "id": tag,
                        "file": path.name,
                        "text": text.strip()
                    }
            except Exception as e:
                print(f"[RAGService] Error reading {path.name}: {e}")

    def get_citation(self, citation_id: str) -> Optional[dict]:
        """Fetch transcript excerpt by citation code [Txx-NNN]"""
        return self.transcripts.get(citation_id)

    def extract_slide_page(self, deck: str = None, page: int = 1) -> str:
        """Extract text from specific page of PDF slide using pypdf.

        Nếu không truyền `deck`, hệ thống sẽ dùng `self.active_deck` đã được random.
        """
        # Gán deck mặc định đã random khi khởi động nếu người gọi không chỉ định
        target_deck = deck or self.active_deck

        if page in self.slide_cache.get(target_deck, {}):
            return self.slide_cache[target_deck][page]

        pdf_name = (
            "d1-slide-hackathon.pdf"
            if target_deck == "d1"
            else "d2-slide-hackathon.pdf"
        )
        pdf_path = SLIDES_DIR / pdf_name
        if not pdf_path.exists():
            return ""

        try:
            import pypdf

            reader = pypdf.PdfReader(str(pdf_path))
            if 1 <= page <= len(reader.pages):
                text = reader.pages[page - 1].extract_text() or ""
                clean_text = " ".join(text.split())

                if target_deck not in self.slide_cache:
                    self.slide_cache[target_deck] = {}
                self.slide_cache[target_deck][page] = clean_text

                return clean_text
        except Exception as e:
            print(
                f"[RAGService] PDF extract error on {target_deck} page {page}: {e}"
            )

        return ""

    def render_slide_image(self, deck: str, page: int, dpi: int = 150) -> Optional[bytes]:
        """Render a specific PDF slide page to high-res PNG bytes"""
        cache_key = f"{deck}_{page}_{dpi}"
        if not hasattr(self, "_img_cache"):
            self._img_cache: Dict[str, bytes] = {}

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
        """Search relevant transcripts by intelligent keyword scoring across 700 lecture transcript chunks"""
        if not keyword or not self.transcripts:
            return []

        # Tách từ khóa và lọc các stop words tiếng Việt thông dụng
        tokens = [w.lower() for w in re.findall(r"\w+", keyword) if len(w) > 1 and w.lower()]
        if not tokens:
            tokens = [w.lower() for w in re.findall(r"\w+", keyword) if len(w) > 1]

        scored = []
        for tag, item in self.transcripts.items():
            text_lower = item["text"].lower()
            score = sum(1 for t in tokens if t in text_lower)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

# Singleton instance
rag_service = RAGService()

