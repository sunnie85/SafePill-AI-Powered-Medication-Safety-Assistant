# Báo cáo đánh giá SafePill (phiên bản v1.1-safety)

> Điền số liệu thật từ `evaluation/results/*.md`. Không làm tròn đẹp hơn thực tế; ghi cả điểm yếu.

## 1. Tóm tắt
- (2–3 câu: đã làm gì, kết quả chính, hạn chế lớn nhất)

## 2. Phản hồi → Thay đổi → Minh chứng
| Góp ý | Thay đổi đã làm | Commit / PR | Minh chứng |
|---|---|---|---|
| 1. Làm rõ dữ liệu, bộ đánh giá chuẩn, mở rộng thử nghiệm | Bộ … ảnh OCR, … cặp tương tác, … câu hỏi AI; gắn nhãn kép; chia dev/test; thử nghiệm … người | `…` | `evaluation/DATASHEET.md`, `evaluation/results/` |
| 2. Ảnh thiếu chữ/mờ/thiếu sáng + bắt xác minh trước khi lưu | Kiểm tra chất lượng 2 mức; ép "chưa chắc"; màn hình xác minh có ảnh gốc, chặn lưu khi thiếu tên/liều | `…` | mục 4, 6 và `docs/img/` |
| 3. Cảnh báo khi thiếu căn cứ/độ tin cậy thấp | Banner độ tin cậy (cao/trung bình/thấp); ghi chú phạm vi CSDL; sửa lọc nguồn; quy tắc an toàn trong prompt | `…` | mục 5 và `docs/img/` |

## 3. Dữ liệu dùng để đánh giá
(Tóm tắt DATASHEET: số lượng, nguồn, cách gắn nhãn, đồng thuận, chia tập, hạn chế.)

## 4. Kết quả OCR (tập test)
(Dán bảng Tổng hợp từ `ocr_report.md`, rồi bảng theo điều kiện ảnh.)
- **Đọc đúng cả 3 trường (tên + hàm lượng + liều):** …
- **Flag recall:** …  | **Lỗi im lặng:** …
- **Ảnh bị từ chối do chất lượng:** …
- Nhận xét theo điều kiện ảnh: (mờ/thiếu sáng/thiếu chữ có bị từ chối hoặc gắn cờ không? ca nào lỗi im lặng?)

## 5. Kết quả tương tác thuốc/thực phẩm & trợ lý AI
- Bảng từ `interaction_report.md`: recall trong phạm vi, **recall tổng thể**, báo nhầm, độ phủ.
- Trợ lý AI: … câu; Đúng & đủ …%; Nguy hiểm …; câu "bẫy" bị hạ độ tin cậy/từ chối đúng …%.

## 6. Thử nghiệm người dùng
(Dán `user_study_report.md`: số người, % phát hiện lỗi cài sẵn, thời gian, SUS, nhận xét định tính.)

## 7. Hạn chế & việc tiếp theo
- CSDL tương tác còn nhỏ (… cặp), chưa có dược sĩ thẩm định.
- Mẫu nhỏ nên khoảng tin cậy rộng; chưa phải thử nghiệm lâm sàng.
- Dữ liệu gửi tới Gemini/openFDA: …
- Kế hoạch: nhờ dược sĩ rà soát CSDL, mở rộng bộ test, thử nghiệm với … người.
