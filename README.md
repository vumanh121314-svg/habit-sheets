# HABIT SHEETS 3.0 – Personal Growth Operating System

## Tính năng 3.0
- Đăng ký / đăng nhập; mật khẩu băm PBKDF2-HMAC-SHA256.
- Dashboard tiến độ, XP, chuỗi ngày.
- Kế hoạch việc cần làm hằng ngày, phân loại và ưu tiên.
- Ghi nhận phiên tập trung theo phút.
- Theo dõi thói quen, mục tiêu và cảnh báo hạn.
- Trang tài chính để theo dõi mục tiêu tài chính (không kết nối ngân hàng).
- Trợ lý 1% đưa gợi ý dựa trên dữ liệu (rule-based, chưa phải AI tạo sinh).
- Nhật ký phản tư và báo cáo 30 ngày.
- Sao lưu CSV ZIP; GitHub Actions nhắc Telegram 20:30.

## Chạy thử
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Tạo tài khoản mới ngay màn hình đăng nhập.

## GitHub + Streamlit Community Cloud
Tạo repository, giải nén dự án, chạy:
```bash
git init
git add .
git commit -m "Habit Sheets 3.0"
git branch -M main
git remote add origin https://github.com/USERNAME/habit-sheets-3.git
git push -u origin main
```
Đăng nhập https://share.streamlit.io bằng GitHub, chọn repo, branch `main`, file `app.py`, Deploy.

## Telegram reminder
Tạo bot bằng @BotFather, nhắn bot và nhấn Start. Lấy Bot Token và Chat ID. Trong GitHub repo vào Settings → Secrets and variables → Actions, thêm:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
Sau đó bật workflow trong tab Actions. Cron 13:30 UTC = 20:30 giờ Việt Nam.

## Giới hạn quan trọng
Bản này là MVP. Mật khẩu được băm, nhưng SQLite là file cục bộ; Streamlit Community Cloud không bảo đảm lưu bền vững, đồng bộ nhiều thiết bị hoặc phù hợp cho nhiều người dùng production. Trước khi phát hành thực tế cần chuyển sang Supabase Auth + PostgreSQL, bật RLS, quản lý khóa trong secrets và kiểm thử bảo mật. Không nhập thông tin ngân hàng, mật khẩu, OTP hay dữ liệu nhạy cảm.
