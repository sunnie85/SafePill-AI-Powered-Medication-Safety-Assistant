-- Chạy trong Supabase → SQL Editor. Bảng ghi ẩn danh chỉnh sửa OCR (KHÔNG lưu ảnh, KHÔNG lưu số điện thoại).
create table if not exists public.ocr_review_log (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  user_hash text not null,          -- sha256 rút gọn của SĐT, không đảo ngược được dễ dàng
  ai_name text, final_name text,
  ai_dose text, final_dose text,
  ai_uncertain boolean, kept boolean,
  engine text
);
alter table public.ocr_review_log enable row level security;
-- App chỉ cần INSERT. Cho phép insert từ khoá anon/service dùng trong app, KHÔNG cho select công khai:
create policy "app can insert" on public.ocr_review_log for insert with check (true);
-- Truy vấn đánh giá: tỉ lệ người dùng phải sửa tên/liều
-- select engine, count(*) as n, avg((ai_name <> final_name)::int) as name_edit_rate,
--        avg((ai_dose <> final_dose)::int) as dose_edit_rate from ocr_review_log where kept group by engine;
