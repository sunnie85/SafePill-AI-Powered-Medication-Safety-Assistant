"""Thử riêng từng công cụ đọc ảnh để biết cái nào hỏng và hỏng vì sao.
Chạy ở thư mục dự án (cùng chỗ với openvino_ocr_helper.py):
    python check_engines.py <khoa_gemini> don_thuoc.jpg
"""
import sys, traceback

key = sys.argv[1] if len(sys.argv) > 1 else ""
img = sys.argv[2] if len(sys.argv) > 2 else "don_thuoc.jpg"

print("=== 1. GEMINI ===")
try:
    from google import genai
    client = genai.Client(api_key=key)
    names = [m.name for m in client.models.list()]
    print("Key hợp lệ. Các model flash khả dụng:", [n for n in names if "flash" in n][:15])
    for model in ("gemini-flash-latest", "gemini-flash-lite-latest"):
        try:
            r = client.models.generate_content(model=model, contents="Trả lời đúng một từ: OK")
            print(f"  {model}: chạy được -> {r.text.strip()[:30]}")
        except Exception as e:
            print(f"  {model}: LỖI -> {str(e)[:300]}")
except Exception:
    traceback.print_exc()

print("\n=== 2. OPENVINO ===")
try:
    import openvino
    print("openvino version:", openvino.__version__)
except Exception:
    print("Không import được openvino:"); traceback.print_exc()
try:
    from openvino_ocr_helper import run_openvino_ocr, parse_offline_ocr_text
    text = run_openvino_ocr(open(img, "rb").read())
    print("Chữ đọc được:", repr(text)[:400])
    print("Thuốc tách được:", parse_offline_ocr_text(text))
except Exception:
    traceback.print_exc()
    