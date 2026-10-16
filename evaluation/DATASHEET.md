# DATASHEET – Bộ dữ liệu đánh giá SafePill

> Điền đầy đủ; mục nào chưa có thì ghi "chưa có" thay vì bỏ trống.

## 1. Bộ ảnh OCR
| Mục | Nội dung |
|---|---|
| Số ảnh / số dòng thuốc | … ảnh / … thuốc |
| Nguồn ảnh | (vd: đơn của … người thân/bạn bè tình nguyện; nhà thuốc …; tự chụp vỏ hộp) |
| Số người cung cấp / khoảng thời gian thu thập | … người / từ … đến … |
| Cơ sở khám/cấp thuốc đa dạng đến đâu | (liệt kê loại: BV tuyến TW, tỉnh, tư nhân, nhà thuốc) |
| Thiết bị chụp | (các dòng điện thoại) |
| Phân bố điều kiện | tot: … · mo: … · thieu_sang: … · choi: … · nghieng: … · bi_cat: … · viet_tay: … |
| Quyền riêng tư | Có đồng ý bằng văn bản; đã che tên/SĐT/mã BN/mã vạch; ảnh gốc lưu ở …; KHÔNG đăng công khai |
| Người gắn nhãn | A: … (vai trò/chuyên môn) · B: … |
| Đồng thuận gắn nhãn kép | … ảnh gắn kép; đồng ý cả 3 trường: …% (xem `label_agreement.py`); bất đồng do … quyết định |
| Chia tập | dev: … ảnh (`split_dev.txt`) · test: … ảnh (`split_test.txt`), seed=42, test chỉ chạy 1 lần |

## 2. Bộ tương tác thuốc / thực phẩm
| Mục | Nội dung |
|---|---|
| Số cặp (có / không tương tác) | … / … |
| Nguồn chuẩn | Drugs.com Interaction Checker, Dược thư Quốc gia VN (link từng cặp trong cột `source`) |
| Ngày tra cứu | … |
| Người tra cứu / người rà soát | … / … |

## 3. Bộ câu hỏi cho trợ lý AI
Số câu: … (trong đó … câu "bẫy"). Người chấm: … Thang chấm: Đúng & đủ / Đúng nhưng thiếu / Sai / Nguy hiểm.

## 4. Những gì bộ dữ liệu KHÔNG đại diện (bắt buộc điền)
- (vd: chưa có đơn viết tay của bác sĩ ở vùng …; chưa có đơn tiếng Anh; ít ảnh nhiều thuốc ≥10 loại; chưa có người dùng ở …)
- (vd: nhóm người thử nghiệm chủ yếu ở … nên chưa đại diện cho toàn bộ người cao tuổi)

## 5. Lịch sử thay đổi bộ dữ liệu
| Ngày | Thay đổi | Người thực hiện |
|---|---|---|
