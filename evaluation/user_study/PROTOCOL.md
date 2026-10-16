# Quy trình thử nghiệm người dùng (≈ 20–25 phút/người)

**Tuyển:** 15–30 người; ≥10 người từ 60 tuổi hoặc dùng ≥5 thuốc/ngày (hoặc người chăm sóc họ).
**Chuẩn bị 1 lần:** 1 đơn thuốc mẫu có 5–6 thuốc (đã che thông tin cá nhân). Trên máy thử nghiệm: quét đơn, rồi trong bảng xác minh
**cố ý sửa 2 lỗi**: (a) đổi tên 1 thuốc sang thuốc khác tên gần giống, (b) đổi 1 hàm lượng (vd 50mg → 100mg). Ghi lại 2 lỗi này.
Đơn mẫu phải có ít nhất 1 cặp thuốc có tương tác trong CSDL.

## Kịch bản (đọc nguyên văn, không gợi ý thêm)
0. Giới thiệu, đọc & ký phiếu đồng ý (`consent_template.md`). Nói rõ: "Chúng tôi đang thử ứng dụng, không phải thử bạn. Bạn có thể dừng bất cứ lúc nào."
1. **Nhiệm vụ 1:** "Đây là kết quả ứng dụng vừa đọc từ đơn thuốc. Hãy kiểm tra và lưu vào tủ thuốc nếu thấy đúng." → bấm giờ từ lúc bắt đầu đến khi lưu.
   - Ghi: có phát hiện lỗi TÊN (1/0)? có phát hiện lỗi HÀM LƯỢNG (1/0)? có tick ô xác nhận mà không đối chiếu ảnh không?
2. **Nhiệm vụ 2:** "Ứng dụng có cảnh báo nào về thuốc của bạn không? Hãy cho tôi biết cảnh báo đó nói gì." → `found_interaction` = 1 nếu nêu được.
3. **Nhiệm vụ 3 (không bắt buộc):** hỏi trợ lý AI 1 câu về thuốc; hỏi người dùng "Bạn tin câu trả lời này đến mức nào? Vì sao?" (ghi nhận họ có đọc banner độ tin cậy không).
4. Bảng SUS 10 câu (thang 1-5), rồi hỏi mở: "Điều gì khó nhất? Bạn sẽ dùng cho người thân không?"

## Ghi chép
Điền `observation_template.csv` (mỗi người 1 dòng) và `sus_template.csv`. `help_requests` = số lần người thử phải hỏi/nhờ bạn giúp.
Chạy: `python evaluation/user_study/user_study_summary.py --obs … --sus … --out evaluation/results/user_study_report.md`

## Câu SUS chuẩn (tiếng Việt, thang 1 = hoàn toàn không đồng ý … 5 = hoàn toàn đồng ý)
1. Tôi nghĩ tôi sẽ muốn dùng ứng dụng này thường xuyên.
2. Tôi thấy ứng dụng phức tạp không cần thiết.
3. Tôi thấy ứng dụng dễ sử dụng.
4. Tôi nghĩ mình cần sự hỗ trợ của người có kỹ thuật để dùng được ứng dụng.
5. Tôi thấy các chức năng trong ứng dụng được tích hợp tốt.
6. Tôi thấy ứng dụng có quá nhiều điểm không nhất quán.
7. Tôi nghĩ hầu hết mọi người sẽ học cách dùng ứng dụng này rất nhanh.
8. Tôi thấy ứng dụng rất rườm rà, khó dùng.
9. Tôi cảm thấy rất tự tin khi dùng ứng dụng.
10. Tôi cần học nhiều thứ trước khi có thể dùng ứng dụng này.
