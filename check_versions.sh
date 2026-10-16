#!/bin/bash
# Kiểm tra bản safepill.py nào là bản mới nhất. Chạy:  bash check_versions.sh
# Chỉ ĐỌC file, không sửa/xoá gì.

REPO="$HOME/dev/safepill"
OLD="$HOME/Desktop/Sáng tạo AI"

if [ ! -d "$REPO" ]; then echo "Không thấy $REPO"; exit 1; fi
if [ ! -d "$OLD" ]; then
  echo "Không thấy thư mục: $OLD"
  echo "Hãy mở Finder, tìm thư mục 'Sáng tạo AI', rồi sửa dòng OLD= trong file này."
  exit 1
fi

report() {
  f="$1"
  echo
  echo "--- $f"
  echo "dòng                 : $(wc -l < "$f" | tr -d ' ')"
  echo "hash                 : $(shasum "$f" | cut -c1-12)"
  echo "import từ core       : $(grep -c 'from safepill_core import' "$f")"
  echo "lỗi st.radio (cũ)    : $(grep -c 'render_pending_review(),' "$f")"
  echo "def check_image_quality: $(grep -c 'def check_image_quality' "$f")"
  echo "độ tin cậy (mới)     : $(grep -c 'assess_answer_confidence' "$f")"
  echo "xác minh mới         : $(grep -c 'validate_pending_rows' "$f")"
  if python3 -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" "$f" 2>/dev/null; then
    echo "cú pháp              : OK"
  else
    echo "cú pháp              : LỖI"
  fi
}

echo "===== BẢN TRÊN GITHUB (đã clone) ====="
report "$REPO/safepill.py"
echo
echo "3 commit gần nhất của safepill.py trên GitHub:"
(cd "$REPO" && git log -3 --format="  %h  %ad  %s" --date=short -- safepill.py)

echo
echo "===== CÁC BẢN TRONG 'Sáng tạo AI' ====="
found=0
for f in "$OLD"/safepill*.py; do
  [ -e "$f" ] || continue
  found=1
  report "$f"
done
[ $found -eq 0 ] && echo "Không có file safepill*.py nào trong thư mục này."

echo
echo "===== safepill_core.py ====="
if [ -e "$OLD/safepill_core.py" ]; then
  if python3 -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" "$OLD/safepill_core.py" 2>/dev/null; then
    echo "$OLD/safepill_core.py : cú pháp OK, $(wc -l < "$OLD/safepill_core.py" | tr -d ' ') dòng"
  else
    echo "$OLD/safepill_core.py : cú pháp LỖI"
  fi
else
  echo "Chưa có safepill_core.py trong 'Sáng tạo AI'"
fi

echo
echo "===== So sánh GitHub với safepill_old.py ====="
if [ -e "$OLD/safepill_old.py" ]; then
  if cmp -s "$REPO/safepill.py" "$OLD/safepill_old.py"; then
    echo "GIỐNG: GitHub chưa có gì mới ngoài bản gốc -> dùng bản bạn đã sửa là an toàn."
  else
    echo "KHÁC: GitHub khác safepill_old.py -> cần gộp, ĐỪNG ghi đè. Gửi lại toàn bộ kết quả này."
  fi
else
  echo "Không có safepill_old.py để so sánh."
fi

echo
echo "===== File nhạy cảm đang nằm trong repo GitHub ====="
(cd "$REPO" && git ls-files | grep -iE "secrets|\.env|\.pdf|\.docx|\.mp4|\.jpg|\.jpeg|\.png|venv" || echo "(không có)")
