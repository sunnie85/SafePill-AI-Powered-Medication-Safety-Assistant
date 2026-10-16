# Changelog

## v1.1-safety
### Sửa lỗi
- `st.radio` nhận nhầm `render_pending_review()` làm tham số (bảng xác minh lỗi).
- Xoá `check_image_quality` trùng lặp (ngưỡng chói 200 báo oan giấy đơn trắng).
- `is_trusted_medical_source`: so khớp hostname + title thay vì chuỗi con; tránh nhận nhầm tên miền giả.
- Chuẩn hoá tên thuốc trước khi tra openFDA.
### Thêm mới
- `safepill_core.py`: tách logic thuần để kiểm thử/đánh giá tự động.
- Kiểm tra chất lượng ảnh 2 mức (chặn / ép "chưa chắc"); phát hiện ảnh có thể thiếu thuốc.
- Màn hình xác minh bắt buộc: ảnh gốc cạnh bảng, dòng chưa chắc bỏ tick, chặn lưu khi thiếu tên/liều, xác nhận trước khi lưu, tuỳ chọn ghi log ẩn danh.
- Độ tin cậy cho tư vấn AI (cao/trung bình/thấp) + quy tắc an toàn trong prompt; ghi chú phạm vi CSDL tương tác.
- Bộ công cụ đánh giá `evaluation/` (OCR, tương tác, đồng thuận nhãn, thử nghiệm người dùng), test và CI.
