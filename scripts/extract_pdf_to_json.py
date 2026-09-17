"""
Script trích xuất toàn bộ dữ liệu PDF slides thành file JSON (slides_data.json)
Giúp hệ thống hoạt động 100% offline không phụ thuộc vào pypdf/pymupdf khi khởi chạy.
"""

import json
import sys
from pathlib import Path

# Đảm bảo UTF-8
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
SLIDES_DIR = BASE_DIR / "Data" / "vlearn-pack" / "slides"
OUTPUT_FILE = BASE_DIR / "Data" / "vlearn-pack" / "slides_data.json"

def extract_all_slides():
    results = {}

    pdf_files = {
        "d1": SLIDES_DIR / "d1-slide-hackathon.pdf",
        "d2": SLIDES_DIR / "d2-slide-hackathon.pdf"
    }

    try:
        import pymupdf
        has_pymupdf = True
    except ImportError:
        has_pymupdf = False

    try:
        import pypdf
        has_pypdf = True
    except ImportError:
        has_pypdf = False

    for deck_id, pdf_path in pdf_files.items():
        if not pdf_path.exists():
            print(f"[Warning] Không tìm thấy file: {pdf_path}")
            continue

        deck_data = {
            "deck_id": deck_id,
            "filename": pdf_path.name,
            "total_pages": 0,
            "pages": {}
        }

        if has_pymupdf:
            try:
                doc = pymupdf.open(str(pdf_path))
                deck_data["total_pages"] = len(doc)
                for page_num in range(1, len(doc) + 1):
                    page = doc.load_page(page_num - 1)
                    text = page.get_text("text") or ""
                    clean_text = " ".join(text.split())
                    deck_data["pages"][str(page_num)] = {
                        "page": page_num,
                        "text": clean_text
                    }
                print(f"[PyMuPDF] Trích xuất thành công {deck_data['total_pages']} trang cho {deck_id}")
            except Exception as e:
                print(f"[PyMuPDF Error] {e}")

        elif has_pypdf:
            try:
                reader = pypdf.PdfReader(str(pdf_path))
                deck_data["total_pages"] = len(reader.pages)
                for page_num in range(1, len(reader.pages) + 1):
                    page = reader.pages[page_num - 1]
                    text = page.extract_text() or ""
                    clean_text = " ".join(text.split())
                    deck_data["pages"][str(page_num)] = {
                        "page": page_num,
                        "text": clean_text
                    }
                print(f"[PyPDF] Trích xuất thành công {deck_data['total_pages']} trang cho {deck_id}")
            except Exception as e:
                print(f"[PyPDF Error] {e}")

        results[deck_id] = deck_data

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Đã lưu dữ liệu slides PDF vào: {OUTPUT_FILE}")
    print(f"Tổng dung lượng JSON: {OUTPUT_FILE.stat().st_size} bytes")

if __name__ == "__main__":
    extract_all_slides()
